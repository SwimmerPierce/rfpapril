"""
Company enrichment pipeline (PROC-04).

Discovers official websites and LinkedIn profile URLs for companies
using DuckDuckGo search and BeautifulSoup HTML parsing.

Threat mitigations:
  T-02-02-01: All requests.get calls include a timeout (10s).
  T-02-02-02: Only URLs are stored; no sensitive page content is retained.
"""

import ipaddress
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from sqlmodel import Session, select

from src.database.models import Company

# Sites that are not company-owned and should be excluded from search results.
_NOISE_DOMAINS = [
    "linkedin.com",
    "facebook.com",
    "yellowpages.ca",
    "yellowpages.com",
    "twitter.com",
    "instagram.com",
    "yelp.ca",
    "yelp.com",
    "canada411.ca",
    "bbb.org",
]

# Default timeout (seconds) for all outbound HTTP requests.
_REQUEST_TIMEOUT = 10

# Private/loopback ranges that must never be fetched (SSRF mitigation, T-02-02-01).
_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_safe_url(url: str) -> bool:
    """Return True only if the URL has an http/https scheme and a non-private host."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        if not hostname:
            return False
        addr = ipaddress.ip_address(hostname)
        return not any(addr in net for net in _PRIVATE_RANGES)
    except ValueError:
        # hostname is a domain name, not an IP — treat as safe
        return True


def find_website(company_name: str) -> Optional[str]:
    """
    Search DuckDuckGo for the official website of a given company.

    Noise sites (social media, directories) are skipped so the result
    is more likely to be the company's own domain.

    Args:
        company_name: Legal name of the company to search for.

    Returns:
        The first non-noise URL found, or None if nothing suitable is found.
    """
    query = f"{company_name} official website"
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            for result in results:
                url: str = result.get("href", "")
                if url and not any(noise in url for noise in _NOISE_DOMAINS):
                    return url
    except Exception:
        # DDG can raise on rate limits or network errors — fail gracefully.
        return None
    return None


def extract_linkedin(website_url: str) -> Optional[str]:
    """
    Fetch a company homepage and extract a LinkedIn company profile URL.

    Only matches linkedin.com/company/ paths (not personal profiles).

    Args:
        website_url: The company's official website URL.

    Returns:
        A LinkedIn company profile URL, or None if not found or on error.
    """
    if not _is_safe_url(website_url):
        return None
    try:
        response = requests.get(
            website_url,
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BCBidsBot/1.0)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href: str = anchor["href"]
            if "linkedin.com/company/" in href:
                return href
    except (requests.exceptions.RequestException, Exception):
        # Network errors, timeouts, and HTML parse errors all return None.
        return None
    return None


def enrich_company(session: Session, company_id: int) -> None:
    """
    Full enrichment orchestration for a single company.

    Steps:
      1. Fetch company record by ID.
      2. Run find_website; update website_found if a result is returned.
      3. If a website was found, run extract_linkedin; update linkedin_found.
      4. Commit all changes to the database.

    Args:
        session: Active SQLModel database session.
        company_id: Primary key of the Company to enrich.
    """
    company = session.exec(select(Company).where(Company.id == company_id)).first()
    if company is None:
        return

    website = find_website(company.legal_name)
    if website:
        company.website_found = website
        linkedin = extract_linkedin(website)
        if linkedin:
            company.linkedin_found = linkedin

    session.add(company)
    session.commit()
