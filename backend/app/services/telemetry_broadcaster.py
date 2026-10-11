"""
DevPilot AI - Real-Time Telemetry and Server-Sent Events (SSE) Broadcaster.
Enables live streaming of test execution logs, stage transitions, and telemetry metrics.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, AsyncGenerator, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TelemetryBroadcaster:
    """
    In-memory async Pub/Sub hub managing live SSE streams per test run.
    Maintains an event history buffer so reconnecting or late-joining clients
    receive the full execution transcript.
    """

    def __init__(self, max_history: int = 500):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._max_history = max_history
        self._lock = asyncio.Lock()

    def _format_sse(self, event_type: str, data: Any) -> str:
        """Formats data into standard Server-Sent Events wire format."""
        if isinstance(data, (dict, list)):
            payload = json.dumps(data)
        else:
            payload = json.dumps({"message": str(data)})
        return f"event: {event_type}\ndata: {payload}\n\n"

    async def publish(self, run_id: str, event_type: str, data: Any) -> None:
        """Publishes an event to all active subscribers for the given run_id and appends to buffer."""
        event_dict = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with self._lock:
            # Store history
            if run_id not in self._history:
                self._history[run_id] = []
            self._history[run_id].append(event_dict)
            if len(self._history[run_id]) > self._max_history:
                self._history[run_id].pop(0)

            # Broadcast to queues
            queues = list(self._subscribers.get(run_id, set()))

        for q in queues:
            try:
                q.put_nowait(event_dict)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for subscriber on run {run_id}, dropping event.")

    async def subscribe(
        self,
        run_id: str,
        initial_history: bool = True,
        heartbeat_interval: float = 15.0,
    ) -> AsyncGenerator[str, None]:
        """
        Subscribes to live SSE events for a specific run.
        Yields buffered history first, followed by live events until terminal event.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        async with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = set()
            self._subscribers[run_id].add(queue)

            history_snapshot = list(self._history.get(run_id, [])) if initial_history else []

        try:
            # 1. Stream buffered events
            for hist_event in history_snapshot:
                yield self._format_sse(hist_event["event_type"], hist_event["data"])
                if hist_event["event_type"] in ("completed", "failed", "done"):
                    return

            # 2. Stream real-time events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                    yield self._format_sse(event["event_type"], event["data"])

                    if event["event_type"] in ("completed", "failed", "done"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"
        finally:
            async with self._lock:
                if run_id in self._subscribers:
                    self._subscribers[run_id].discard(queue)
                    if not self._subscribers[run_id]:
                        del self._subscribers[run_id]

    def clear_run(self, run_id: str) -> None:
        """Purges cached history for a completed run."""
        self._history.pop(run_id, None)
        self._subscribers.pop(run_id, None)


# Global singleton broadcaster instance
telemetry_broadcaster = TelemetryBroadcaster()
