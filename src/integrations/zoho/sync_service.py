import logging
from typing import List, Optional, Type, Any, Dict
from sqlmodel import Session, select
from src.database.models import Project, Company, Bid, SystemError
from src.integrations.zoho.client import ZohoClient
from src.integrations.zoho.mapper import (
    to_zoho_project, to_zoho_company, to_zoho_bid, to_zoho_error
)

logger = logging.getLogger(__name__)

class ZohoSyncService:
    # Module names in Zoho CRM
    MODULE_PROJECTS = "BC_Bids_Projects"
    MODULE_COMPANIES = "BC_Bids_Companies"
    MODULE_BIDS = "BC_Bids_Individual_Bids"
    MODULE_ERRORS = "Admin_Queue"

    def __init__(self, client: Optional[ZohoClient] = None):
        self.client = client or ZohoClient()

    def sync_companies(self, session: Session, batch_size: int = 100) -> int:
        """Find and sync companies to Zoho."""
        # Find companies that haven't been synced or have been modified (if we had a modified_at field)
        # For MVP, we'll sync those without zoho_id.
        companies = session.exec(select(Company).where(Company.zoho_id == None)).all()
        if not companies:
            return 0

        synced_count = 0
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            payload = {"data": [to_zoho_company(c) for c in batch]}
            
            try:
                # Use upsert with Company_Name_Legal as duplicate check field
                response = self.client.post(f"{self.MODULE_COMPANIES}/upsert", json={
                    **payload,
                    "duplicate_check_fields": ["Company_Name_Legal"]
                })
                
                self._process_upsert_response(batch, response, session)
                synced_count += len(batch)
            except Exception as e:
                logger.error(f"Failed to sync company batch: {e}")
                # Log to local DB as system error
                self._record_sync_error(session, "sync_companies", str(e))
        
        session.commit()
        return synced_count

    def sync_projects(self, session: Session, batch_size: int = 100) -> int:
        """Find and sync projects to Zoho."""
        projects = session.exec(select(Project).where(Project.zoho_id == None)).all()
        if not projects:
            return 0

        synced_count = 0
        for i in range(0, len(projects), batch_size):
            batch = projects[i:i + batch_size]
            payload = {"data": [to_zoho_project(p) for p in batch]}
            
            try:
                response = self.client.post(f"{self.MODULE_PROJECTS}/upsert", json={
                    **payload,
                    "duplicate_check_fields": ["Opportunity_ID"]
                })
                
                self._process_upsert_response(batch, response, session)
                synced_count += len(batch)
            except Exception as e:
                logger.error(f"Failed to sync project batch: {e}")
                self._record_sync_error(session, "sync_projects", str(e))
        
        session.commit()
        return synced_count

    def sync_bids(self, session: Session, batch_size: int = 100) -> int:
        """Find and sync bids to Zoho."""
        # Bids require both project and company to have zoho_ids
        bids = session.exec(
            select(Bid)
            .join(Project, Bid.project_id == Project.id)
            .join(Company, Bid.company_id == Company.id)
            .where(Bid.zoho_id == None)
            .where(Project.zoho_id != None)
            .where(Company.zoho_id != None)
        ).all()
        
        if not bids:
            return 0

        synced_count = 0
        for i in range(0, len(bids), batch_size):
            batch = bids[i:i + batch_size]
            
            # Map with linked Zoho IDs
            batch_data = []
            for bid in batch:
                batch_data.append(to_zoho_bid(
                    bid, 
                    bid.project.zoho_id, 
                    bid.company.zoho_id
                ))
            
            payload = {"data": batch_data}
            
            try:
                # Bids don't have a natural unique key from BC Bids besides (project, company)
                # Zoho doesn't support composite unique keys for upsert easily.
                # If we don't have zoho_id, we just post it.
                response = self.client.post(self.MODULE_BIDS, json=payload)
                
                self._process_upsert_response(batch, response, session)
                synced_count += len(batch)
            except Exception as e:
                logger.error(f"Failed to sync bid batch: {e}")
                self._record_sync_error(session, "sync_bids", str(e))
        
        session.commit()
        return synced_count

    def sync_errors(self, session: Session, batch_size: int = 100) -> int:
        """Sync system errors to Zoho Admin Queue."""
        errors = session.exec(select(SystemError).where(SystemError.zoho_id == None)).all()
        if not errors:
            return 0

        synced_count = 0
        for i in range(0, len(errors), batch_size):
            batch = errors[i:i + batch_size]
            payload = {"data": [to_zoho_error(e) for e in batch]}
            
            try:
                response = self.client.post(self.MODULE_ERRORS, json=payload)
                self._process_upsert_response(batch, response, session)
                synced_count += len(batch)
            except Exception as e:
                logger.error(f"Failed to sync error batch: {e}")
                # Don't record error sync errors in local DB to avoid infinite loop
                # Just log to console
        
        session.commit()
        return synced_count

    def _process_upsert_response(self, batch: List[Any], response: Dict[str, Any], session: Session):
        """Process the response from Zoho and update local records with zoho_id."""
        if "data" not in response:
            logger.warning(f"Unexpected response format from Zoho: {response}")
            return

        for record, res_item in zip(batch, response["data"]):
            if res_item.get("status") == "success":
                record.zoho_id = res_item.get("details", {}).get("id")
                session.add(record)
            elif res_item.get("status") == "error":
                logger.warning(f"Failed to sync record {record.id}: {res_item.get('message')}")
                # Could log individual record failure here

    def _record_sync_error(self, session: Session, source: str, message: str):
        """Record a sync error in the local database."""
        error = SystemError(
            source=source,
            error_message=f"Sync Error: {message}"
        )
        session.add(error)
        # Don't commit here, let the caller decide

    def sync_all(self, session: Session):
        """Orchestrate the sync order."""
        logger.info("Starting Zoho Sync")
        
        companies_synced = self.sync_companies(session)
        logger.info(f"Synced {companies_synced} companies")
        
        projects_synced = self.sync_projects(session)
        logger.info(f"Synced {projects_synced} projects")
        
        bids_synced = self.sync_bids(session)
        logger.info(f"Synced {bids_synced} bids")
        
        errors_synced = self.sync_errors(session)
        logger.info(f"Synced {errors_synced} errors")
        
        logger.info("Zoho Sync completed")
