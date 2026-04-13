import pytest
from sqlmodel import Session, select, create_mock_engine
from src.database.models import Project, Company, Bid, SystemError
from src.database.session import get_engine

def test_project_creation():
    project = Project(
        opportunity_id="OPP-123",
        name="Test Project",
        issuing_org="Test Org",
        url="http://example.com"
    )
    assert project.opportunity_id == "OPP-123"

def test_company_uniqueness_normalization():
    # This test will check if legal_name is indexed/unique and normalized
    # But since we're using SQLModel/SQLAlchemy, we'll just check if the model fields exist for now
    company = Company(legal_name="Test Company Ltd.")
    assert company.legal_name == "test company ltd."

def test_bid_relationships():
    project = Project(opportunity_id="P1", name="P1", issuing_org="O", url="U")
    company = Company(legal_name="C1")
    bid = Bid(amount=1000.50, is_winner=True, project=project, company=company)
    assert bid.amount == 1000.50
    assert bid.project.name == "P1"
    assert bid.company.legal_name == "c1"

def test_system_error():
    err = SystemError(source="Scraper", error_message="Timeout")
    assert err.source == "Scraper"
    assert err.resolved is False
