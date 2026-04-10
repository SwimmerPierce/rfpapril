<!-- GSD:project-start source:PROJECT.md -->
## Project

**BC Bids Lead Generation Platform**

A lead generation platform that scrapes the BC Bids government website daily for unverified bid results, tracks companies and their bidding activity, and delivers actionable morning reports to insurance brokers. The goal is to identify companies that may benefit from better contract bonding and insurance services so brokers can proactively reach out.

**Core Value:** Ensure absolute data accuracy of who bid and who lost on government contracts, delivering timely and actionable leads safely to brokers so they can sell contract bonding insurance.

### Constraints

- **[Dependency]**: BC Bids structure — Fragile web scraping. Scraping needs to be modular to adapt to markup changes quickly.
- **[Technology]**: Python & PostgreSQL — Standard web stack chosen for AI-coding ease and broad scraping ecosystem support.
- **[Cost]**: Budget ceiling — Total hosting/API budget is $200/month.
- **[Feature]**: Permanent Admin Queues — System failures, missing mapping, or enrichment alerts must never be ephemeral notifications; they must exist as open issues in Zoho CRM.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack (2025)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.agent/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
