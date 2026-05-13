import pytest
from fastapi import HTTPException

from backend.api.routes import SimulateTriggerRequest, simulate_trigger
from backend.config import Settings
from backend.trigger.smtp_sender import send_reply


def test_simulate_endpoint_rejects_path_traversal() -> None:
    with pytest.raises(HTTPException) as exc_info:
        simulate_trigger(SimulateTriggerRequest(customer_id="acme", filenames=["../x.pdf"]))

    assert exc_info.value.status_code == 400


def test_smtp_sender_raises_when_not_configured() -> None:
    settings = Settings(gemini_api_key="test-key")

    with pytest.raises(RuntimeError, match="SMTP not configured"):
        send_reply(settings, to="reply@example.com", subject="Docs", body="Please amend.")
