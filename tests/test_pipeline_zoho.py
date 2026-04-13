import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from sqlmodel import Session, SQLModel, create_engine, select

from src.database.models import (
    Project, Company, Bid, SystemError
)
from src.processor.pipeline import run_post_scrape_pipeline

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def _make_project(session: Session, hours_ago: int = 1) -> Project:
    project = Project(
        opportunity_id=f"OP-{hours_ago}",
        name=f"Test Project",
        issuing_org="Gov",
        date=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        url="https://bcbids.example.com/test",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

def _make_company(session: Session, name: str = "ACME Ltd") -> Company:
    company = Company(legal_name=name)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company

def _make_bid(session: Session, project: Project, company: Company, amount: Decimal) -> Bid:
    bid = Bid(amount=amount, project_id=project.id, company_id=company.id)
    session.add(bid)
    session.commit()
    session.refresh(bid)
    return bid

def test_pipeline_triggers_zoho_sync(session):
    """Verify that the pipeline triggers Zoho sync at the end."""
    project = _make_project(session, hours_ago=2)
    company = _make_company(session, "Sync Co")
    _make_bid(session, project, company, Decimal("1000.00"))
    
    with patch("src.integrations.zoho.sync_service.ZohoSyncService.sync_all") as mock_sync:
        # Mock other steps to avoid side effects or complex setup
        with patch("src.processor.pipeline.flag_winners"), \
             patch("src.processor.pipeline.assign_brokers"), \
             patch("src.processor.pipeline.enrich_company"):
            
            run_post_scrape_pipeline(session)
            
            mock_sync.assert_called_once_with(session)

def test_pipeline_logs_error_if_zoho_sync_fails(session):
    """Verify that a Zoho sync failure doesn't crash the pipeline and is logged."""
    project = _make_project(session, hours_ago=2)
    
    with patch("src.integrations.zoho.sync_service.ZohoSyncService.sync_all", side_effect=Exception("Zoho Down")):
        # Mock other steps
        with patch("src.processor.pipeline.flag_winners"), \
             patch("src.processor.pipeline.assign_brokers"), \
             patch("src.processor.pipeline.enrich_company"):
            
            run_post_scrape_pipeline(session)
            
    # Check if error was logged
    errors = session.exec(select(SystemError)).all()
    assert any("Zoho sync orchestration failed" in e.error_message for e in errors)
    assert any("Zoho Down" in e.error_message for e in errors)
