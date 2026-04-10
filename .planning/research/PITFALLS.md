# Project Pitfalls Research

## Common Mistakes in Scraping & Syncing

1. **Fragility to DOM Changes**
   - **Warning Sign**: Scraper fails returning `NoneType` or element not found errors.
   - **Prevention**: Use resilient CSS/XPath selectors. Add data validation schemas (like Pydantic) immediately after scraping to ensure expected shapes before database insertion. Failure should cleanly write to Admin Queue.

2. **ASP.NET Session States**
   - **Warning Sign**: Infinite redirects, session timeouts, or empty query results.
   - **Prevention**: Playwright maintains session cookies natively. Avoid manual cookie management. Navigate from the front page to the search page as a real user would if direct linking fails.

3. **Zoho API Rate Limits**
   - **Warning Sign**: 429 Too Many Requests.
   - **Prevention**: Use bulk APIs where possible (up to 100 records per call) and implement exponential backoff + retries in the Zoho Sync module.

4. **Blind Company Matching**
   - **Warning Sign**: Duplicate companies in Zoho.
   - **Prevention**: Legal names on government bids are generally strict. Trust the exact string match, but trim whitespace and standardize casing. In the future, add fuzzy matching if duplicates appear.

5. **Google Places Enrichment False Positives**
   - **Warning Sign**: Contact info for `Smith Construction` in New York is added to a BC Bids company.
   - **Prevention**: Scope all Google Places queries to British Columbia, Canada explicitly.
