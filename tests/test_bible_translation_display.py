import backend.services.bible_service as bible_service


def test_parse_reference_query_returns_display_translation_label(monkeypatch):
    monkeypatch.setenv("nlt_bible_id", "78a9f6124f344018-01")
    monkeypatch.setenv("niv_bible_id", "4567890123456789-01")

    parsed = bible_service._parse_reference_query("NIV John 3:16")

    assert parsed["reference"] == "John 3:16"
    assert parsed["translations"] == ["4567890123456789-01"]
    assert parsed["translation_labels"] == ["NIV"]


def test_parse_reference_query_supports_explicit_translation_ids():
    parsed = bible_service._parse_reference_query("NIV:78a9f6124f344018-01 John 3:16")

    assert parsed["reference"] == "John 3:16"
    assert parsed["translations"] == ["78a9f6124f344018-01"]
    assert parsed["translation_labels"] == ["NIV"]
