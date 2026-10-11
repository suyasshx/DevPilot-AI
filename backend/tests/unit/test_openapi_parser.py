"""
DevPilot AI - Unit Tests for OpenAPI Parser.
"""

import pytest
from app.ingestion.openapi_parser import (
    OpenAPIParser,
    OpenAPIValidationError,
    ParsedSpecification,
)


def test_parse_sample_ecommerce_spec(sample_spec_content: str) -> None:
    """Test parsing the complete sample e-commerce specification."""
    parser = OpenAPIParser()
    parsed: ParsedSpecification = parser.parse(sample_spec_content)

    assert parsed.title == "DevPilot AI Sample E-Commerce Target API"
    assert parsed.version == "1.0.0"
    assert parsed.spec_format == "json"
    assert len(parsed.checksum_sha256) == 64
    assert len(parsed.endpoints) == 10

    # Verify key endpoints are extracted
    endpoint_map = {(ep.path, ep.method): ep for ep in parsed.endpoints}
    assert ("/auth/login", "POST") in endpoint_map
    assert ("/users", "POST") in endpoint_map
    assert ("/users/{user_id}", "GET") in endpoint_map
    assert ("/products", "GET") in endpoint_map
    assert ("/orders", "POST") in endpoint_map

    # Check /orders POST endpoint details
    orders_ep = endpoint_map[("/orders", "POST")]
    assert orders_ep.summary is not None
    assert "Orders" in orders_ep.tags
    assert orders_ep.auth_required is True  # Protected endpoint
    assert "201" in orders_ep.responses_schema
    assert "401" in orders_ep.responses_schema
    assert "422" in orders_ep.responses_schema


def test_dereference_components(sample_spec_content: str) -> None:
    """Verify internal $ref pointers in requestBody and responses are dereferenced."""
    parser = OpenAPIParser()
    parsed = parser.parse(sample_spec_content)
    endpoint_map = {(ep.path, ep.method): ep for ep in parsed.endpoints}

    orders_ep = endpoint_map[("/orders", "POST")]
    body_schema = orders_ep.request_body_schema
    # The request body schema should have resolved properties, not a bare unresolved $ref
    assert "properties" in body_schema
    assert "items" in body_schema["properties"]
    assert "shipping_address" in body_schema["properties"]


def test_parameter_extraction(sample_spec_content: str) -> None:
    """Verify path and query parameters with their schemas and types."""
    parser = OpenAPIParser()
    parsed = parser.parse(sample_spec_content)
    endpoint_map = {(ep.path, ep.method): ep for ep in parsed.endpoints}

    # /users/{user_id} path param
    user_ep = endpoint_map[("/users/{user_id}", "GET")]
    assert len(user_ep.parameters) >= 1
    user_id_param = next(p for p in user_ep.parameters if p["name"] == "user_id")
    assert user_id_param["in"] == "path"
    assert user_id_param["required"] is True
    assert user_id_param["schema"].get("type") == "integer"

    # /products query params
    prod_ep = endpoint_map[("/products", "GET")]
    param_names = [p["name"] for p in prod_ep.parameters]
    assert "skip" in param_names
    assert "limit" in param_names


def test_parse_yaml_spec() -> None:
    """Test parsing a valid OpenAPI 3.0 specification written in YAML."""
    yaml_spec = """
openapi: 3.0.0
info:
  title: EA Telemetry Ingestion API
  version: 2.1.0
paths:
  /telemetry/events:
    post:
      summary: Ingest game client telemetry batch
      tags:
        - Telemetry
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - event_type
              properties:
                event_type:
                  type: string
      responses:
        '202':
          description: Batch accepted for asynchronous processing
"""
    parser = OpenAPIParser()
    parsed = parser.parse(yaml_spec)
    assert parsed.title == "EA Telemetry Ingestion API"
    assert parsed.version == "2.1.0"
    assert parsed.spec_format == "yaml"
    assert len(parsed.endpoints) == 1
    assert parsed.endpoints[0].path == "/telemetry/events"
    assert parsed.endpoints[0].method == "POST"


def test_invalid_spec_empty() -> None:
    """Test rejection when spec string is empty."""
    parser = OpenAPIParser()
    with pytest.raises(OpenAPIValidationError, match="empty"):
        parser.parse("")


def test_invalid_spec_malformed_syntax() -> None:
    """Test rejection of malformed JSON / YAML syntax."""
    parser = OpenAPIParser()
    with pytest.raises(OpenAPIValidationError):
        parser.parse("{not valid json or yaml: [unclosed")


def test_invalid_spec_missing_openapi_version() -> None:
    """Test rejection when openapi version tag is missing."""
    spec = '{"info": {"title": "Test", "version": "1.0"}, "paths": {}}'
    parser = OpenAPIParser()
    with pytest.raises(OpenAPIValidationError, match="OpenAPI version"):
        parser.parse(spec)


def test_invalid_spec_missing_paths() -> None:
    """Test rejection when paths object is missing."""
    spec = '{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}}'
    parser = OpenAPIParser()
    with pytest.raises(OpenAPIValidationError, match="'paths'"):
        parser.parse(spec)


def test_checksum_deduplication_consistency(sample_spec_content: str) -> None:
    """Verify that identical spec strings yield identical SHA256 checksums."""
    parser = OpenAPIParser()
    parsed1 = parser.parse(sample_spec_content)
    parsed2 = parser.parse(sample_spec_content)
    assert parsed1.checksum_sha256 == parsed2.checksum_sha256
