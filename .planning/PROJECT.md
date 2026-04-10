# BC Bids Lead Generation Platform

## What This Is

A lead generation platform that scrapes the BC Bids government website daily for unverified bid results, tracks companies and their bidding activity, and delivers actionable morning reports to insurance brokers. The goal is to identify companies that may benefit from better contract bonding and insurance services so brokers can proactively reach out.

## Core Value

Ensure absolute data accuracy of who bid and who lost on government contracts, delivering timely and actionable leads safely to brokers so they can sell contract bonding insurance.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Daily scraper for BC Bids unverified bid results (previous day)
- [ ] Database storage (PostgreSQL) of projects, companies, and bids
- [ ] Winner determination (lowest bid)
- [ ] Broker assignment (matching by issuing org + bid size range)
- [ ] Daily email delivery to each broker at 4:00 AM Pacific
- [ ] Zoho CRM sync for three custom modules (Companies, Projects, Bids)
- [ ] Company enrichment pipeline (Google → website → LinkedIn)
- [ ] Admin dashboard within Zoho for managing a persistent issue queue
- [ ] Error logging and routing for unresolved issues
- [ ] CI/CD deployment pipeline with GitHub Actions

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- [Fully automated outreach] — No human-less outreach. A human must always review and send communication.
- [Historical data backfill] — Deferred to post-MVP to keep initial launch fast.
- [Growth signal detection] — Deferred to post-MVP. AI-powered insights and advanced logic come later.
- [Real-time data sync] — Scraping runs daily overnight; real-time scraping isn't required and adds massive complexity.

## Context

The system is built for an internal insurance brokerage focused on finding construction or service companies that need contract bonding. Because BC Bids is an ASP.NET system without a public API, all data is obtained via daily HTML scraping. There is high reliance on code maintainability and AI coding agent readability over cleverness to ensure long-term ease of updates.

## Constraints

- **[Dependency]**: BC Bids structure — Fragile web scraping. Scraping needs to be modular to adapt to markup changes quickly.
- **[Technology]**: Python & PostgreSQL — Standard web stack chosen for AI-coding ease and broad scraping ecosystem support.
- **[Cost]**: Budget ceiling — Total hosting/API budget is $200/month.
- **[Feature]**: Permanent Admin Queues — System failures, missing mapping, or enrichment alerts must never be ephemeral notifications; they must exist as open issues in Zoho CRM.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Lowest bid = Winner | True 99% of time, allows MVP to proceed without finding an explicit award data source. Must be a deeply isolated, configurable function. | — Pending |
| Zoho CRM is NOT source of truth | The App's PostgreSQL database is the single source of truth to protect against CRM sync errors. | — Pending |
| Ephemeral Notifications are banned for Admin | If a task or error requires admin manual intervention, it goes to the Zoho Dashboard Issue Queue. Email is for final broker leads only. | — Pending |

---
*Last updated: April 10, 2026 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
