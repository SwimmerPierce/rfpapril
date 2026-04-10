# Project Requirements

## v1 Requirements

### Scraping
- [ ] **SCRAP-01**: System executes a reliable daily data gathering task at 3:00 AM automatically.
- [ ] **SCRAP-02**: System navigates BC Bids and extracts all unverified bid results posted during the previous day.

### Database & Storage
- [ ] **DB-01**: System persists unique Project records (Opportunity ID, Name, Issuing Org, Date, URL).
- [ ] **DB-02**: System persists Company records, handling deduplication based on legal names.
- [ ] **DB-03**: System persists Bid records mapping bid amounts to specific Companies and Projects.

### Business Logic & Processing
- [ ] **PROC-01**: System flags the lowest bid on a given project as the assumed winner.
- [ ] **PROC-02**: System assigns projects strictly to specific brokers based on the Issuing Organization.
- [ ] **PROC-03**: System applies minimum and maximum bid amount thresholds to filter what each assigned broker receives.
- [ ] **PROC-04**: System flags previously unseen companies and runs an enrichment pipeline (Google -> Website -> LinkedIn) to gather contact information.

### Zoho CRM Sync
- [ ] **SYNC-01**: System synchronizes Company data accurately to the custom 'BC Bids Companies' Zoho module.
- [ ] **SYNC-02**: System synchronizes Project data accurately to the custom 'BC Bids Projects' Zoho module.
- [ ] **SYNC-03**: System synchronizes Bid data accurately to the custom 'BC Bids (Individual Bids)' Zoho module.

### Notifications
- [ ] **NOTIF-01**: System generates and sends exactly one digest email to each broker at 4:00 AM containing their matched leads.
- [ ] **NOTIF-02**: System generates and sends an administrative email containing any bids that matched no brokers or had no mapped issuing org.

### Admin Dashboard
- [ ] **ADMIN-01**: System records unmapped orgs, scrape failures, and incomplete enrichment tasks as persistent items.
- [ ] **ADMIN-02**: System exposes these items in an admin dashboard queue in Zoho that prevents them from being ignored or lost.

### Operations
- [ ] **OPS-01**: System relies on a continuous integration and deployment pipeline (GitHub Actions -> Railway/Render) for automated deployments.

## v2 Requirements (Deferred)

- **V2-01**: Historical data backfill from all past BC Bids records.
- **V2-02**: Detect growth signals (e.g. companies bidding significantly higher than their average).
- **V2-03**: AI-powered categorization of bids by industry, rather than relying solely on issuing organizations.
- **V2-04**: Extract absolute award data as a more thorough win condition instead of assuming the lowest bid won.
- **V2-05**: Auto-create email templates in Zoho CRM for brokers to review and send.
- **V2-06**: Elaborate reporting dashboards analyzing win rates and broker funnel performance.

## Out of Scope

- **Fully Automated Outreach**: The system will never send emails directly to prospects. A human broker must review and send correspondence to protect reputation.
- **Real-time Scraping**: Runs occur daily. Immediate execution isn't required and would introduce high operational burden and rate-limit risks.

## Traceability

- **Phase 1: Database & Scraper Skeleton**: SCRAP-01, SCRAP-02, DB-01, DB-02, DB-03, OPS-01
- **Phase 2: Business Logic Engine**: PROC-01, PROC-02, PROC-03, PROC-04
- **Phase 3: Zoho CRM Integration**: SYNC-01, SYNC-02, SYNC-03, ADMIN-01, ADMIN-02
- **Phase 4: Email Notifications**: NOTIF-01, NOTIF-02
