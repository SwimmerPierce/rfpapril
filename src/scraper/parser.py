from bs4 import BeautifulSoup
import re

def parse_unverified_results(html_content: str):
    """
    Parses the HTML content of the BC Bids unverified results page.
    Returns a list of dictionaries with extracted bid data.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # BC Bids table structure might vary, but assuming rows are <tr>
    # For now, we'll look for rows that look like data rows.
    # Often they have specific classes or are inside a main table.
    rows = soup.find_all('tr')
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
            
        # Basic heuristic to skip header rows
        # In a real scenario, we'd check for specific IDs or classes
        opp_id = cols[0].get_text(strip=True)
        if not opp_id or opp_id.lower() == 'opportunity id':
            continue
            
        project_name = cols[1].get_text(strip=True)
        bidder_name = cols[2].get_text(strip=True)
        raw_amount = cols[3].get_text(strip=True)
        
        # Clean amount: remove $, commas, and non-numeric chars except period
        amount_match = re.search(r'[\d,.]+', raw_amount)
        if amount_match:
            clean_amount_str = amount_match.group(0).replace(',', '')
            try:
                bid_amount = float(clean_amount_str)
            except ValueError:
                bid_amount = 0.0
        else:
            bid_amount = 0.0
            
        results.append({
            "opportunity_id": opp_id,
            "project_name": project_name,
            "bidder_name": bidder_name,
            "bid_amount": bid_amount
        })
        
    return results
