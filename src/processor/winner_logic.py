"""
Winner identification logic (PROC-01).

Identifies the lowest bid(s) for a project and marks them as is_winner=True.
All other bids for the same project are reset to is_winner=False.

Design notes:
- Uses a SQL-level min() subquery to avoid loading all bids into memory.
- Parameterized queries via SQLModel prevent SQL injection (T-02-01-01).
- Ties (multiple bids sharing the lowest amount) are all marked as winners.
"""
from sqlmodel import Session, func, select

from src.database.models import Bid


def flag_winners(session: Session, project_id: int) -> None:
    """Flag the lowest bid(s) for a project as winners.

    All bids for the given project are first reset to is_winner=False.
    Then the bid(s) matching the minimum amount are set to is_winner=True.

    Args:
        session: An active SQLModel database session.
        project_id: The primary key of the Project to process.
    """
    # Step 1: Reset all bids for this project to ensure no stale winner flags.
    bids = session.exec(
        select(Bid).where(Bid.project_id == project_id)
    ).all()
    for bid in bids:
        bid.is_winner = False

    # Step 2: Find the minimum bid amount using a SQL aggregate.
    min_amount = session.exec(
        select(func.min(Bid.amount)).where(Bid.project_id == project_id)
    ).one()

    if min_amount is None:
        # No bids for this project — nothing to do.
        session.commit()
        return

    # Step 3: Mark all bids at the minimum amount as winners (handles ties).
    winners = session.exec(
        select(Bid).where(
            Bid.project_id == project_id,
            Bid.amount == min_amount,
        )
    ).all()
    for winner in winners:
        winner.is_winner = True

    session.commit()
