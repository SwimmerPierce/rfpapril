"""
Centralized error logging for the processing pipeline (ADMIN-01).

All processing and enrichment failures are written to the SystemError table
so they appear as open issues for admin review and (Phase 3) Zoho Admin Queue sync.

Design notes:
- Errors are committed immediately using the caller's session so they survive
  a subsequent session rollback in the caller.
- entity_id ties an error to a specific DB record (bid_id, company_id, etc.)
  for easy triage.
"""
from typing import Optional

from sqlmodel import Session

from src.database.models import SystemError


def log_processing_error(
    session: Session,
    source: str,
    message: str,
    entity_id: Optional[int] = None,
) -> SystemError:
    """Insert a SystemError record into the database.

    Args:
        session: An active SQLModel database session.
        source: Identifier for the subsystem where the error originated
                (e.g. "pipeline", "enrichment", "broker_assignment").
        message: Human-readable description of the error.  Should include
                 exception text where available.
        entity_id: Optional primary key of the DB record being processed
                   when the error occurred (bid.id, company.id, etc.).

    Returns:
        The newly created and committed SystemError instance.
    """
    error = SystemError(
        source=source,
        error_message=message,
        entity_id=entity_id,
    )
    session.add(error)
    session.commit()
    session.refresh(error)
    return error
