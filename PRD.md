# BC Bids Lead Generation Platform — Requirements Specification

**Version:** 1.0 (MVP)
**Date:** April 10, 2026
**Prepared for:** Internal Insurance Brokerage

---

## 1. Project Overview

A lead generation platform that scrapes the BC Bids government website daily for unverified bid results, tracks companies and their bidding activity, and delivers actionable morning reports to insurance brokers. The goal is to identify companies that may benefit from better contract bonding and insurance services.

### 1.1 Core Value Proposition

When a company bids on government contracts, they almost always need contract bonding insurance. By monitoring who is bidding — and especially who is losing — the brokerage can proactively reach out and offer competitive bonding services.

### 1.2 Key Principles

- **Data accuracy is the top priority.** Incorrect data erodes trust in the system.
- **No fully automated outreach.** A human always reviews and sends any communication to a prospect.
- **Notifications must be persistent.** Admin tasks and flags must live in a queue/task list — never ephemeral alerts that can be missed.
- **Easy to understand and update.** The codebase will be maintained with heavy AI coding agent assistance. Clarity and documentation matter more than cleverness.

---

## 2. Data Source: BC Bids

### 2.1 Site Details

- **URL:** BC Bids (Government of British Columbia procurement portal)
- **Technology:** ASP.NET (C# / .NET Framework)
- **API:** None available — all data must be obtained via HTML scraping
- **Legal:** Terms of service have been reviewed; scraping has been discussed with government representatives

### 2.2 Key Data Points

| Field | Source |
|---|---|
| Opportunity ID | Unique identifier per RFP/bid — used as the stable reference key |
| Project name | Listed on the opportunity page |
| Issuing organization | The government body that posted the RFP |
| Unverified bid results | Accessible via "Unverified Bidders" button on the opportunity page, or by searching Opportunity ID in the Unverified Bid Results section |
| Bidder company names | Listed in the unverified bids section (assumed to always be legal names) |
| Bid amounts | Listed per bidder in the unverified bids section |

### 2.3 URL Structure

- The site has consistent URL patterns based on Opportunity ID
- The unverified bid results page can be reached by searching an Opportunity ID or navigating from an opportunity page
- Each opportunity has a detail page with a "View Unverified Bidders" button that reveals all bidders and amounts

### 2.4 Winner Determination (MVP)

- **Rule: The lowest bidder is assumed to be the winner.**
- This is correct approximately 99% of the time per client observation.
- This logic must be implemented as an isolated, configurable function so the win condition can be updated later (e.g., to incorporate explicit award data if a reliable source is found).

---

## 3. System Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    DAILY PIPELINE                         │
│                                                          │
│  3:00 AM ─► Scraper runs                                 │
│             - Hits BC Bids for previous day's postings    │
│             - Extracts opportunity + bidder data          │
│             - Stores in database                          │
│                                                          │
│  3:XX AM ─► Processing                                   │
│             - Identifies new companies → enrichment queue │
│             - Determines winners (lowest bid)             │
│             - Matches issuing org → broker assignment     │
│             - Flags unmatched orgs → admin queue          │
│             - Syncs to Zoho CRM                          │
│                                                          │
│  4:00 AM ─► Email delivery                               │
│             - One email per broker with their matches     │
│             - Admin gets unmatched + flagged items        │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│              ASYNC / ON-DEMAND PROCESSES                  │
│                                                          │
│  Company Enrichment (triggered on new company)           │
│  - Google Business → Website → LinkedIn                  │
│  - Populates contact info in Zoho CRM                    │
│  - Flags incomplete records for human review             │
│                                                          │
│  Admin Dashboard (inside Zoho)                           │
│  - Persistent queue of unresolved issues                 │
│  - Unmapped orgs, missing contacts, scraper errors       │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Data Model

### 4.1 Core Entities (Database)

The application database stores the scraped and processed data. This is the source of truth that syncs to Zoho CRM.

#### Projects Table

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| opportunity_id | String (unique) | BC Bids Opportunity ID — the canonical reference |
| project_name | String | Name of the opportunity |
| issuing_organization | String | Government body that posted the RFP |
| date_posted | Date | Date the results were posted on BC Bids |
| bc_bids_url | String | Direct URL to the opportunity on BC Bids |
| number_of_bidders | Integer | Total count of companies that bid |
| winning_bid_amount | Decimal | Lowest bid amount (MVP winner) |
| date_scraped | Timestamp | When this record was captured |

#### Companies Table

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| legal_name | String (unique) | Company's legal name as it appears on BC Bids |
| dba_name | String (nullable) | Doing-business-as name |
| head_office_address | String (nullable) | Office address |
| website | String (nullable) | Company website URL |
| office_phone | String (nullable) | Office phone number |
| office_email | String (nullable) | Office email |
| key_person_name | String (nullable) | Owner or key contact name |
| key_person_position | String (nullable) | Position/title |
| key_person_email | String (nullable) | Direct email |
| key_person_phone | String (nullable) | Direct phone |
| enrichment_status | Enum | `pending`, `complete`, `incomplete_flagged` |
| enrichment_source | String (nullable) | Where the data was found (Google, LinkedIn, etc.) |
| zoho_record_id | String (nullable) | Corresponding Zoho CRM record ID |
| date_first_seen | Date | When company first appeared in a bid |
| total_bids | Integer | Running count of all bids |
| total_wins | Integer | Running count of wins |
| total_losses | Integer | Running count of losses |
| average_bid_size | Decimal | Running average of bid amounts |
| assigned_broker | FK (nullable) | Broker assigned via org mapping (nullable if unmapped) |

#### Bids Table (Junction)

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| project_id | FK → Projects | The project being bid on |
| company_id | FK → Companies | The company that placed the bid |
| bid_amount | Decimal | Amount bid |
| is_winner | Boolean | True if this is the lowest bid (MVP logic) |
| zoho_record_id | String (nullable) | Corresponding Zoho CRM record ID |

**Relationships:**
- A **Project** has many **Bids**
- A **Company** has many **Bids**
- A **Bid** belongs to one Project and one Company (many-to-many junction)

### 4.2 Configuration Tables

#### Brokers Table

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| name | String | Broker's full name |
| email | String | Email address for daily notifications |
| min_bid_size | Decimal | Minimum bid amount to include in their report |
| max_bid_size | Decimal | Maximum bid amount to include in their report |
| is_active | Boolean | Whether this broker is currently receiving emails |

#### Issuing Org Assignments Table

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| issuing_organization | String (unique) | Name of the issuing org as it appears on BC Bids |
| broker_id | FK → Brokers | Assigned broker |

#### Admin Queue Table

| Field | Type | Description |
|---|---|---|
| id | UUID / Auto-increment | Internal primary key |
| issue_type | Enum | `unmapped_org`, `missing_contact`, `scrape_error`, `enrichment_failed`, `other` |
| description | Text | Human-readable description of the issue |
| related_entity_type | String (nullable) | `project`, `company`, `bid` |
| related_entity_id | String (nullable) | ID of the related record |
| status | Enum | `open`, `in_progress`, `resolved` |
| created_at | Timestamp | When the issue was created |
| resolved_at | Timestamp (nullable) | When the issue was resolved |
| resolved_by | String (nullable) | Who resolved it |

---

## 5. Zoho CRM Integration

### 5.1 Custom Modules

Three custom modules should be created in Zoho CRM, mirroring the core data model.

#### Module: BC Bids Companies

| Field | Zoho Field Type | Maps To |
|---|---|---|
| Company Name (Legal) | Single Line | `companies.legal_name` |
| DBA Name | Single Line | `companies.dba_name` |
| Head Office Address | Multi Line | `companies.head_office_address` |
| Website | URL | `companies.website` |
| Office Phone | Phone | `companies.office_phone` |
| Office Email | Email | `companies.office_email` |
| Key Person Name | Single Line | `companies.key_person_name` |
| Key Person Position | Single Line | `companies.key_person_position` |
| Key Person Email | Email | `companies.key_person_email` |
| Key Person Phone | Phone | `companies.key_person_phone` |
| Enrichment Status | Picklist | `companies.enrichment_status` |
| Total Bids | Number | `companies.total_bids` |
| Total Wins | Number | `companies.total_wins` |
| Total Losses | Number | `companies.total_losses` |
| Average Bid Size | Currency | `companies.average_bid_size` |
| Assigned Broker | Lookup (User) | `companies.assigned_broker` |
| Broker Notes | Multi Line | Free-text field for broker notes |
| Contact Status | Picklist | `not_contacted`, `contacted`, `in_discussion`, `not_interested`, `client` |
| Date First Seen | Date | `companies.date_first_seen` |

#### Module: BC Bids Projects

| Field | Zoho Field Type | Maps To |
|---|---|---|
| Opportunity ID | Single Line (unique) | `projects.opportunity_id` |
| Project Name | Single Line | `projects.project_name` |
| Issuing Organization | Single Line | `projects.issuing_organization` |
| Date Posted | Date | `projects.date_posted` |
| BC Bids URL | URL | `projects.bc_bids_url` |
| Number of Bidders | Number | `projects.number_of_bidders` |
| Winning Bid Amount | Currency | `projects.winning_bid_amount` |

#### Module: BC Bids (Individual Bids)

| Field | Zoho Field Type | Maps To |
|---|---|---|
| Company | Lookup → BC Bids Companies | `bids.company_id` |
| Project | Lookup → BC Bids Projects | `bids.project_id` |
| Bid Amount | Currency | `bids.bid_amount` |
| Won | Checkbox | `bids.is_winner` |

### 5.2 Sync Behavior

- The application database is the source of truth.
- After the daily scrape and processing, new and updated records are pushed to Zoho CRM via the Zoho CRM API.
- The `zoho_record_id` field in the local database tracks the link.
- If a Zoho API call fails, the error is logged and an item is added to the admin queue.

### 5.3 Admin Dashboard (Zoho)

Build as a **Zoho Creator** embedded app or a **custom Zoho widget** inside the CRM. This dashboard displays:

- A persistent queue of all unresolved issues
- Filterable by issue type: unmapped orgs, missing contacts, scrape errors
- Each item has a status (`open`, `in_progress`, `resolved`)
- Ability to resolve items and (for unmapped orgs) assign them to a broker directly
- Items are never auto-dismissed — they must be explicitly resolved

**No error notifications via email.** All errors surface through this dashboard.

---

## 6. Daily Email Notification

### 6.1 Delivery

- **Sent at:** 4:00 AM Pacific daily
- **From:** A system email address (configured via Outlook 365 or a transactional email service)
- **To:** Each broker receives one email containing only their matched bids
- **Admin fallback:** Any bid that cannot be matched to a broker (unmapped issuing org or outside all brokers' size ranges) is included in an admin-specific email

### 6.2 Email Content (Per Bid Result)

Each row/section in the email includes:

| Field | Description |
|---|---|
| Project Name | Name of the opportunity |
| Issuing Organization | Government body that posted it |
| Winning Company | Company with the lowest bid |
| Winning Bid Amount | Dollar amount of the lowest bid |
| Number of Bidders | How many companies bid |
| Zoho CRM Link | Hyperlink to the Company record in Zoho CRM |
| BC Bids Link | Hyperlink to the opportunity on BC Bids |
| Additional Notes | Placeholder section — empty in MVP, will be used for growth signals and AI insights in future iterations |

### 6.3 Email Format

- Clean, scannable format — each bid result as a distinct block or table row
- All previous day's results in one email (not one email per bid)
- Mobile-friendly (brokers may check early morning on phone)

---

## 7. Company Enrichment Pipeline

### 7.1 Trigger

When a company name appears in a bid for the first time (no matching record in the Companies table), a new company record is created with `enrichment_status = pending`, and an enrichment job is queued.

### 7.2 Data Collection Priority

**Office information (always collected):**
1. Doing-business-as name
2. Legal name (already known from BC Bids)
3. Head office address
4. Website
5. Office phone

**Key person information (collected in fallback order):**
1. **Owner** — name, email, phone, position (preferred; almost always the right contact at this company size)
2. **Other key person** — if owner info cannot be found
3. **Office contact info only** — if no individual can be identified

### 7.3 Data Sources (in priority order)

1. Google Business Profile
2. Company website (from Google Business or direct search)
3. LinkedIn

### 7.4 Enrichment Outcomes

| Status | Action |
|---|---|
| `complete` | All required fields populated — record syncs to Zoho |
| `incomplete_flagged` | Some data missing or confidence is low — admin queue item created for human review |

---

## 8. Broker Assignment Logic

### 8.1 Assignment Rules (applied in order)

1. Look up the bid's **issuing organization** in the Issuing Org Assignments table
2. If a broker is mapped, check if the **bid amount falls within that broker's min/max range**
3. If both match → assign to that broker
4. If the org is mapped but bid is outside the broker's range → goes to **admin email**
5. If the org is **not mapped** to any broker → goes to **admin email** AND an admin queue item is created (type: `unmapped_org`)

### 8.2 Configuration

- Brokers set their own min/max bid size thresholds
- Issuing org → broker mapping is maintained by the admin
- New orgs are expected to appear regularly (100+ existing orgs); the system must handle unknown orgs gracefully

---

## 9. Users and Roles

| Role | Count | Access | Notifications |
|---|---|---|---|
| Broker | 5 | Zoho CRM (company/bid/project records) | Daily email with matched bids |
| Admin Assistant | 1 | Zoho CRM + Admin Dashboard | Daily email with unmatched bids; dashboard for issue queue |
| Marketing Manager | 1 | Zoho CRM (read) | None in MVP |
| Owner | 1 | Zoho CRM + Admin Dashboard | None in MVP (can view dashboard) |

---

## 10. Technology Stack (Recommended)

### 10.1 Selection Criteria

- Maximum online documentation and community support
- AI coding agent friendly (clear patterns, well-known frameworks)
- Simple to deploy and iterate on with CI/CD
- Low operational complexity

### 10.2 Recommended Stack

| Component | Technology | Rationale |
|---|---|---|
| Language | **Python** | Best documentation, largest AI/scraping ecosystem, most AI agents are fluent in it |
| Web Scraping | **Playwright** or **Selenium** | ASP.NET sites often require JavaScript rendering; Playwright has excellent docs |
| Database | **PostgreSQL** | Robust, well-documented, excellent for relational data |
| Task Scheduling | **Cron job** or **APScheduler** | Simple scheduled daily run; no need for heavy orchestration in MVP |
| Email Sending | **Outlook 365 SMTP** or **Microsoft Graph API** | Already have Outlook 365; keeps emails coming from a familiar domain |
| CRM Integration | **Zoho CRM API v2** | Well-documented REST API; Python SDK available |
| Company Enrichment | **Google Places API** + **Web scraping** | For Google Business data; fallback to scraping company sites |
| Hosting | **Railway** or **Render** | Simple deploy from GitHub, managed PostgreSQL add-ons, affordable, minimal DevOps |
| CI/CD | **GitHub Actions** | Native to GitHub, excellent documentation, free tier is sufficient |
| Error Logging | **Structured logging** (Python `logging` module) + **Sentry** (optional) | Best practice error tracking |

### 10.3 Budget Estimate

| Item | Estimated Monthly Cost |
|---|---|
| Railway/Render (app + cron worker) | $5–20 |
| Managed PostgreSQL | $0–15 (included on most platforms) |
| Google Places API (enrichment) | $0–50 (depending on volume) |
| Sentry (error tracking, optional) | $0 (free tier) |
| **Total** | **~$20–85/month** |

Well within the $200/month ceiling.

---

## 11. Deployment and CI/CD

### 11.1 Repository Structure

```
bc-bids-lead-gen/
├── README.md
├── .github/
│   └── workflows/
│       ├── deploy.yml         # Auto-deploy on push to main
│       └── test.yml           # Run tests on PR
├── src/
│   ├── scraper/               # BC Bids scraping logic
│   ├── processing/            # Winner determination, broker matching
│   ├── enrichment/            # Company contact enrichment
│   ├── notifications/         # Email generation and sending
│   ├── integrations/
│   │   └── zoho/              # Zoho CRM sync logic
│   ├── models/                # Database models / ORM
│   ├── config/                # Broker config, org mappings, thresholds
│   └── admin/                 # Admin queue management
├── tests/
├── migrations/                # Database migrations
├── requirements.txt
└── .env.example
```

### 11.2 Deployment Flow

1. Developer pushes to a feature branch
2. GitHub Actions runs tests
3. PR merged to `main`
4. GitHub Actions auto-deploys to Railway/Render
5. Cron job runs daily at 3:00 AM Pacific

---

## 12. MVP Scope vs. Future Features

### 12.1 MVP (This Build)

- [x] Daily scraper for BC Bids unverified bid results (previous day)
- [x] Database storage of projects, companies, and bids
- [x] Winner determination (lowest bid)
- [x] Broker assignment by issuing org + bid size range
- [x] Daily email to each broker at 4:00 AM
- [x] Zoho CRM sync (three custom modules)
- [x] Company enrichment pipeline (Google → website → LinkedIn)
- [x] Admin dashboard in Zoho (persistent issue queue)
- [x] Error logging and admin queue for unresolved issues
- [x] CI/CD pipeline with GitHub Actions
- [x] Forward-looking data only (no historical backfill)

### 12.2 Post-MVP Roadmap

- [ ] **Historical backfill** — Scrape and import historical bid data from BC Bids
- [ ] **Growth signal detection** — Flag companies bidding on projects significantly larger than their historical average (displayed in "Additional Notes" in email and on Zoho CRM record)
- [ ] **AI-powered categorization** — Classify bids by industry/type using AI instead of relying solely on issuing org
- [ ] **Advanced win condition** — Replace lowest-bid assumption with actual award data if a reliable source is identified
- [ ] **Outreach templates** — Pre-drafted email templates in Zoho for brokers to review and send
- [ ] **Reporting dashboard** — Analytics on bid volume, win rates, broker performance
- [ ] **Additional Notes enrichment** — Populate the email's "Additional Notes" section with AI-generated insights per bid

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| BC Bids changes HTML structure | Scraper breaks silently | Validate expected page structure on each run; alert admin queue on unexpected format; keep scraper logic modular for quick fixes |
| Company name variations | Duplicate company records | MVP assumes legal names are consistent; add fuzzy matching post-MVP if duplicates emerge |
| Zoho API rate limits | Sync failures on high-volume days | Batch API calls; implement retry with backoff; log failures to admin queue |
| Google Places API returns wrong business | Incorrect contact info | Always set enrichment to `incomplete_flagged` if confidence is low; human reviews all flagged records |
| Scraper blocked by BC Bids | No data collected | Implement polite scraping (rate limiting, realistic headers); monitor for blocks; alert admin queue |

---

## 14. Acceptance Criteria (MVP)

1. The scraper successfully collects all unverified bid results posted on BC Bids from the previous day
2. New companies are created in the database and queued for enrichment
3. The lowest bidder is correctly identified as the winner for each project
4. Each broker receives exactly one email at 4:00 AM containing only bids matching their org assignments and size range
5. Unmatched bids go to the admin email
6. All data syncs correctly to the three Zoho CRM custom modules
7. The admin dashboard in Zoho shows all open issues and allows resolution
8. No outreach is ever sent without human review
9. The system logs errors following best practices and surfaces them in the admin queue
10. The full pipeline can be deployed via GitHub push with no manual server configuration
