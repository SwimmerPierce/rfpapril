"""
Broker assignment engine (PROC-02, PROC-03).

For a given Bid, finds all active Brokers whose BrokerMapping matches:
  1. The Bid's Project's issuing_org.
  2. The Bid's amount falls within [min_threshold, max_threshold].

Creates BidAssignment records for each matching Broker.
If no mapping matches, no records are created (Phase 3 will add the
unmapped-org queue that routes these to the Zoho Admin dashboard).

Design notes:
- All queries are parameterized via SQLModel to prevent SQL injection (T-02-01-01).
- Broker email addresses are only accessed internally — not logged or exposed externally (T-02-01-02).
- Inactive brokers are explicitly excluded to avoid sending leads to departed staff.
"""
from sqlmodel import Session, select

from src.database.models import Bid, BidAssignment, Broker, BrokerMapping, Project


def assign_brokers(session: Session, bid_id: int) -> list[BidAssignment]:
    """Assign all matching active brokers to a bid.

    Finds BrokerMapping rows whose issuing_org matches the bid's project and
    whose threshold range contains the bid amount. Creates one BidAssignment
    per matching broker.

    Args:
        session: An active SQLModel database session.
        bid_id: The primary key of the Bid to process.

    Returns:
        A list of newly created BidAssignment records (may be empty).
    """
    # Load the bid and its parent project.
    bid = session.get(Bid, bid_id)
    if bid is None:
        return []

    project = session.get(Project, bid.project_id)
    if project is None:
        return []

    # Find all BrokerMappings for the issuing org where the bid amount is in range.
    mappings = session.exec(
        select(BrokerMapping).where(
            BrokerMapping.issuing_org == project.issuing_org,
            BrokerMapping.min_threshold <= bid.amount,
            BrokerMapping.max_threshold >= bid.amount,
        )
    ).all()

    if not mappings:
        return []

    # Filter to active brokers only, then create assignments (idempotent).
    assignments: list[BidAssignment] = []
    for mapping in mappings:
        broker = session.get(Broker, mapping.broker_id)
        if broker is None or not broker.is_active:
            continue

        # Skip if assignment already exists (prevents duplicates on re-runs).
        existing = session.exec(
            select(BidAssignment).where(
                BidAssignment.bid_id == bid_id,
                BidAssignment.broker_id == broker.id,
            )
        ).first()
        if existing:
            assignments.append(existing)
            continue

        assignment = BidAssignment(bid_id=bid_id, broker_id=broker.id)
        session.add(assignment)
        assignments.append(assignment)

    if assignments:
        session.commit()
        for assignment in assignments:
            session.refresh(assignment)

    return assignments
