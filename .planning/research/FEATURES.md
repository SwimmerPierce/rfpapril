# Project Features Research: BC Bids Lead Gen

## Table Stakes (Must-Haves)

Users expect these features as the absolute baseline for a data scraping pipeline:
- **Daily Reliable Scraping**: The scraper must run reliably every single day without manual intervention.
- **Deduplication**: Must not create duplicate company or project records across scraping runs.
- **Relational Integrity**: Bids must accurately reflect which company made the bid, what the amount was, and on which project.
- **Matching & Routing**: Must correctly associate bids with specific issuing organizations to route strictly to the assigned broker.

## Differentiators

These provide the business advantage:
- **Lowest-Bidder Winner Assumption**: Simple heuristic allowing immediate MVP value without waiting for lagging "Awarded" indicators.
- **Company Enrichment**: Automatically querying Google Places, websites, and LinkedIn to build contact lists without broker effort.
- **Actionable Daily Email**: Delivers concise "go-do" emails rather than raw data dumps.

## Anti-Features (What NOT to build)

- **Automated Cold Emailing**: Never send emails automatically. High risk of reputation damage and poor targeting.
- **Real-time Scraping**: Unnecessary load on BC Bids and complexity; daily runs are sufficient for contract bonding sales cycles.
- **Ephemeral Error Alerts**: Email alerts for system errors are ignored. They must live as actionable tasks in the Zoho Admin dashboard.
