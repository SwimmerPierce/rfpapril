# Domain Research Summary: BC Bids Lead Generation

## Overview

The standard approach for scraping state/provincial government sites (often legacy ASP.NET) is heavily leaning towards Python and Playwright, backed by a relational database like PostgreSQL. This domain requires high resilience to UI changes and strict handling of entity relationships before syncing to a CRM.

## Recommendations

- **Stack**: Python 3.11+, Playwright for accurate interaction with ASP.NET viewstates, PostgreSQL for the relational backbone, and deployment via Railway/Render for low DevOps overhead.
- **Table Stakes**: The system must run flawlessly unsupervised at 3:00 AM, deduplicate correctly, and NEVER drop an error silently.
- **Watch Out For**:
  - **ASP.NET Fragility**: Ensure Playwright is used over simple `requests` to handle `__VIEWSTATE` and JS rendering seamlessly.
  - **CRM Rate Limits**: Standardize bulk syncing logic to Zoho and ensure any network failure creates a persistent ticket in the Admin Dashboard, not a flooded inbox.
  - **Entity Normalization**: Ensure string matching on company names trims whitespace and enforces rigorous uniqueness constraints prior to CRM syncing.

Proceeding to Requirements Definition.
