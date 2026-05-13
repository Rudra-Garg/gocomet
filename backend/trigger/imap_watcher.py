from __future__ import annotations

import email
import imaplib
import json
import logging
import mimetypes
import threading
import time
import uuid
from datetime import datetime, timezone
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from backend.config import PROJECT_ROOT, Settings
from backend.pipeline.multi import ingest_shipment
from backend.trigger.models import ShipmentAttachment, ShipmentIngest

LOGGER = logging.getLogger(__name__)
SUPPORTED_ATTACHMENT_PREFIXES = ("application/pdf", "image/")


def start_imap_watcher(settings: Settings) -> threading.Thread | None:
    if not settings.imap_host:
        return None
    thread = threading.Thread(
        target=watch_inbox,
        args=(settings,),
        daemon=True,
        name="imap-shipment-watcher",
    )
    thread.start()
    LOGGER.info("IMAP watcher started for host=%s mailbox=%s", settings.imap_host, settings.imap_mailbox)
    return thread


def watch_inbox(settings: Settings) -> None:
    while True:
        try:
            poll_once(settings)
        except Exception:
            LOGGER.exception("IMAP watcher poll failed")
        time.sleep(settings.imap_poll_seconds)


def poll_once(settings: Settings) -> int:
    if not (settings.imap_host and settings.imap_username and settings.imap_password):
        LOGGER.info("IMAP watcher skipped because IMAP settings are incomplete")
        return 0

    sender_map = _load_sender_map()
    processed = 0
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as mailbox:
        mailbox.login(settings.imap_username, settings.imap_password)
        mailbox.select(settings.imap_mailbox)
        status, data = mailbox.search(None, "UNSEEN")
        if status != "OK":
            LOGGER.warning("IMAP search failed with status=%s", status)
            return 0

        for message_id in data[0].split():
            fetch_status, fetched = mailbox.fetch(message_id, "(RFC822)")
            if fetch_status != "OK" or not fetched:
                LOGGER.warning("IMAP fetch failed for uid=%s status=%s", message_id, fetch_status)
                continue
            raw = fetched[0][1]
            message = email.message_from_bytes(raw)
            ingest = _message_to_ingest(message, sender_map)
            if ingest.attachments:
                LOGGER.info(
                    "IMAP ingest starting run_id=%s sender=%s attachments=%s",
                    ingest.run_id,
                    ingest.sender,
                    len(ingest.attachments),
                )
                try:
                    ingest_shipment(ingest, settings)
                except Exception:
                    LOGGER.exception("IMAP ingest failed run_id=%s", ingest.run_id)
                    continue
                mailbox.store(message_id, "+FLAGS", "\\Seen")
                LOGGER.info("IMAP ingest completed run_id=%s; message marked Seen", ingest.run_id)
                processed += 1
            else:
                LOGGER.info("IMAP message skipped because no PDF/image attachments were found")
    return processed


def _message_to_ingest(message: Message, sender_map: dict[str, str]) -> ShipmentIngest:
    sender = _first_address(message.get("From", ""))
    reply_to = _first_address(message.get("Reply-To", "")) or sender
    customer_id = sender_map.get(sender.casefold(), "acme")
    return ShipmentIngest(
        run_id=str(uuid.uuid4()),
        customer_id=customer_id,
        sender=sender,
        reply_to=reply_to,
        subject=message.get("Subject", ""),
        message_id=message.get("Message-ID"),
        received_at=_received_at(message),
        attachments=_attachments(message),
    )


def _attachments(message: Message) -> list[ShipmentAttachment]:
    attachments = []
    for part in message.walk():
        if part.get_content_disposition() != "attachment":
            continue
        filename = part.get_filename() or "attachment"
        content = part.get_payload(decode=True) or b""
        mime_type = part.get_content_type() or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if mime_type == "application/octet-stream":
            mime_type = mimetypes.guess_type(filename)[0] or mime_type
        if mime_type == "application/pdf" or mime_type.startswith("image/"):
            attachments.append(
                ShipmentAttachment(
                    filename=Path(filename).name,
                    mime_type=mime_type,
                    content=content,
                ),
            )
    return attachments


def _load_sender_map() -> dict[str, str]:
    path = PROJECT_ROOT / "data" / "rulesets" / "sender_map.json"
    if not path.exists():
        return {}
    return {key.casefold(): value for key, value in json.loads(path.read_text()).items()}


def _first_address(header_value: str) -> str:
    addresses = getaddresses([header_value])
    return addresses[0][1] if addresses else ""


def _received_at(message: Message) -> datetime:
    try:
        parsed = parsedate_to_datetime(message.get("Date", ""))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
