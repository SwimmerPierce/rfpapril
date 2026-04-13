# Phase 3: Zoho CRM Integration - Research

**Researched:** 2026-04-13
**Domain:** CRM Integration, OAuth2, Zoho CRM API
**Confidence:** HIGH

## Summary

This phase focuses on syncing the local database state to Zoho CRM custom modules. The application database remains the source of truth, and a daily sync push occurs after the processing pipeline completes. Sync failures and other issues are logged to a Zoho-based Admin Queue.

**Primary recommendation:** Use direct REST API calls via `requests` for Zoho CRM interaction. The Zoho Python SDK is unnecessarily heavy for this specific set of custom modules. Implement a standard OAuth2 refresh-token flow to manage access tokens. Use the `upsert` API to maintain idempotency.

## Zoho CRM Configuration (Assumed from PRD)

### Custom Modules
| Module Name | API Name | Key Unique Field |
|-------------|----------|------------------|
| BC Bids Companies | `BC_Bids_Companies` | `Legal_Name` |
| BC Bids Projects | `BC_Bids_Projects` | `Opportunity_ID` |
| BC Bids Bids | `BC_Bids_Bids` | `Internal_ID` (Local DB PK) |
| Admin Queue | `Admin_Queue` | `Internal_ID` (Local DB PK) |

### OAuth Scopes Required
- `ZohoCRM.modules.ALL`
- `ZohoCRM.settings.ALL` (for metadata if needed)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | 2.32.5 | API calls | Industry standard, already used in Phase 2 for enrichment. |
| `python-dotenv` | 1.0.1 | Secret Management | For storing `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`. |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── integrations/
│   ├── __init__.py
│   └── zoho/
│       ├── __init__.py
│       ├── client.py        # OAuth and Base Request logic
│       ├── sync_service.py  # Orchestrates Entity-to-Zoho mapping
│       └── mapper.py        # Transforms SQLModel instances to Zoho JSON
└── main.py                  # Trigger sync after pipeline
```

### Pattern 1: Idempotent Sync (Upsert)
Use the Zoho `upsert` endpoint to ensure that running the sync multiple times doesn't create duplicate records.
**Endpoint:** `POST /crm/v7/{module}/upsert`

### Pattern 2: Token Management
Store the `refresh_token` in `.env`. Access tokens should be cached in memory or a temporary file and refreshed only when expired (401 response or 1-hour timer).

## Code Examples

### Zoho OAuth Refresh
```python
def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN"),
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    return response.json()["access_token"]
```

### Upsert Record
```python
def upsert_record(module, data, duplicate_check_fields):
    token = get_access_token()
    url = f"https://www.zohoapis.com/crm/v7/{module}/upsert"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    payload = {
        "data": [data],
        "duplicate_check_fields": duplicate_check_fields
    }
    return requests.post(url, headers=headers, json=payload)
```

## Common Pitfalls

### Pitfall 1: Multi-select & Lookup Fields
**What goes wrong:** Sending a string to a Lookup field.
**How to avoid:** Lookup fields in Zoho require an object: `{"id": "zoho_record_id"}`.

### Pitfall 2: API Rate Limits
**What goes wrong:** Exceeding daily API credits.
**How to avoid:** Batch records in groups of 100 (Zoho API max per call).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Custom Module API names follow standard snake_case. | Zoho Config | API calls will return 400. Need to verify in Zoho Setup. |
| A2 | `Legal_Name` is unique enough for Company upsert. | Zoho Config | Merging different companies with same name (rare but possible). |
| A3 | The client has already created the custom modules in Zoho. | Summary | Implementation will fail until modules exist. |

## Open Questions

1. **Data Center:** Is the client on `.com`, `.eu`, or `.ca`? (Defaulting to `.com`)
2. **Duplicate Check Fields:** Are the unique fields (Opportunity ID, Legal Name) marked as "Unique" in Zoho? This is required for the `upsert` API to work correctly.

## Validation Architecture

### Integration Tests
- `tests/test_zoho_sync.py`: Mock the Zoho API responses to verify mapping and batching logic.
- E2E test with a sandbox Zoho account if available.

## Security Domain

### Secret Protection
- Never log the `ZOHO_REFRESH_TOKEN`.
- Access tokens should be treated as sensitive but ephemeral.
- Use `pydantic-settings` or `python-dotenv` to ensure secrets are never committed.
