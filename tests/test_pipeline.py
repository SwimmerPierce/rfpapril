"""
Integration and unit tests for the central processing pipeline (02-03).

Tests cover:
- run_post_scrape_pipeline: end-to-end orchestration of winner flagging,
  broker assignment, and company enrichment.
- log_processing_error: persistent error logging to the SystemError table.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from sqlmodel import Session, SQLModel, create_engine, select

from src.database.models import (
    Project, Company, Bid, Broker, BrokerMapping, BidAssignment, SystemError
)
from src.processor.pipeline import run_post_scrape_pipeline
from src.processor.error_queue import log_processing_error


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    """In-memory SQLite session, created fresh for every test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_project(session: Session, org: str = "Ministry of Highways", hours_ago: int = 1) -> Project:
    """Helper: create and persist a Project with date in the past."""
    project = Project(
        opportunity_id=f"OP-{id(org)}-{hours_ago}",
        name=f"Test Project - {org}",
        issuing_org=org,
        date=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        url="https://bcbids.example.com/test",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _make_company(session: Session, name: str = "ACME Ltd", unenriched: bool = True) -> Company:
    """Helper: create and persist a Company."""
    company = Company(legal_name=name)
    if not unenriched:
        company.website_found = "https://acme.example.com"
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _make_bid(session: Session, project: Project, company: Company, amount: Decimal) -> Bid:
    """Helper: create and persist a Bid."""
    bid = Bid(amount=amount, project_id=project.id, company_id=company.id)
    session.add(bid)
    session.commit()
    session.refresh(bid)
    return bid


def _make_broker(session: Session, org: str, min_t: Decimal = Decimal("0"), max_t: Decimal = Decimal("999999999")) -> Broker:
    """Helper: create a Broker + BrokerMapping for a given org."""
    broker = Broker(name="Test Broker", email=f"broker-{id(org)}@example.com", is_active=True)
    session.add(broker)
    session.commit()
    session.refresh(broker)

    mapping = BrokerMapping(
        issuing_org=org,
        broker_id=broker.id,
        min_threshold=min_t,
        max_threshold=max_t,
    )
    session.add(mapping)
    session.commit()
    return broker


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestRunPostScrapePipeline:
    """Tests for run_post_scrape_pipeline orchestration."""

    def test_pipeline_flags_winner_for_recent_project(self, session: Session):
        """Projects with bids within last 24 h should have winners flagged."""
        project = _make_project(session, hours_ago=2)
        company = _make_company(session, "Low Bidder Ltd")
        company2 = _make_company(session, "High Bidder Ltd")
        bid_low = _make_bid(session, project, company, Decimal("1000.00"))
        bid_high = _make_bid(session, project, company2, Decimal("2000.00"))

        with patch("src.processor.pipeline.enrich_company"):
            run_post_scrape_pipeline(session)

        session.refresh(bid_low)
        session.refresh(bid_high)
        assert bid_low.is_winner is True
        assert bid_high.is_winner is False

    def test_pipeline_skips_old_projects(self, session: Session):
        """Projects older than 24 h should not be re-processed."""
        project = _make_project(session, hours_ago=48)
        company = _make_company(session, "Old Bidder Ltd")
        bid = _make_bid(session, project, company, Decimal("500.00"))

        with patch("src.processor.pipeline.enrich_company"):
            run_post_scrape_pipeline(session)

        session.refresh(bid)
        # bid should remain unprocessed (is_winner stays False, not touched)
        assert bid.is_winner is False

    def test_pipeline_assigns_brokers_to_winner_bids(self, session: Session):
        """Winning bids should be assigned to matching brokers."""
        org = "Ministry of Highways"
        project = _make_project(session, org=org, hours_ago=1)
        company = _make_company(session, "Winner Corp")
        bid = _make_bid(session, project, company, Decimal("5000.00"))
        _make_broker(session, org=org)

        with patch("src.processor.pipeline.enrich_company"):
            run_post_scrape_pipeline(session)

        assignments = session.exec(
            select(BidAssignment).where(BidAssignment.bid_id == bid.id)
        ).all()
        assert len(assignments) == 1

    def test_pipeline_enriches_unenriched_companies(self, session: Session):
        """Companies without website_found should be enriched."""
        project = _make_project(session, hours_ago=1)
        company = _make_company(session, "Unenriched Corp", unenriched=True)
        _make_bid(session, project, company, Decimal("100.00"))

        with patch("src.processor.pipeline.enrich_company") as mock_enrich:
            run_post_scrape_pipeline(session)

        mock_enrich.assert_called_once_with(session, company.id)

    def test_pipeline_skips_already_enriched_companies(self, session: Session):
        """Companies with website_found should NOT be re-enriched."""
        project = _make_project(session, hours_ago=1)
        company = _make_company(session, "Enriched Corp", unenriched=False)
        _make_bid(session, project, company, Decimal("100.00"))

        with patch("src.processor.pipeline.enrich_company") as mock_enrich:
            run_post_scrape_pipeline(session)

        mock_enrich.assert_not_called()

    def test_pipeline_logs_error_on_assignment_failure(self, session: Session):
        """If assign_brokers raises, error should be logged and pipeline continues."""
        project = _make_project(session, hours_ago=1)
        company = _make_company(session, "Crash Corp")
        _make_bid(session, project, company, Decimal("100.00"))

        with patch("src.processor.pipeline.assign_brokers", side_effect=Exception("DB boom")):
            with patch("src.processor.pipeline.enrich_company"):
                run_post_scrape_pipeline(session)

        errors = session.exec(select(SystemError)).all()
        assert len(errors) >= 1
        assert any("DB boom" in e.error_message for e in errors)

    def test_pipeline_logs_error_on_enrichment_failure(self, session: Session):
        """If enrich_company raises, error should be logged and pipeline continues."""
        project = _make_project(session, hours_ago=1)
        company = _make_company(session, "Enrich Fail Corp", unenriched=True)
        _make_bid(session, project, company, Decimal("100.00"))

        with patch("src.processor.pipeline.enrich_company", side_effect=Exception("DDG down")):
            run_post_scrape_pipeline(session)

        errors = session.exec(select(SystemError)).all()
        assert len(errors) >= 1
        assert any("DDG down" in e.error_message for e in errors)


# ---------------------------------------------------------------------------
# Error logging tests
# ---------------------------------------------------------------------------

class TestLogProcessingError:
    """Tests for log_processing_error function."""

    def test_error_logging_creates_system_error_record(self, session: Session):
        """log_processing_error should insert a SystemError record."""
        log_processing_error(session, "pipeline", "Something went wrong", entity_id=42)

        errors = session.exec(select(SystemError)).all()
        assert len(errors) == 1
        error = errors[0]
        assert error.source == "pipeline"
        assert "Something went wrong" in error.error_message
        assert error.entity_id == 42
        assert error.resolved is False

    def test_error_logging_without_entity_id(self, session: Session):
        """log_processing_error should work with entity_id=None."""
        log_processing_error(session, "enrichment", "No website found", entity_id=None)

        errors = session.exec(select(SystemError)).all()
        assert len(errors) == 1
        assert errors[0].entity_id is None

    def test_error_logging_timestamp_is_set(self, session: Session):
        """SystemError timestamp should be set to a recent datetime."""
        before = datetime.now(timezone.utc)
        log_processing_error(session, "broker", "No mapping found", entity_id=7)
        after = datetime.now(timezone.utc)

        error = session.exec(select(SystemError)).first()
        assert error is not None
        # Timestamp should be between before and after (allow tz-naive SQLite)
        ts = error.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert before <= ts <= after

    def test_error_logging_multiple_errors(self, session: Session):
        """Multiple calls should create multiple independent records."""
        log_processing_error(session, "pipeline", "Error 1", entity_id=1)
        log_processing_error(session, "pipeline", "Error 2", entity_id=2)

        errors = session.exec(select(SystemError)).all()
        assert len(errors) == 2

    def test_error_logging_resolved_defaults_to_false(self, session: Session):
        """New errors should have resolved=False by default."""
        log_processing_error(session, "pipeline", "Unresolved error", entity_id=None)

        error = session.exec(select(SystemError)).first()
        assert error.resolved is False
