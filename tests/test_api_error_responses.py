import importlib

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_unknown_route_returns_json_error_response() -> None:
    response = client.get("/api/definitely-not-a-route")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["success"] is False
    assert "error" in data


def test_bible_service_uses_bible_api_key_env(monkeypatch) -> None:
    import backend.services.bible_service as bible_service

    monkeypatch.delenv("API_BIBLE_KEY", raising=False)
    monkeypatch.delenv("api_bible_key", raising=False)
    monkeypatch.setenv("bible_api_key", "test-key")

    module = importlib.reload(bible_service)

    assert module._api_headers()["api-key"] == "test-key"


def test_bible_service_parses_translation_prefix(monkeypatch) -> None:
    import backend.services.bible_service as bible_service

    monkeypatch.setenv("nlt_bible_id", "nlt-id")
    monkeypatch.setenv("nkjv_bible_id", "nkjv-id")
    monkeypatch.setenv("niv_bible_id", "niv-id")

    module = importlib.reload(bible_service)
    parsed = module._parse_reference_query("NLT/NKJV/NIV 1 Corinthians 16:14")

    assert parsed["reference"] == "1 Corinthians 16:14"
    assert parsed["translations"] == ["nlt-id", "nkjv-id", "niv-id"]
