"""
Central processing pipeline (PROC-01 through PROC-04).

Orchestrates all post-scrape business logic in a single call:
  1. Find all Projects updated within the last 24 hours.
  2. Flag the lowest bid(s) as winners.
  3. Assign brokers to every bid in those projects.
  4. Enrich any Company that hasn't been processed yet (website_found is None).
  5. Sync all new/updated records to Zoho CRM.

All per-item failures are caught and written to the SystemError table so a
single bad record never aborts the rest of the run (T-02-03-01).

Enrichment is skipped for companies that already have a website_found value,
preventing infinite retry loops on dead sites (T-02-03-02).
"""
import traceback
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from src.database.models import Bid, Company, Project
from src.processor.broker_engine import assign_brokers
from src.processor.enrichment import enrich_company
from src.processor.error_queue import log_processing_error
from src.processor.winner_logic import flag_winners

# Look-back window for "recent" projects.
_LOOKBACK_HOURS = 24


def run_post_scrape_pipeline(session: Session) -> None:
    """Run the full post-scrape business logic pipeline.

    Processes all projects whose date falls within the last 24 hours:
      - Winner flagging via flag_winners()
      - Broker assignment via assign_brokers() for every bid
      - Company enrichment via enrich_company() for companies without a website

    Per-item exceptions are logged to SystemError and execution continues with
    the next item so one failure never silently drops subsequent records.

    Args:
        session: An active SQLModel database session.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)

    # -----------------------------------------------------------------------
    # Step 1: Load recent projects.
    # -----------------------------------------------------------------------
    recent_projects = session.exec(
        select(Project).where(Project.date >= cutoff)
    ).all()

    processed_company_ids: set[int] = set()

    for project in recent_projects:
        # -------------------------------------------------------------------
        # Step 2: Flag winners for this project.
        # -------------------------------------------------------------------
        try:
            flag_winners(session, project.id)
        except Exception:
            log_processing_error(
                session,
                source="pipeline.flag_winners",
                message=f"Winner flagging failed for project {project.id}: {traceback.format_exc()}",
                entity_id=project.id,
            )
            # Continue — try broker assignment even if winner logic failed.

        # -------------------------------------------------------------------
        # Step 3: Assign brokers to every bid in this project.
        # -------------------------------------------------------------------
        bids = session.exec(
            select(Bid).where(Bid.project_id == project.id)
        ).all()

        for bid in bids:
            try:
                assign_brokers(session, bid.id)
            except Exception:
                log_processing_error(
                    session,
                    source="pipeline.assign_brokers",
                    message=f"Broker assignment failed for bid {bid.id}: {traceback.format_exc()}",
                    entity_id=bid.id,
                )

            # Track company IDs for the enrichment step below.
            if bid.company_id is not None:
                processed_company_ids.add(bid.company_id)

    # -----------------------------------------------------------------------
    # Step 4: Enrich companies that have not yet been processed.
    # We only enrich companies linked to recent projects and whose
    # website_found is still None (prevents re-enriching on every run).
    # -----------------------------------------------------------------------
    for company_id in processed_company_ids:
        company = session.get(Company, company_id)
        if company is None or company.website_found is not None:
            continue

        try:
            enrich_company(session, company_id)
        except Exception:
            log_processing_error(
                session,
                source="pipeline.enrich_company",
                message=f"Enrichment failed for company {company_id}: {traceback.format_exc()}",
                entity_id=company_id,
            )

    # -----------------------------------------------------------------------
    # Step 5: Sync all data to Zoho CRM.
    # We call sync_all() to push companies, projects, bids, and system errors.
    # -----------------------------------------------------------------------
    try:
        from src.integrations.zoho.sync_service import ZohoSyncService
        sync_service = ZohoSyncService()
        sync_service.sync_all(session)
    except Exception:
        log_processing_error(
            session,
            source="pipeline.zoho_sync",
            message=f"Zoho sync orchestration failed: {traceback.format_exc()}",
        )
