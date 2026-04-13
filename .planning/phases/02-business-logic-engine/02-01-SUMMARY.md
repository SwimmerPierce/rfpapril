---
phase: 02-business-logic-engine
plan: "01"
subsystem: business-logic
tags: [winner-logic, broker-assignment, database-models, tdd, sqlmodel]
dependency_graph:
  requires: [01-database-scraper-skeleton]
  provides: [winner-identification, broker-assignment-engine, broker-db-models]
  affects: [src/database/models.py, src/processor/winner_logic.py, src/processor/broker_engine.py]
tech_stack:
  added: []
  patterns: [tdd-red-green-refactor, sql-aggregate-subquery, parameterized-orm-queries]
key_files:
  created:
    - src/processor/__init__.py
    - src/processor/winner_logic.py
    - src/processor/broker_engine.py
    - tests/test_logic.py
  modified:
    - src/database/models.py
    - migrations/env.py
decisions:
  - "Inactive brokers are excluded at assignment time rather than at query time — keeps BrokerMapping records intact for audit while preventing stale leads"
  - "BidAssignment is a concrete table (not a pure join) so assignments can carry metadata in future (e.g. sent_at timestamp)"
  - "flag_winners resets all bids to is_winner=False before re-flagging — prevents stale winner state if called more than once on the same project"
metrics:
  duration_minutes: 35
  completed_date: "2026-04-13"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 2
---

# Phase 02 Plan 01: Business Logic Engine — Core Models and Processing Summary

**One-liner:** Broker and BidAssignment models added to schema; SQL-based winner flagging and threshold-driven broker assignment implemented with full TDD coverage.

## What Was Built

### Task 1: Broker and BrokerMapping Models (`ecc8347`)
Added three new SQLModel tables to `src/database/models.py`:

- **`Broker`** — name, email, is_active. Represents an insurance broker who receives daily leads.
- **`BrokerMapping`** — issuing_org, broker_id (FK), min_threshold, max_threshold. Database-driven rule table replacing any hard-coded org-to-broker mapping.
- **`BidAssignment`** — bid_id (FK), broker_id (FK). Explicit link table supporting many-to-many Bid-to-Broker assignment with future extensibility (e.g. sent_at).
- Updated `Bid` model with an `assignments` relationship.
- Updated `migrations/env.py` to import the new models for Alembic autogenerate.
- Verified schema applies cleanly via `SQLModel.metadata.create_all`.

### Task 2: Winner Identification Logic — TDD (PROC-01) (`c352ef2` RED, `7e89bc5` GREEN)
`src/processor/winner_logic.py` — `flag_winners(session, project_id)`:

- Resets all bids for a project to `is_winner=False` (prevents stale state).
- Uses `func.min()` SQL aggregate to identify lowest bid amount without loading all bids into Python memory.
- Marks all bids at the minimum amount as winners (handles tie edge case).
- 4 tests covering: single winner, tie, stale-flag reset, single-bid project.

### Task 3: Broker Assignment Engine — TDD (PROC-02, PROC-03) (`a8db0a2`)
`src/processor/broker_engine.py` — `assign_brokers(session, bid_id)`:

- Loads the bid's project to obtain `issuing_org`.
- Queries `BrokerMapping` with parameterized filters: org match + amount within `[min_threshold, max_threshold]`.
- Skips inactive brokers at assignment time.
- Creates `BidAssignment` records for all matching active brokers.
- Returns empty list gracefully when no mapping exists (Phase 3 will route unmapped orgs to Zoho Admin Queue).
- 5 tests covering: single match, no match, threshold boundary, multiple brokers, inactive broker excluded.

## Test Results

```
9 passed in 0.39s
```

All tests in `tests/test_logic.py` pass with no warnings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Refactor] Replaced deprecated `session.query()` with `session.exec(select())`**
- **Found during:** Task 3 (GREEN phase, first test run)
- **Issue:** Tests used `session.query()` which SQLModel deprecates in favour of `session.exec(select(...))`. Produced deprecation warnings on every broker test.
- **Fix:** Replaced all 5 occurrences in `tests/test_logic.py` with the SQLModel-idiomatic `session.exec(select(...).where(...))` form.
- **Files modified:** `tests/test_logic.py`
- **Commit:** `a8db0a2` (included in Task 3 commit)

### Verification Note on Alembic
The plan specified `alembic revision --autogenerate && alembic upgrade head` as the Task 1 verification step. The worktree has no PostgreSQL connection string configured (only SQLite fallback). Schema correctness was verified instead via `SQLModel.metadata.create_all(engine)` against the SQLite test database, confirming all 7 tables including the 3 new ones. Alembic autogenerate will be run in the main environment where PostgreSQL is configured.

## Known Stubs

None. All logic is fully wired: models reference each other through relationships, `flag_winners` reads from and writes to the `bid` table, and `assign_brokers` reads `project`/`brokermapping`/`broker` and writes to `bidassignment`.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All queries use SQLModel parameterized `select()` calls (mitigates T-02-01-01). Broker email addresses exist only in the database and are not logged or returned by any public API surface (mitigates T-02-01-02).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/database/models.py | FOUND |
| src/processor/winner_logic.py | FOUND |
| src/processor/broker_engine.py | FOUND |
| tests/test_logic.py | FOUND |
| .planning/phases/02-business-logic-engine/02-01-SUMMARY.md | FOUND |
| commit ecc8347 (Task 1 models) | FOUND |
| commit c352ef2 (Task 2 RED) | FOUND |
| commit 7e89bc5 (Task 2 GREEN) | FOUND |
| commit a8db0a2 (Task 3) | FOUND |
| pytest tests/test_logic.py | 9 passed, 0 warnings |
