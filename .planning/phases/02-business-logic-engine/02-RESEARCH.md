# Phase 2: Business Logic Engine - Research

**Researched:** 2026-04-13
**Domain:** Business Logic, Data Processing, Enrichment Pipelines, CRM Integration
**Confidence:** HIGH

## Summary

This phase focuses on the "intelligence" layer of the BC Bids platform. After the scraper extracts raw data, the Business Logic Engine must transform it into actionable leads by identifying winners, matching projects to the correct insurance brokers, and enriching new company profiles with contact data.

**Primary recommendation:** Use a modular `ProcessingService` that operates on a "Pull" model from the database, handling batches of unverified bids. For enrichment, leverage free search tools (DuckDuckGo) initially to respect the $200/mo budget, while using a persistent local `SystemError` table to track "Issues" that will sync to the Zoho Admin Queue.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlmodel` | 0.0.38 | ORM / Data Modeling | Already used in Phase 1; provides Pydantic validation for DB records. |
| `requests` | 2.32.5 | API calls & Scraping | Industry standard for REST APIs (Zoho) and simple web fetching. |
| `beautifulsoup4` | 4.13.5 | HTML Parsing | Excellent for extracting links (LinkedIn) and contact info from company websites. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `duckduckgo-search` | 6.3.7+ | Company Search | To find company websites from legal names without a paid API. |
| `python-dotenv` | 1.2.2 | Config Management | For storing Zoho CRM credentials and broker threshold configs. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `duckduckgo-search` | `Serper` or `Tavily` | Paid APIs offer higher reliability but introduce recurring costs (~$30-50/mo). |
| `zohocrmsdk` | `requests` (Direct API) | SDK is complex to initialize; direct API is lighter and easier to debug for custom modules. |

**Installation:**
```bash
pip install duckduckgo-search beautifulsoup4 requests
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── database/
│   ├── models.py        # Added Broker, Mapping, and AdminQueue models
│   └── session.py
├── processor/
│   ├── __init__.py
│   ├── winner_logic.py  # PROC-01
│   ├── broker_engine.py # PROC-02, PROC-03
│   ├── enrichment.py    # PROC-04
│   └── error_queue.py   # ADMIN-01
└── main.py              # Orchestrates the post-scrape pipeline
```

### Pattern 1: Batch Identification Service
To identify winners (PROC-01), use a set-based SQL approach rather than looping in Python to ensure performance as the database grows.
**Example:**
```python
# Identify lowest bid for a project
min_bid_subquery = select(func.min(Bid.amount)).where(Bid.project_id == project_id)
winner_bid = session.exec(select(Bid).where(Bid.project_id == project_id, Bid.amount == min_bid_subquery)).first()
if winner_bid:
    winner_bid.is_winner = True
```

### Anti-Patterns to Avoid
- **Hard-coding Broker Rules:** Avoid `if issuing_org == "City of Vancouver": broker = "John"`. Use a database-driven `BrokerMapping` table. [VERIFIED: General Architecture Pattern]
- **Synchronous Enrichment during Scraping:** Enrichment involves external network calls that can fail or be slow. It should be a separate background task. [CITED: GSD Architecture Patterns]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Google Search | Custom Scraper | `duckduckgo-search` | Google blocks raw scrapers quickly; DDGS/Serper handle this. |
| Contact Extraction | Custom Regex Only | `BeautifulSoup` + Regex | HTML structures vary wildly; soup handles malformed tags better. |
| Zoho OAuth | Custom Token Store | `requests` + `dotenv` | Simple refresh-token flow is safer and easier to maintain. |

## Common Pitfalls

### Pitfall 1: "Legal Name" Mismatches in Search
**What goes wrong:** Searching for "123456 B.C. Ltd" might return no results or generic registry links.
**Why it happens:** Legal names in bid data don't always match the brand name on the website.
**How to avoid:** Append context to the search query (e.g., `"{name} official website bc bids"`).
**Warning signs:** Enrichment `website_found` rate below 50%.

### Pitfall 2: Zoho CRM Custom Field API Names
**What goes wrong:** `requests.post` fails with "invalid field name".
**Why it happens:** Zoho display names (e.g., "Project Name") differ from API names (e.g., "Project_Name").
**How to avoid:** Always verify API names in **Setup > Developer Space > APIs > API Names**. [VERIFIED: Zoho API Docs]

## Code Examples

### PROC-01: Winner Flagging (SQLModel)
```python
from sqlmodel import Session, select, func
from src.database.models import Bid

def flag_winners(session: Session, project_id: int):
    # Reset all bids for the project
    bids = session.exec(select(Bid).where(Bid.project_id == project_id)).all()
    for b in bids: b.is_winner = False
    
    # Find min amount
    min_amount = session.exec(select(func.min(Bid.amount)).where(Bid.project_id == project_id)).one()
    
    # Flag bid(s) with min amount
    winners = session.exec(select(Bid).where(Bid.project_id == project_id, Bid.amount == min_amount)).all()
    for w in winners:
        w.is_winner = True
    session.commit()
```

### PROC-04: Enrichment Pipeline (Initial DDGS)
```python
from duckduckgo_search import DDGS

def find_website(company_name: str):
    with DDGS() as ddgs:
        # Search for official website
        results = ddgs.text(f"{company_name} official website", max_results=3)
        for r in results:
            url = r['href']
            # Filter out social media noise
            if not any(x in url for x in ['linkedin.com', 'facebook.com', 'yellowpages.ca']):
                return url
    return None
```

### ADMIN-01/02: Zoho Issue Recording (Logic)
```python
def log_issue_for_zoho(session: Session, source: str, message: str, entity_id: int = None):
    # Record locally first
    error = SystemError(source=source, error_message=message, entity_id=entity_id)
    session.add(error)
    session.commit()
    # Phase 3 will sync these to the Zoho "Admin_Queue" custom module
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `duckduckgo-search` is sufficient for initial enrichment. | Standard Stack | Lower website hit rate; might need paid Serper API. |
| A2 | Broker assignments are 1:1 or 1:N based on Organization. | Architecture | If assignment logic is more complex (territories, etc.), schema needs update. |
| A3 | LinkedIn URLs can be found on company homepage. | Common Pitfalls | If companies don't link LinkedIn on site, discovery will fail. |

## Open Questions

1. **Broker Configuration Storage:** Should brokers be managed in a local DB table or should they be pulled from Zoho?
   - *Recommendation:* Keep a local `Broker` and `BrokerMapping` table for speed, and create a "Sync Brokers" task in Phase 3.
2. **Contact Info Depth:** What specific contact info is needed (Email, Phone, Person Name)?
   - *Recommendation:* Start with Website/LinkedIn. If specific emails are needed, we may need a paid tool like Hunter.io later.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.14.0a4 | — |
| PostgreSQL | Database | ✓ | (Local/Docker) | SQLite |
| requests | Zoho API | ✓ | 2.32.5 | — |
| duckduckgo-search | Enrichment | ✗ | — | `pip install` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_logic.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROC-01 | Flag lowest bid as winner | Unit | `pytest tests/test_logic.py::test_winner_logic` | ❌ Wave 0 |
| PROC-02 | Assign broker via Org | Unit | `pytest tests/test_logic.py::test_broker_assignment` | ❌ Wave 0 |
| PROC-04 | Find website via DDGS | Integration | `pytest tests/test_enrichment.py` | ❌ Wave 0 |

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | SQLModel / Pydantic for data integrity |
| V6 Cryptography | yes | Securely store Zoho Refresh Tokens in Environment Variables |

### Known Threat Patterns for Python/Zoho
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token Leakage | Information Disclosure | Never log full Authorization headers or Access Tokens. |
| SQL Injection | Tampering | Use SQLModel `select` and `exec` (parameterized queries). |

## Sources

### Primary (HIGH confidence)
- `sqlmodel` official docs - Model relationships and queries.
- Zoho CRM API Reference - Custom module record creation.
- Python `requests` docs - REST interactions.

### Secondary (MEDIUM confidence)
- `duckduckgo-search` GitHub - Usage and rate limits.
- Community patterns for company enrichment.

## Metadata
**Confidence breakdown:**
- Standard stack: HIGH - Libraries are mature and standard.
- Architecture: HIGH - Modular processing is a proven pattern for scrapers.
- Pitfalls: MEDIUM - Enrichment success rates are inherently variable.

**Research date:** 2026-04-13
**Valid until:** 2026-05-13
