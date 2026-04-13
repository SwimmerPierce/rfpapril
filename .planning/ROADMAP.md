# Execution Roadmap

**4 phases** | **15 requirements mapped** | All v1 requirements covered ✓

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Database & Scraper Skeleton | Establish reliable data capture and continuous deployment pipeline. | SCRAP-01, SCRAP-02, DB-01, DB-02, DB-03, OPS-01 | 3 |
| 2 | Business Logic Engine | Establish logic to identify winners, match brokers, and queue enrichment. | PROC-01, PROC-02, PROC-03, PROC-04 | 3 |
| 3 | Zoho CRM Integration | 2/3 | In Progress|  |
| 4 | Email Notifications | Send 4:00 AM daily digests to assigned brokers and an Admin fallback email. | NOTIF-01, NOTIF-02 | 2 |

---

### Phase Details

#### Phase 1: Database & Scraper Skeleton
**Goal:** Establish reliable data capture and continuous deployment pipeline.
**Requirements:** SCRAP-01, SCRAP-02, DB-01, DB-02, DB-03, OPS-01
**Success criteria:**
1. A push to `main` branch reliably deploys the application.
2. The scraper runs daily on a cron schedule, independently pulling all unverified bids from BC Bids.
3. All new projects, companies, and bids are inserted into the PostgreSQL database without duplicates.
**Plans:** 3 plans
- [ ] 01-01-PLAN.md — Development Environment & Data Models
- [ ] 01-02-PLAN.md — Infrastructure & CI/CD
- [ ] 01-03-PLAN.md — BC Bids Scraper Core

#### Phase 2: Business Logic Engine
**Goal:** Establish logic to identify winners, match brokers, and queue enrichment.
**Requirements:** PROC-01, PROC-02, PROC-03, PROC-04
**Success criteria:**
1. System correctly flags the lowest bid on a given project as the winner.
2. System accurately assigns specific brokers to bids based on the Issuing Organization and respective min/max thresholds.
3. System reliably identifies unseen companies and runs the Google -> Website -> LinkedIn enrichment process.
**UI hint:** no

#### Phase 3: Zoho CRM Integration
**Goal:** Sync local DB state to Zoho and route issues to an Admin Dashboard.
**Requirements:** SYNC-01, SYNC-02, SYNC-03, ADMIN-01, ADMIN-02
**Success criteria:**
1. All extracted Companies, Projects, and Bids seamlessly sync into their respective Custom Modules in Zoho CRM.
2. Any entity syncing failures, unmapped organizations, or enrichment errors generate persistent records.
3. The Admin can view and resolve tasks exclusively within the Zoho Dashboard.
**UI hint:** no
**Plans:** 2/3 plans executed
- [x] 03-01-PLAN.md — Data Model Updates & OAuth Client
- [x] 03-02-PLAN.md — Record Mappers & Sync Service
- [ ] 03-03-PLAN.md — Pipeline Integration & Admin Queue Sync

#### Phase 4: Email Notifications
**Goal:** Send 4:00 AM daily digests to assigned brokers and an Admin fallback email.
**Requirements:** NOTIF-01, NOTIF-02
**Success criteria:**
1. Each active broker receives exactly one email summarizing their properly assigned and matched bids.
2. The Admin receives a fallback email containing any unmatched bids the brokers did not receive.
**UI hint:** no
