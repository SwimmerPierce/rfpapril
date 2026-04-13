from playwright.sync_api import sync_playwright
from src.scraper.parser import parse_unverified_results
import time

def scrape_unverified_results():
    """
    Navigates to BC Bids Unverified Results page and returns extracted data.
    """
    url = "https://www.bcbid.gov.bc.ca/open.dll/showUnverifiedBidResults?mid=1"
    
    with sync_playwright() as p:
        # Launching browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to the results page
            page.goto(url, wait_until="networkidle")
            
            # Wait for the table to be visible/loaded. 
            # In a real scenario, we might need a specific selector.
            # Assuming there's some table with results.
            page.wait_for_selector("table", timeout=15000)
            
            # Get the content
            html_content = page.content()
            
            # Use the parser to extract data
            results = parse_unverified_results(html_content)
            
            return results
            
        except Exception as e:
            print(f"Scraping failed: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    data = scrape_unverified_results()
    print(f"Extracted {len(data)} results.")
    for res in data[:5]:
        print(res)
