import pytest

from backend.routes.api import _validate_container_payload


def test_validate_container_payload_accepts_components_v2_message():
    payload = {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "components": [
                    {"type": 10, "content": "DailyBread Verse"},
                    {"type": 14},
                ],
            }
        ],
    }

    validated = _validate_container_payload(payload)

    assert validated["flags"] == 32768
    assert validated["components"][0]["type"] == 17


def test_validate_container_payload_rejects_missing_text_display():
    payload = {
        "flags": 32768,
        "components": [{"type": 17, "components": [{"type": 14}]}],
    }

    with pytest.raises(ValueError):
        _validate_container_payload(payload)
