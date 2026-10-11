"""
DevPilot AI - Test Case Signature Hashing and Deduplication.
Prevents duplicate test cases from polluting test suites and inflating execution latency.
"""

import json
import hashlib
from typing import List, Set, Tuple
from ..schemas.test_case import GeneratedTestCaseItem


class TestCaseDeduplicator:
    """Computes canonical structural signatures and suppresses duplicates."""

    @staticmethod
    def canonical_json(obj: any) -> str:
        """Produce deterministic, sorted JSON representation."""
        if not obj:
            return "{}"
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))

    @classmethod
    def compute_signature(
        cls,
        endpoint_id: str,
        http_method: str,
        test_case: GeneratedTestCaseItem,
    ) -> str:
        """Compute SHA256 signature for test case based on structural execution identity."""
        raw_identity = (
            f"{endpoint_id}:"
            f"{http_method.upper()}:"
            f"{test_case.category.lower()}:"
            f"{test_case.expected_status}:"
            f"{cls.canonical_json(test_case.path_params)}:"
            f"{cls.canonical_json(test_case.query_params)}:"
            f"{cls.canonical_json(test_case.request_body)}"
        )
        return hashlib.sha256(raw_identity.encode("utf-8")).hexdigest()

    @classmethod
    def deduplicate(
        cls,
        test_cases: List[GeneratedTestCaseItem],
        endpoint_id: str,
        http_method: str,
        existing_signatures: Set[str],
    ) -> Tuple[List[GeneratedTestCaseItem], int]:
        """
        Filter out test cases whose signatures match already seen tests
        or existing test cases in the database.
        """
        seen_in_batch: Set[str] = set()
        unique_tests: List[GeneratedTestCaseItem] = []
        duplicates_count = 0

        for tc in test_cases:
            sig = cls.compute_signature(endpoint_id, http_method, tc)
            if sig in existing_signatures or sig in seen_in_batch:
                duplicates_count += 1
                continue

            seen_in_batch.add(sig)
            unique_tests.append(tc)

        return unique_tests, duplicates_count
