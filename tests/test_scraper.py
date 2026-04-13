import pytest
from src.scraper.parser import parse_unverified_results

def test_parse_unverified_results():
    sample_html = """
    <table>
        <tr class="header">
            <td>Opportunity ID</td>
            <td>Project Name</td>
            <td>Bidder Name</td>
            <td>Bid Amount</td>
        </tr>
        <tr class="row">
            <td>12345</td>
            <td>Test Project</td>
            <td>Acme Corp</td>
            <td>$100,000.00</td>
        </tr>
        <tr class="row">
            <td>12345</td>
            <td>Test Project</td>
            <td>Bravo Ltd</td>
            <td>$95,000.00</td>
        </tr>
        <tr class="row">
            <td>67890</td>
            <td>Another Project</td>
            <td>Charlie Inc</td>
            <td>$50,000.50</td>
        </tr>
    </table>
    """
    results = parse_unverified_results(sample_html)
    
    assert len(results) == 3
    
    assert results[0]["opportunity_id"] == "12345"
    assert results[0]["project_name"] == "Test Project"
    assert results[0]["bidder_name"] == "Acme Corp"
    assert results[0]["bid_amount"] == 100000.00
    
    assert results[2]["opportunity_id"] == "67890"
    assert results[2]["bidder_name"] == "Charlie Inc"
    assert results[2]["bid_amount"] == 50000.50
