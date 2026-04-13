from decimal import Decimal
from typing import List, Dict, Any
from sqlmodel import Session, select, create_engine
from src.database.models import Project, Company, Bid, SystemError
from src.database.session import engine
import traceback

def process_results(results: List[Dict[str, Any]]):
    """
    Saves extracted results to the database with deduplication logic.
    """
    total_saved = 0
    total_skipped = 0
    
    with Session(engine) as session:
        for item in results:
            try:
                # 1. Normalize and find/create Project
                opp_id = item["opportunity_id"]
                project_name = item["project_name"]
                
                project = session.exec(
                    select(Project).where(Project.opportunity_id == opp_id)
                ).first()
                
                if not project:
                    project = Project(
                        opportunity_id=opp_id,
                        name=project_name,
                        issuing_org="BC Bids", # Default for now
                        url=f"https://www.bcbid.gov.bc.ca/open.dll/showOpportunity?id={opp_id}" # Tentative
                    )
                    session.add(project)
                    session.flush() # Get project.id
                
                # 2. Normalize and find/create Company
                legal_name = item["bidder_name"].lower().strip()
                company = session.exec(
                    select(Company).where(Company.legal_name == legal_name)
                ).first()
                
                if not company:
                    company = Company(legal_name=legal_name)
                    session.add(company)
                    session.flush() # Get company.id
                
                # 3. Create or update Bid
                bid_amount = Decimal(str(item["bid_amount"]))
                
                existing_bid = session.exec(
                    select(Bid).where(
                        Bid.project_id == project.id,
                        Bid.company_id == company.id
                    )
                ).first()
                
                if existing_bid:
                    if existing_bid.amount != bid_amount:
                        existing_bid.amount = bid_amount
                        total_saved += 1
                    else:
                        total_skipped += 1
                else:
                    new_bid = Bid(
                        amount=bid_amount,
                        project_id=project.id,
                        company_id=company.id
                    )
                    session.add(new_bid)
                    total_saved += 1
                
                session.commit()
                
            except Exception as e:
                session.rollback()
                print(f"Error processing item {item}: {e}")
                log_system_error("processor", f"Error processing item {item}: {traceback.format_exc()}")
                
    return total_saved, total_skipped

def log_system_error(source: str, message: str):
    """Logs an error to the SystemError table."""
    try:
        # Use a new session for logging errors to ensure it commits even if other things fail
        with Session(engine) as session:
            error = SystemError(source=source, error_message=message)
            session.add(error)
            session.commit()
    except Exception as e:
        print(f"Failed to log system error: {e}")
