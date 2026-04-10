# Project Architecture Research

## Component Boundaries & Data Flow

1. **Scraping Module (Playwright + Python)**
   - Triggered at 3:00 AM daily by cron job.
   - Navigates BC Bids, extracts yesterday's Unverified Bid Results.
   - Outputs raw normalized data structures.

2. **Core Processor**
   - Reads raw data from Scraping Module.
   - Performs Entity Resolution: Identifies new projects, matches existing companies via Legal Name, creates Bid records.
   - Identifies Winners (lowest bid).

3. **Broker Assignment Engine**
   - Matches Issuing Organizations against configured rules.
   - Filters bids by min/max bid size configurations.
   - Flags unmatched orgs for Admin intervention.

4. **Zoho CRM Sync Engine**
   - Identifies records needing sync.
   - Pushes Projects, Companies, and Bids to Zoho custom modules.
   - Saves returned Zoho Record IDs to PostgreSQL database for future updates.

5. **Notification / Reporting Engine**
   - Combines matched data into HTML emails.
   - Blasts to brokers via Outlook 365 SMTP.

6. **Admin Dashboard (Zoho Creator/Widget)**
   - Separate visualization layer inside the CRM.
   - Reads directly from Zoho entities, pulling from the "Admin Queue" tags or tracking custom module for errors.

## Suggested Build Order

1. **Database Models & Skeleton** -> Establish PostgreSQL schema.
2. **Scraping Module** -> Most fragile part; secure this logic first.
3. **Core Processor & Database Storage** -> Get the data saving locally correctly.
4. **Zoho Sync Integration** -> Test CRM syncing.
5. **Assignment & Email** -> Reporting logic.
