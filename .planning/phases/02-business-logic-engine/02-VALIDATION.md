# Phase 2 Validation: Business Logic Engine

## Success Criteria Verification

| ID | Criterion | Verification Method | Status |
|----|-----------|---------------------|--------|
| SC-02-01 | Lowest bid flagged as winner | `tests/test_logic.py::test_winner_logic` | PENDING |
| SC-02-02 | Accurate broker assignment | `tests/test_logic.py::test_broker_assignment` | PENDING |
| SC-02-03 | Enrichment pipeline (Google/Website/LinkedIn) | `tests/test_enrichment.py` | PENDING |

## Requirement Traceability

| Req ID | Description | Plan | Task |
|--------|-------------|------|------|
| PROC-01 | Flag lowest bid as assumed winner | 02-01 | 2 |
| PROC-02 | Assign projects to specific brokers | 02-01 | 3 |
| PROC-03 | Apply bid amount thresholds | 02-01 | 3 |
| PROC-04 | Enrichment pipeline for companies | 02-02 | 1, 2, 3 |
| ADMIN-01 | Record unmapped orgs/failures | 02-03 | 3 |

## Manual Verification Steps

1. **Broker Configuration:** Seed the `Broker` and `BrokerMapping` tables with test data.
2. **End-to-End Run:** Execute `python -m src.main --test-run` and verify `is_winner` and `broker_id` fields in the database.
3. **Enrichment Check:** Verify that `Company` records have `website_found` and `linkedin_found` populated for known companies.
4. **Error Queue:** Intentionally provide an unmapped organization and verify a `SystemError` record is created.
