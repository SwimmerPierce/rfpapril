# Project Stack Research: Lead Generation & Web Scraping

## Recommended Stack (2025)

1. **Language: Python**
   - **Why**: Python is the absolute standard for web scraping. It has the richest ecosystem of libraries, most robust documentation, and is exceptionally friendly for AI coding companions.
   - **Alternative**: Node.js/TypeScript is also strong, but Python's data pipeline tools (Pandas if needed) and scraping robustness make it preferable.

2. **Web Scraping: Playwright (Python)**
   - **Why**: BC Bids is an ASP.NET application. These sites heavily rely on dynamically generated content, `__VIEWSTATE`, and complex asynchronous loading. Playwright handles complex interactions, rendering, and wait states far better than native Requests/BeautifulSoup.
   - **Avoid**: Selenium (slower, heavier overhead, harder to run headless gracefully on cheap PaaS).

3. **Database: PostgreSQL**
   - **Why**: Standard for production relational data. The requirement to map Opportunity IDs to bids and companies is inherently relational.
   - **Avoid**: MongoDB or NoSQL. The data has strict entity relationships (Projects to Bids to Companies).

4. **Task Scheduling: APScheduler or Platform Native Cron**
   - **Why**: A simple daily 3:00 AM job does not require heavy orchestration like Airflow, Prefect, or Dagster. Native cron on Railway/Render keeps costs minimal.

5. **CRM Sync: Zoho SDK or `httpx` (Async)**
   - **Why**: Official Zoho Python SDK is acceptable, but direct interaction using `httpx` and OAuth2 can sometimes be easier to debug with AI agents.

6. **Deployment: Railway or Render**
   - **Why**: Minimal DevOps overhead. "Push to deploy" from GitHub with managed PostgreSQL instances starting at $5/month. Fits the <$200/month budget perfectly.
