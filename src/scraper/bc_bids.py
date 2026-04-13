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
        
        all_results = []
        try:
            # Navigate to the results page
            page.goto(url, wait_until="networkidle")
            
            page_num = 1
            while page_num <= 10: # Limit to 10 pages for safety
                # Wait for the table to be visible/loaded
                page.wait_for_selector("table", timeout=15000)
                
                # Get the content
                html_content = page.content()
                
                # Use the parser to extract data
                results = parse_unverified_results(html_content)
                all_results.extend(results)
                
                # Check for "Next" button
                # BC Bids often uses a link with "Next" text or specific ID
                next_button = page.get_by_text("Next", exact=False).first
                if next_button.is_visible():
                    print(f"Navigating to page {page_num + 1}...")
                    next_button.click()
                    page.wait_for_load_state("networkidle")
                    page_num += 1
                else:
                    break
            
            return all_results
            
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
