import argparse
import sys
import traceback
from src.scraper.bc_bids import scrape_unverified_results
from src.scraper.processor import process_results, log_system_error
from sqlmodel import Session
from src.database.session import init_db, get_engine
from src.processor.pipeline import run_post_scrape_pipeline

def run_scraper(dry_run: bool = False):
    """
    Main orchestration function for the BC Bids scraper.
    """
    print("Initializing Database...")
    init_db()
    
    print("Starting BC Bids Scraper...")
    try:
        results = scrape_unverified_results()
        print(f"Scraped {len(results)} results.")
        
        if dry_run:
            print("Dry Run: Not saving to database.")
            for res in results[:5]:
                print(res)
            return
            
        print("Processing results and saving to database...")
        saved, skipped = process_results(results)
        print(f"Done! Saved/Updated: {saved}, Skipped: {skipped}")

        print("Running post-scrape business logic pipeline...")
        try:
            with Session(get_engine()) as session:
                run_post_scrape_pipeline(session)
            print("Pipeline complete.")
        except Exception as pipeline_err:
            error_msg = f"Pipeline error (non-fatal): {traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            log_system_error("pipeline_main", error_msg)

    except Exception as e:
        error_msg = f"Fatal error in scraper orchestration: {traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        log_system_error("scraper_main", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BC Bids Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Scrape data but don't save to DB")
    parser.add_argument("--test-run", action="store_true", help="Alias for dry-run with mock data check")
    parser.add_argument("--trigger-failure", action="store_true", help="Force a failure for testing error handling")
    
    args = parser.parse_args()
    
    # Ensure DB is initialized before any operations
    init_db()
    
    if args.trigger_failure:
        print("Triggering intentional failure...")
        try:
            raise Exception("Intentional test failure triggered by --trigger-failure")
        except Exception as e:
            log_system_error("test_failure", traceback.format_exc())
            print("Error logged successfully.")
            sys.exit(0)
            
    run_scraper(dry_run=args.dry_run or args.test_run)
