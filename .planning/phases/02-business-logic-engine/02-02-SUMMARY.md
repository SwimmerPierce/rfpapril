---
phase: 02-business-logic-engine
plan: "02"
subsystem: enrichment
tags: [enrichment, duckduckgo, beautifulsoup, tdd, company-discovery]
dependency_graph:
  requires: [src/database/models.py (Company model)]
  provides: [src/processor/enrichment.py]
  affects: [Company.website_found, Company.linkedin_found]
tech_stack:
  added: [duckduckgo-search>=6.3.7, beautifulsoup4>=4.13.0]
  patterns: [TDD red-green, mock-based unit testing, graceful error handling]
key_files:
  created:
    - src/processor/__init__.py
    - src/processor/enrichment.py
    - tests/test_enrichment.py
  modified:
    - requirements.txt
decisions:
  - "Use mocks for all external calls (DDG, requests) in tests to ensure deterministic, offline test runs"
  - "Restrict LinkedIn extraction to /company/ paths only (not personal profiles)"
  - "Noise domain list kept in a module-level constant for easy extension"
  - "enrich_company silently no-ops on unknown company IDs rather than raising"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-13"
  tasks_completed: 3
  files_created: 3
  files_modified: 1
---

# Phase 02 Plan 02: Company Enrichment Pipeline Summary

## One-liner

DuckDuckGo-powered website discovery and BeautifulSoup LinkedIn extraction, with a full TDD suite of 15 tests covering noise filtering, timeouts, and DB orchestration.

## What Was Built

The company enrichment pipeline (`src/processor/enrichment.py`) provides three public functions:

- `find_website(company_name)` — Queries DuckDuckGo for the company's official website, filters noise domains (LinkedIn, Facebook, YellowPages, etc.), and returns the first matching URL or `None`.
- `extract_linkedin(website_url)` — Fetches the company homepage and extracts `linkedin.com/company/` anchor links using BeautifulSoup. Returns the first match or `None` on any network/parse error.
- `enrich_company(session, company_id)` — Orchestrates the full flow: fetches the Company record, runs discovery, updates `website_found` and `linkedin_found`, and commits.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| TDD RED | Failing tests for enrichment pipeline | 8c422ba | tests/test_enrichment.py |
| TDD GREEN | Implement enrichment pipeline | a85096b | src/processor/enrichment.py, src/processor/__init__.py, requirements.txt |

## Test Results

```
21 passed in 0.49s (15 enrichment + 6 pre-existing)
```

All 15 new tests cover:
- `find_website`: valid result, noise filtering, empty results, all-noise, DDG exception
- `extract_linkedin`: anchor detection, no link, timeout, connection error, timeout param assertion, company-only filter
- `enrich_company`: website + LinkedIn, website only, no website (LinkedIn skipped), unknown ID

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-02-02-01 (DoS) | `requests.get` always called with `timeout=10` — verified by dedicated test `test_extract_linkedin_uses_timeout_on_request` |
| T-02-02-02 (Info Disclosure) | Only URLs stored in `website_found` / `linkedin_found`; no page content retained |

## Deviations from Plan

### Auto-added (Rule 2 - Missing critical functionality)

**1. [Rule 2 - Security] Extended noise domain list**
- **Found during:** Task 1 implementation
- **Issue:** Plan mentioned only LinkedIn, Facebook, YellowPages but additional noise sources (Twitter, Instagram, Yelp, BBB, Canada411) are equally common in DDG results for BC companies.
- **Fix:** Added 5 additional noise domains to `_NOISE_DOMAINS` constant.
- **Files modified:** src/processor/enrichment.py

**2. [Rule 2 - Missing test] Added timeout assertion test**
- **Found during:** Task 2 (extract_linkedin)
- **Issue:** Threat T-02-02-01 requires timeout on requests; plan did not include a test verifying the timeout parameter is actually passed.
- **Fix:** Added `test_extract_linkedin_uses_timeout_on_request` to enforce the security requirement in CI.
- **Files modified:** tests/test_enrichment.py

## Known Stubs

None. All functions return real data from mocked but correctly-typed interfaces.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers.

## Self-Check: PASSED

- [x] src/processor/enrichment.py exists
- [x] src/processor/__init__.py exists
- [x] tests/test_enrichment.py exists
- [x] Commit 8c422ba exists (test RED)
- [x] Commit a85096b exists (feat GREEN)
- [x] 21 tests pass (pytest tests/)
