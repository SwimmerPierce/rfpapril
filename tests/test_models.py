import pytest
from datetime import datetime
from sqlmodel import Session, select, create_mock_engine
from src.database.models import Project, Company, Bid, SystemError, ZohoSyncState
from src.database.session import get_engine

def test_project_creation():
    project = Project(
        opportunity_id="OPP-123",
        name="Test Project",
        issuing_org="Test Org",
        url="http://example.com",
        zoho_id="Z-123"
    )
    assert project.opportunity_id == "OPP-123"
    assert project.zoho_id == "Z-123"

def test_company_uniqueness_normalization():
    # This test will check if legal_name is indexed/unique and normalized
    # But since we're using SQLModel/SQLAlchemy, we'll just check if the model fields exist for now
    company = Company(legal_name="Test Company Ltd.", zoho_id="ZC-123")
    assert company.legal_name == "test company ltd."
    assert company.zoho_id == "ZC-123"

def test_bid_relationships():
    project = Project(opportunity_id="P1", name="P1", issuing_org="O", url="U")
    company = Company(legal_name="C1")
    bid = Bid(amount=1000.50, is_winner=True, project=project, company=company, zoho_id="ZB-123")
    assert bid.amount == 1000.50
    assert bid.project.name == "P1"
    assert bid.company.legal_name == "c1"
    assert bid.zoho_id == "ZB-123"

def test_system_error():
    err = SystemError(source="Scraper", error_message="Timeout", zoho_id="ZE-123")
    assert err.source == "Scraper"
    assert err.resolved is False
    assert err.zoho_id == "ZE-123"

def test_zoho_sync_state():
    sync = ZohoSyncState(module_name="Projects", last_sync=datetime.now())
    assert sync.module_name == "Projects"
    assert isinstance(sync.last_sync, datetime)
