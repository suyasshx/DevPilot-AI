"""
DevPilot AI - OpenAPI 3.x Specification Parser.

Parses, validates, normalizes, and dereferences OpenAPI specifications in JSON or YAML format.
Extracts endpoints, schemas, parameters, response matrices, and security constraints.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import yaml


class OpenAPIValidationError(Exception):
    """Raised when an uploaded API specification violates OpenAPI structural rules."""
    pass


@dataclass
class ParsedEndpoint:
    """Strongly typed metadata extracted from an individual OpenAPI operation."""
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body_schema: Dict[str, Any] = field(default_factory=dict)
    responses_schema: Dict[str, Any] = field(default_factory=dict)
    auth_required: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class ParsedSpecification:
    """Complete parsed and validated specification metadata."""
    title: str
    version: str
    spec_format: str
    checksum_sha256: str
    raw_content: str
    endpoints: List[ParsedEndpoint] = field(default_factory=list)


class OpenAPIParser:
    """Robust parser and dereferencer for OpenAPI 3.0 / 3.1 specifications."""

    SUPPORTED_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

    def parse(self, raw_content: str) -> ParsedSpecification:
        """
        Parse and validate raw specification content (JSON or YAML string).
        Raises OpenAPIValidationError on malformed or unsupported specifications.
        """
        if not raw_content or not raw_content.strip():
            raise OpenAPIValidationError("Specification content is empty.")

        # Compute SHA256 checksum for audit and deduplication
        checksum = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

        # Try JSON first, fallback to YAML
        spec_format = "json"
        try:
            doc = json.loads(raw_content)
        except json.JSONDecodeError:
            try:
                doc = yaml.safe_load(raw_content)
                spec_format = "yaml"
            except yaml.YAMLError as exc:
                raise OpenAPIValidationError(f"Failed to parse specification as JSON or YAML: {str(exc)}") from exc

        if not isinstance(doc, dict):
            raise OpenAPIValidationError("Top-level OpenAPI structure must be a JSON/YAML object/dictionary.")

        # Validate mandatory OpenAPI fields
        version_key = doc.get("openapi") or doc.get("swagger")
        if not version_key:
            raise OpenAPIValidationError("Missing required OpenAPI version declaration ('openapi' or 'swagger' field).")

        info = doc.get("info")
        if not info or not isinstance(info, dict):
            raise OpenAPIValidationError("Missing required 'info' object in specification.")

        title = str(info.get("title", "Untitled API"))
        version = str(info.get("version", "1.0.0"))

        paths = doc.get("paths")
        if paths is None:
            raise OpenAPIValidationError("Missing required 'paths' object in specification.")

        if not isinstance(paths, dict):
            raise OpenAPIValidationError("'paths' field must be an object/dictionary mapping URLs to operations.")

        # Check global security schemes
        global_security = doc.get("security", [])
        has_global_auth = bool(global_security)

        # Extract endpoints and dereference components
        endpoints: List[ParsedEndpoint] = []
        for path_key, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Path-level parameters common to all operations on this path
            path_level_params = path_item.get("parameters", [])

            for method_key, operation in path_item.items():
                method_lower = method_key.lower()
                if method_lower not in self.SUPPORTED_HTTP_METHODS:
                    continue

                if not isinstance(operation, dict):
                    continue

                endpoint = self._parse_operation(
                    doc=doc,
                    path=path_key,
                    method=method_lower.upper(),
                    operation=operation,
                    path_level_params=path_level_params,
                    has_global_auth=has_global_auth,
                )
                endpoints.append(endpoint)

        return ParsedSpecification(
            title=title,
            version=version,
            spec_format=spec_format,
            checksum_sha256=checksum,
            raw_content=raw_content,
            endpoints=endpoints,
        )

    def _parse_operation(
        self,
        doc: Dict[str, Any],
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_level_params: List[Any],
        has_global_auth: bool,
    ) -> ParsedEndpoint:
        """Parse an individual HTTP operation within a path."""
        summary = operation.get("summary")
        description = operation.get("description")
        tags = [str(t) for t in operation.get("tags", [])]

        # Auth evaluation: operation-level security overrides global security
        op_security = operation.get("security")
        if op_security is not None:
            auth_required = bool(op_security)
        else:
            auth_required = has_global_auth

        # Combine path-level and operation-level parameters
        raw_params = list(path_level_params) + list(operation.get("parameters", []))
        parameters: List[Dict[str, Any]] = []
        seen_params = set()

        for p in raw_params:
            resolved_p = self._dereference(doc, p)
            if not isinstance(resolved_p, dict):
                continue

            p_name = resolved_p.get("name")
            p_in = resolved_p.get("in")
            if not p_name or not p_in:
                continue

            param_key = (p_name, p_in)
            if param_key in seen_params:
                continue
            seen_params.add(param_key)

            p_schema = self._dereference(doc, resolved_p.get("schema", {}))
            parameters.append({
                "name": p_name,
                "in": p_in,
                "required": bool(resolved_p.get("required", False)),
                "description": resolved_p.get("description"),
                "schema": p_schema,
            })

        # Request Body schema resolution
        request_body_schema: Dict[str, Any] = {}
        raw_body = operation.get("requestBody")
        if raw_body:
            resolved_body = self._dereference(doc, raw_body)
            if isinstance(resolved_body, dict):
                content = resolved_body.get("content", {})
                json_content = content.get("application/json") or next(iter(content.values()), None)
                if json_content and isinstance(json_content, dict):
                    raw_schema = json_content.get("schema", {})
                    request_body_schema = self._dereference(doc, raw_schema)
                    request_body_schema["_required"] = bool(resolved_body.get("required", False))

        # Responses schema matrix resolution
        responses_schema: Dict[str, Any] = {}
        raw_responses = operation.get("responses", {})
        if isinstance(raw_responses, dict):
            for status_code, resp_obj in raw_responses.items():
                resolved_resp = self._dereference(doc, resp_obj)
                if not isinstance(resolved_resp, dict):
                    continue

                resp_entry: Dict[str, Any] = {
                    "description": resolved_resp.get("description", ""),
                    "schema": {},
                }

                resp_content = resolved_resp.get("content", {})
                if isinstance(resp_content, dict):
                    json_resp = resp_content.get("application/json") or next(iter(resp_content.values()), None)
                    if json_resp and isinstance(json_resp, dict):
                        resp_schema = json_resp.get("schema", {})
                        resp_entry["schema"] = self._dereference(doc, resp_schema)

                responses_schema[str(status_code)] = resp_entry

        return ParsedEndpoint(
            path=path,
            method=method,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body_schema=request_body_schema,
            responses_schema=responses_schema,
            auth_required=auth_required,
            tags=tags,
        )

    def _dereference(self, doc: Dict[str, Any], obj: Any, visited: Optional[set] = None) -> Any:
        """
        Recursively dereference internal JSON references ($ref) such as '#/components/schemas/User'.
        Protects against infinite recursion with cycle detection.
        """
        if visited is None:
            visited = set()

        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                if ref_path in visited:
                    return {"_circular_ref": ref_path}

                visited.add(ref_path)
                resolved = self._resolve_ref(doc, ref_path)
                return self._dereference(doc, resolved, visited.copy())

            # Recursively resolve nested dict values
            return {k: self._dereference(doc, v, visited) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._dereference(doc, item, visited) for item in obj]

        return obj

    def _resolve_ref(self, doc: Dict[str, Any], ref_path: str) -> Any:
        """Resolve a local pointer string like '#/components/schemas/LoginRequest'."""
        if not ref_path.startswith("#/"):
            # Remote external URLs are returned as-is to prevent SSRF
            return {"_external_ref": ref_path}

        parts = ref_path.lstrip("#/").split("/")
        current = doc
        for part in parts:
            part_unescaped = part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and part_unescaped in current:
                current = current[part_unescaped]
            else:
                return {"_unresolved_ref": ref_path}

        return current
