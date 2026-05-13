from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ShipmentAttachment:
    filename: str
    mime_type: str
    content: bytes


@dataclass(frozen=True)
class ShipmentIngest:
    run_id: str
    customer_id: str
    sender: str
    reply_to: str
    subject: str
    message_id: str | None
    received_at: datetime
    attachments: list[ShipmentAttachment]
