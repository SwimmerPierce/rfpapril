import pytest
from unittest.mock import MagicMock, patch
from sqlmodel import Session, create_engine, SQLModel, select
from src.database.models import Project, Company, Bid, SystemError
from src.integrations.zoho.sync_service import ZohoSyncService
from src.integrations.zoho.client import ZohoClient
from decimal import Decimal

@pytest.fixture(name="session")
def session_fixture():
    # Use an in-memory SQLite database for testing
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="zoho_client")
def zoho_client_fixture():
    # Mock ZohoClient
    return MagicMock(spec=ZohoClient)

@pytest.fixture(name="sync_service")
def sync_service_fixture(zoho_client):
    return ZohoSyncService(client=zoho_client)

def test_sync_companies_success(session, sync_service, zoho_client):
    """Test successful sync of companies to Zoho."""
    # Add a company to sync
    company = Company(legal_name="Test Company 1")
    session.add(company)
    session.commit()
    
    # Mock Zoho response for upsert
    zoho_client.post.return_value = {
        "data": [
            {
                "status": "success",
                "details": {"id": "ZOHO_CO_1"}
            }
        ]
    }
    
    count = sync_service.sync_companies(session)
    
    assert count == 1
    session.refresh(company)
    assert company.zoho_id == "ZOHO_CO_1"
    
    # Check that post was called with correct data
    zoho_client.post.assert_called_once()
    args, kwargs = zoho_client.post.call_args
    assert "BC_Bids_Companies/upsert" in args[0]
    assert kwargs["json"]["data"][0]["Company_Name_Legal"] == "test company 1" # Lowercase due to model init

def test_sync_projects_success(session, sync_service, zoho_client):
    """Test successful sync of projects to Zoho."""
    project = Project(opportunity_id="OP-001", name="Project 1", issuing_org="Gov", url="http://test")
    session.add(project)
    session.commit()
    
    zoho_client.post.return_value = {
        "data": [
            {
                "status": "success",
                "details": {"id": "ZOHO_PR_1"}
            }
        ]
    }
    
    count = sync_service.sync_projects(session)
    
    assert count == 1
    session.refresh(project)
    assert project.zoho_id == "ZOHO_PR_1"

def test_sync_bids_success(session, sync_service, zoho_client):
    """Test successful sync of bids to Zoho."""
    # Bid requires company and project with zoho_ids
    company = Company(legal_name="Test Co", zoho_id="ZOHO_CO_1")
    project = Project(opportunity_id="OP-1", name="Pr 1", issuing_org="G", url="http://", zoho_id="ZOHO_PR_1")
    session.add(company)
    session.add(project)
    session.commit()
    
    # Refresh to ensure relationships are loaded or accessible
    session.refresh(company)
    session.refresh(project)
    
    bid = Bid(amount=Decimal("100.00"), is_winner=True, company_id=company.id, project_id=project.id)
    session.add(bid)
    session.commit()
    
    # Reload bid to ensure relationships are wired
    session.refresh(bid)
    
    zoho_client.post.return_value = {
        "data": [
            {
                "status": "success",
                "details": {"id": "ZOHO_BID_1"}
            }
        ]
    }
    
    count = sync_service.sync_bids(session)
    
    assert count == 1
    session.refresh(bid)
    assert bid.zoho_id == "ZOHO_BID_1"
    
    # Verify mapping
    args, kwargs = zoho_client.post.call_args
    bid_data = kwargs["json"]["data"][0]
    assert bid_data["Project"] == {"id": "ZOHO_PR_1"}
    assert bid_data["Company"] == {"id": "ZOHO_CO_1"}
    assert bid_data["Bid_Amount"] == 100.0

def test_sync_partial_failure(session, sync_service, zoho_client):
    """Test handling of partial failure in a batch."""
    # Two companies, one fails in Zoho
    c1 = Company(legal_name="Co 1")
    c2 = Company(legal_name="Co 2")
    session.add(c1)
    session.add(c2)
    session.commit()
    
    zoho_client.post.return_value = {
        "data": [
            {
                "status": "success",
                "details": {"id": "ZOHO_CO_1"}
            },
            {
                "status": "error",
                "message": "Invalid field value"
            }
        ]
    }
    
    count = sync_service.sync_companies(session)
    
    assert count == 2 # Attempted 2
    session.refresh(c1)
    session.refresh(c2)
    assert c1.zoho_id == "ZOHO_CO_1"
    assert c2.zoho_id == None

def test_sync_exception_handling(session, sync_service, zoho_client):
    """Test handling of network/API exceptions during sync."""
    company = Company(legal_name="Error Co")
    session.add(company)
    session.commit()
    
    # Mock an exception
    zoho_client.post.side_effect = Exception("API Down")
    
    count = sync_service.sync_companies(session)
    
    # count will be 0 because it caught the exception before returning synced count
    # (actually in my implementation it returns synced_count which is 0)
    assert count == 0
    
    # Verify an error was recorded in the DB
    errors = session.exec(select(SystemError)).all()
    assert len(errors) == 1
    assert "sync_companies" in errors[0].source
    assert "API Down" in errors[0].error_message

def test_sync_errors_success(session, sync_service, zoho_client):
    """Test successful sync of system errors to Zoho."""
    error = SystemError(source="test_source", error_message="Test Error Message", entity_id=123)
    session.add(error)
    session.commit()
    
    zoho_client.post.return_value = {
        "data": [
            {
                "status": "success",
                "details": {"id": "ZOHO_ERR_1"}
            }
        ]
    }
    
    count = sync_service.sync_errors(session)
    
    assert count == 1
    session.refresh(error)
    assert error.zoho_id == "ZOHO_ERR_1"
    
    # Verify mapping
    args, kwargs = zoho_client.post.call_args
    error_data = kwargs["json"]["data"][0]
    assert error_data["Issue_Type"] == "test_source"
    assert error_data["Description"] == "Test Error Message"
    assert error_data["Related_Entity_ID"] == "123"
    assert error_data["Status"] == "Open"
