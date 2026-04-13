---
phase: 02
status: issues
reviewed: 2026-04-13
---

# Phase 02: Code Review Report — Business Logic Engine

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

---

## Summary

Phase 02 introduced broker data models, winner identification, broker assignment, company enrichment via DuckDuckGo/BeautifulSoup, a pipeline orchestrator, and a persistent error queue. The overall design is solid: queries are parameterized, per-item failures are isolated, and timeouts are set on outbound HTTP calls.

However, three issues require attention before this code is production-ready:

1. **Critical — SSRF:** `extract_linkedin` fetches an arbitrary URL returned from a DuckDuckGo search result without any scheme or host validation. An attacker who can influence DuckDuckGo results (or who has inserted a malicious `BrokerMapping.issuing_org`) could force internal-network requests.
2. **High — `get_session` misuse in `main.py`:** `get_session()` is a plain generator (`yield`-based), not a `@contextmanager`. Calling `with get_session() as session:` does not behave as intended — it calls `__enter__` on the generator object (which is not a context manager), almost certainly raising a `TypeError` at runtime.
3. **High — Duplicate `BidAssignment` rows:** `assign_brokers` is called for every bid on every pipeline run but has no guard against inserting duplicate `(bid_id, broker_id)` pairs. There is no unique constraint on `BidAssignment`. Re-running the pipeline within the 24-hour window will create duplicate assignment rows.

Five lower-severity findings are also documented below.

---

## Summary Table

| ID    | Severity | File                        | Line(s) | Issue                                                   |
|-------|----------|-----------------------------|---------|----------------------------------------------------------|
| CR-01 | Critical | `src/processor/enrichment.py` | 79–89   | SSRF — unvalidated external URL fetched without scheme/host checks |
| HR-01 | High     | `src/main.py`               | 33      | `get_session()` is a generator, not a context manager — `with` statement fails at runtime |
| HR-02 | High     | `src/processor/broker_engine.py` | 64–66 | Duplicate `BidAssignment` rows created on repeated pipeline runs |
| WR-01 | Warning  | `src/processor/winner_logic.py` | 28–32 | Session state may be stale after early commit — stale `is_winner=False` resets not flushed before min query |
| WR-02 | Warning  | `src/processor/enrichment.py` | 88–89  | LinkedIn URL stored verbatim from page HTML — may be a relative path or javascript: URI |
| WR-03 | Warning  | `src/processor/error_queue.py` | 33      | `message` field has no length cap — very long tracebacks may exceed DB column limits |
| IN-01 | Info     | `src/database/models.py`    | 24      | `google_found` field defined but never written by any Phase 02 code |
| IN-02 | Info     | `src/processor/enrichment.py` | 90      | `except (requests.exceptions.RequestException, Exception)` — redundant; `Exception` already covers everything |

---

## Critical Issues

### CR-01: SSRF — unvalidated URL passed to `requests.get`

**File:** `src/processor/enrichment.py:79`

**Issue:** `extract_linkedin(website_url)` calls `requests.get(website_url, ...)` where `website_url` is the raw string returned from `find_website()`. That value comes directly from the `"href"` field of a DuckDuckGo search result with no scheme or host validation. If a search result contains a `file://`, `ftp://`, `http://169.254.169.254/...` (AWS metadata), or `http://localhost/...` URL, the bot will make a request to that destination. Additionally, `extract_linkedin` is a public function — any caller passing an untrusted URL has full SSRF reach.

**Attack surface:** Any company name that can be influenced to produce a poisoned DuckDuckGo result (or any future caller supplying an unvalidated URL) triggers this.

**Fix:**
```python
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}

def _is_safe_url(url: str) -> bool:
    """Return True only for public http/https URLs."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False
    hostname = parsed.hostname or ""
    # Block localhost and link-local addresses
    blocked_prefixes = ("localhost", "127.", "0.", "10.", "192.168.", "169.254.")
    if any(hostname.startswith(p) for p in blocked_prefixes):
        return False
    return True


def extract_linkedin(website_url: str) -> Optional[str]:
    if not _is_safe_url(website_url):
        return None
    # ... rest of existing code ...
```

Apply the same `_is_safe_url` guard inside `find_website` before returning a result.

---

## High Issues

### HR-01: `get_session()` is a generator, not a context manager

**File:** `src/main.py:33`

**Issue:** `session.py` defines `get_session` as:
```python
def get_session():
    with Session(engine) as session:
        yield session
```
This is a raw generator function, **not** decorated with `@contextmanager`. Calling `with get_session() as session:` in `main.py` line 33 invokes `__enter__` on a bare generator object, which raises `AttributeError: __enter__` (Python 3.10+) or silently produces undefined behaviour in earlier versions. The pipeline will never run.

**Fix — Option A (minimal, recommended):** Add `@contextmanager` decorator in `session.py`:
```python
from contextlib import contextmanager

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
```

**Fix — Option B:** Change `main.py` to not use the generator as a context manager:
```python
session_gen = get_session()
session = next(session_gen)
try:
    run_post_scrape_pipeline(session)
finally:
    try:
        next(session_gen)
    except StopIteration:
        pass
```
Option A is far cleaner. Note that `get_session` is also used in FastAPI dependency injection elsewhere (where bare generators are correct), so adding `@contextmanager` would break that usage. The cleanest resolution is to add a separate `get_session_ctx()` context-manager variant for direct calls, and keep the generator for FastAPI.

---

### HR-02: Duplicate `BidAssignment` rows on repeated pipeline runs

**File:** `src/processor/broker_engine.py:64–66`

**Issue:** `assign_brokers` creates a new `BidAssignment` row for every matching `(bid_id, broker_id)` pair without first checking whether an assignment already exists. The `BidAssignment` model has no `UniqueConstraint` on `(bid_id, broker_id)`. The pipeline's 24-hour look-back window means any project from the past day is re-processed on every run, and `assign_brokers` is called for every bid each time. Running the pipeline twice in one day will double all assignment rows; running it N times will create N duplicates.

**Fix — Part 1: Add unique constraint to the model** (`src/database/models.py`):
```python
from sqlalchemy import UniqueConstraint

class BidAssignment(SQLModel, table=True):
    __tablename__ = "bidassignment"
    __table_args__ = (UniqueConstraint("bid_id", "broker_id", name="uq_bidassignment_bid_broker"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: int = Field(foreign_key="bid.id", index=True)
    broker_id: int = Field(foreign_key="broker.id", index=True)
    # ...
```

**Fix — Part 2: Guard in `assign_brokers`** before inserting:
```python
from src.database.models import Bid, BidAssignment, Broker, BrokerMapping, Project

for mapping in mappings:
    broker = session.get(Broker, mapping.broker_id)
    if broker is None or not broker.is_active:
        continue

    # Idempotency guard
    existing = session.exec(
        select(BidAssignment).where(
            BidAssignment.bid_id == bid_id,
            BidAssignment.broker_id == broker.id,
        )
    ).first()
    if existing:
        continue

    assignment = BidAssignment(bid_id=bid_id, broker_id=broker.id)
    session.add(assignment)
    assignments.append(assignment)
```

---

## Warnings

### WR-01: Unflushed resets before aggregate query in `flag_winners`

**File:** `src/processor/winner_logic.py:28–54`

**Issue:** Step 1 sets `bid.is_winner = False` on in-memory ORM objects, but does not call `session.flush()` before Step 2's `func.min()` query. In SQLite (autoflush default on) this is usually safe, but with `autoflush=False` sessions the database still holds the old `is_winner` values when the aggregate runs. More importantly, if the session's identity map has dirty objects, some drivers may not see the pending changes in the subquery. Adding an explicit flush makes the intent clear and safe across all session configurations.

**Fix:**
```python
for bid in bids:
    bid.is_winner = False
session.flush()  # <-- push resets to DB before aggregate query

min_amount = session.exec(
    select(func.min(Bid.amount)).where(Bid.project_id == project_id)
).one()
```

---

### WR-02: LinkedIn `href` stored without URL normalization — may be relative or dangerous

**File:** `src/processor/enrichment.py:87–89`

**Issue:** The href extracted from BeautifulSoup is stored verbatim in `company.linkedin_found`. A page may link to LinkedIn with a relative path (`/company/foo`), a protocol-relative URL (`//linkedin.com/company/foo`), or even a `javascript:` URI. Any of these would be stored as-is and could cause issues in downstream consumers (e.g., email links, UI rendering).

**Fix:**
```python
from urllib.parse import urljoin, urlparse

for anchor in soup.find_all("a", href=True):
    href: str = anchor["href"]
    if "linkedin.com/company/" in href:
        # Resolve relative/protocol-relative URLs
        absolute = urljoin(website_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https"):
            return absolute
```

---

### WR-03: Unbounded `error_message` may exceed DB column limits

**File:** `src/processor/error_queue.py:33` / `src/database/models.py:98`

**Issue:** `SystemError.error_message` is typed as `str` with no `max_length` set. `traceback.format_exc()` output passed from `pipeline.py` can be several kilobytes long. SQLite silently accepts arbitrary text, but PostgreSQL `VARCHAR` without a limit or migration to `TEXT` may cause truncation or errors when this project graduates from SQLite.

**Fix:** Either enforce a max length in the model or explicitly use `sa_column=Column(Text)` for the field:
```python
from sqlalchemy import Column, Text

class SystemError(SQLModel, table=True):
    # ...
    error_message: str = Field(sa_column=Column(Text))
```

---

## Info

### IN-01: `google_found` field is never written

**File:** `src/database/models.py:24`

**Issue:** The `Company.google_found: Optional[bool]` field exists in the schema but no Phase 02 code ever sets it to `True` or `False`. `enrich_company` updates `website_found` and `linkedin_found` only. This is likely planned for a future phase, but it creates dead schema surface that may confuse future developers.

**Suggestion:** Either add a `# TODO(phase-3): set by Google enrichment step` comment, or remove the field until it is implemented to keep the schema minimal.

---

### IN-02: Redundant exception type in `extract_linkedin`

**File:** `src/processor/enrichment.py:90`

**Issue:** `except (requests.exceptions.RequestException, Exception)` — `Exception` is a supertype of `RequestException`, so listing both is redundant. The same catch-all behaviour is achieved by `except Exception:` alone (as done in `find_website`).

**Suggestion:**
```python
except Exception:
    return None
```

---

## Files Reviewed

- `src/database/models.py`
- `src/processor/winner_logic.py`
- `src/processor/broker_engine.py`
- `src/processor/enrichment.py`
- `src/processor/pipeline.py`
- `src/processor/error_queue.py`
- `src/main.py`

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
