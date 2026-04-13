from typing import Any, Dict, Optional
from src.database.models import Project, Company, Bid, SystemError

def to_zoho_project(project: Project) -> Dict[str, Any]:
    """Map a Project model to a Zoho BC_Bids_Projects record."""
    return {
        "Opportunity_ID": project.opportunity_id,
        "Project_Name": project.name,
        "Issuing_Organization": project.issuing_org,
        "Date_Posted": project.date.strftime("%Y-%m-%d"),
        "BC_Bids_URL": project.url,
        # zoho_id is used for upsert tracking by the sync service, 
        # but if we have it, we should include it to ensure we update the right record
        "id": project.zoho_id
    }

def to_zoho_company(company: Company) -> Dict[str, Any]:
    """Map a Company model to a Zoho BC_Bids_Companies record."""
    data = {
        "Company_Name_Legal": company.legal_name,
        "Website": company.website_found,
        "id": company.zoho_id
    }
    
    # Optional fields from our current model
    if hasattr(company, 'dba_name'):
        data["DBA_Name"] = getattr(company, 'dba_name')
    if hasattr(company, 'head_office_address'):
        data["Head_Office_Address"] = getattr(company, 'head_office_address')
    if hasattr(company, 'office_phone'):
        data["Office_Phone"] = getattr(company, 'office_phone')
    if hasattr(company, 'office_email'):
        data["Office_Email"] = getattr(company, 'office_email')
    
    return data

def to_zoho_bid(bid: Bid, project_zoho_id: str, company_zoho_id: str) -> Dict[str, Any]:
    """Map a Bid model to a Zoho BC_Bids_Individual_Bids record."""
    return {
        "Project": {"id": project_zoho_id},
        "Company": {"id": company_zoho_id},
        "Bid_Amount": float(bid.amount),
        "Won": bid.is_winner,
        "id": bid.zoho_id
    }

def to_zoho_error(error: SystemError) -> Dict[str, Any]:
    """Map a SystemError to a Zoho Admin_Queue record."""
    return {
        "Issue_Type": error.source,
        "Description": error.error_message,
        "Related_Entity_ID": str(error.entity_id) if error.entity_id else None,
        "Status": "Resolved" if error.resolved else "Open",
        "id": error.zoho_id
    }
