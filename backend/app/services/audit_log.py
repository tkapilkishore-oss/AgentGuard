import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditChainState, AuditEvent

GENESIS_PREV_HASH = "0" * 64


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Computes deterministic SHA256 hex string for a payload dictionary."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_event_hash(
    prev_hash: str,
    event_type: str,
    actor: str,
    transaction_id: str | None,
    payload_hash: str,
) -> str:
    """Computes deterministic SHA256 chain hash for an audit event link."""
    event_string = (
        f"{prev_hash}:{event_type}:{actor}:{transaction_id or ''}:{payload_hash}"
    )
    return hashlib.sha256(event_string.encode("utf-8")).hexdigest()


def log_audit_event(
    db: Session,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    transaction_id: str | None = None,
) -> AuditEvent:
    """Appends a new tamper-evident audit event to the server-side hash chain under row lock."""
    # Lock the AuditChainState singleton row (id=1)
    state = db.query(AuditChainState).filter_by(id=1).with_for_update().first()
    if not state:
        state = AuditChainState(id=1, last_hash=GENESIS_PREV_HASH)
        db.add(state)
        db.flush()

    prev_hash = state.last_hash
    payload_hash = compute_payload_hash(payload)
    event_hash = compute_event_hash(
        prev_hash=prev_hash,
        event_type=event_type,
        actor=actor,
        transaction_id=transaction_id,
        payload_hash=payload_hash,
    )

    audit_event = AuditEvent(
        id=str(uuid.uuid4()),
        transaction_id=transaction_id,
        event_type=event_type,
        actor=actor,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit_event)

    state.last_hash = event_hash
    db.flush()
    return audit_event


def verify_audit_chain(db: Session) -> tuple[bool, str | None]:
    """Verifies the integrity of the audit hash chain from genesis to state head.

    Returns (is_valid: bool, error_message: str | None).
    """
    events = (
        db.query(AuditEvent)
        .order_by(AuditEvent.seq_id.asc())
        .all()
    )
    if not events:
        return True, None

    expected_prev_hash = GENESIS_PREV_HASH
    for idx, event in enumerate(events):
        if event.prev_hash != expected_prev_hash:
            return (
                False,
                f"Tamper detected at event index {idx} (id={event.id}): expected prev_hash {expected_prev_hash}, got {event.prev_hash}",
            )

        event_string = f"{event.prev_hash}:{event.event_type}:{event.actor}:{event.transaction_id or ''}:{event.payload_hash}"
        expected_prev_hash = hashlib.sha256(event_string.encode("utf-8")).hexdigest()

    state = db.query(AuditChainState).filter_by(id=1).first()
    if state and state.last_hash != expected_prev_hash:
        return (
            False,
            f"Chain state head mismatch: state last_hash {state.last_hash} != calculated {expected_prev_hash}",
        )

    return True, None
