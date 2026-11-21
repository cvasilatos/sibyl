import json
from pathlib import Path

from sibyl.openapi import main


def test_writes_schema_with_typed_responses(tmp_path: Path) -> None:
    """The exported schema lists the API routes with named response models."""
    out = tmp_path / "openapi.json"
    main(["openapi", str(out)])
    schema = json.loads(out.read_text())
    response = schema["paths"]["/api/reviews"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"].endswith("/ReviewList")


def test_schema_lists_websocket_messages(tmp_path: Path) -> None:
    """The WebSocket message models are exported, with refs that resolve inside the schema."""
    out = tmp_path / "openapi.json"
    main(["openapi", str(out)])
    schemas = json.loads(out.read_text())["components"]["schemas"]
    for name in ("ReviewProgress", "ReviewCompleted", "ReviewResults", "ReviewResult", "SocketError", "PullProgress"):
        assert name in schemas, name
    assert schemas["ReviewResult"]["properties"]["criteria"]["$ref"] == "#/components/schemas/ReviewCriteria"
    assert schemas["ReviewCompleted"]["properties"]["status"]["const"] == "completed"
