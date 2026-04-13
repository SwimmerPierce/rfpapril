from src.scraper.processor import process_results
from src.database.session import init_db, engine
from src.database.models import Project, Company, Bid
from sqlmodel import Session, select

def test_persistence():
    print("Testing persistence...")
    init_db()
    
    mock_results = [
        {
            "opportunity_id": "TEST-001",
            "project_name": "Persistence Test Project",
            "bidder_name": "Test Company Alpha",
            "bid_amount": 123456.78
        },
        {
            "opportunity_id": "TEST-001",
            "project_name": "Persistence Test Project",
            "bidder_name": "Test Company Bravo",
            "bid_amount": 99999.00
        }
    ]
    
    saved, skipped = process_results(mock_results)
    print(f"First run: Saved={saved}, Skipped={skipped}")
    
    # Run again with same data - should skip
    saved2, skipped2 = process_results(mock_results)
    print(f"Second run: Saved={saved2}, Skipped={skipped2}")
    
    # Run with updated amount
    mock_results[0]["bid_amount"] = 150000.00
    saved3, skipped3 = process_results(mock_results)
    print(f"Third run (updated amount): Saved={saved3}, Skipped={skipped3}")
    
    # Verify in DB
    with Session(engine) as session:
        projects = session.exec(select(Project).where(Project.opportunity_id == "TEST-001")).all()
        companies = session.exec(select(Company).where(Company.legal_name.like("%test company%"))).all()
        bids = session.exec(select(Bid)).all()
        
        print(f"Found {len(projects)} projects.")
        print(f"Found {len(companies)} companies.")
        print(f"Found {len(bids)} bids total.")
        
        assert len(projects) == 1
        assert len(companies) == 2
        # Alpha and Bravo for TEST-001
        assert len(bids) >= 2
        
        alpha_bid = session.exec(
            select(Bid).join(Company).where(
                Bid.project_id == projects[0].id,
                Company.legal_name == "test company alpha"
            )
        ).first()
        print(f"Alpha bid amount: {alpha_bid.amount}")
        assert alpha_bid.amount == 150000.00

if __name__ == "__main__":
    test_persistence()
