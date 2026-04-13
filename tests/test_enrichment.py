"""
Tests for company enrichment pipeline (PROC-04).

Uses mocking to avoid live external network calls in automated tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.database.models import Company
from src.processor.enrichment import enrich_company, extract_linkedin, find_website


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    """In-memory SQLite session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Task 1: find_website
# ---------------------------------------------------------------------------

class TestFindWebsite:
    """Tests for find_website(company_name) -> Optional[str]"""

    def test_find_website_returns_url_for_valid_company(self):
        """find_website should return a URL string when DDG returns results."""
        mock_results = [
            {"href": "https://www.acmecontracting.ca", "title": "Acme Contracting", "body": "..."},
        ]
        with patch("src.processor.enrichment.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = mock_results
            mock_ddgs_cls.return_value = mock_ddgs

            result = find_website("Acme Contracting Ltd")

        assert result == "https://www.acmecontracting.ca"

    def test_find_website_filters_out_noise_sites(self):
        """find_website should skip LinkedIn, Facebook, and YellowPages results."""
        mock_results = [
            {"href": "https://www.linkedin.com/company/acme", "title": "LinkedIn"},
            {"href": "https://www.facebook.com/acme", "title": "Facebook"},
            {"href": "https://www.yellowpages.ca/acme", "title": "YellowPages"},
            {"href": "https://www.acmecontracting.ca", "title": "Acme"},
        ]
        with patch("src.processor.enrichment.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = mock_results
            mock_ddgs_cls.return_value = mock_ddgs

            result = find_website("Acme Contracting Ltd")

        assert result == "https://www.acmecontracting.ca"

    def test_find_website_returns_none_when_no_results(self):
        """find_website should return None when DDG finds nothing."""
        with patch("src.processor.enrichment.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value = mock_ddgs

            result = find_website("123456 B.C. Ltd")

        assert result is None

    def test_find_website_returns_none_when_all_results_are_noise(self):
        """find_website should return None when all results are noise sites."""
        mock_results = [
            {"href": "https://www.linkedin.com/company/acme", "title": "LinkedIn"},
            {"href": "https://www.facebook.com/acme", "title": "Facebook"},
        ]
        with patch("src.processor.enrichment.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = mock_results
            mock_ddgs_cls.return_value = mock_ddgs

            result = find_website("Acme Contracting Ltd")

        assert result is None

    def test_find_website_handles_ddg_exception(self):
        """find_website should return None if DDG raises an exception."""
        with patch("src.processor.enrichment.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.side_effect = Exception("Rate limited")
            mock_ddgs_cls.return_value = mock_ddgs

            result = find_website("Acme Contracting Ltd")

        assert result is None


# ---------------------------------------------------------------------------
# Task 2: extract_linkedin
# ---------------------------------------------------------------------------

class TestExtractLinkedin:
    """Tests for extract_linkedin(website_url) -> Optional[str]"""

    def test_extract_linkedin_finds_url_in_anchor_tag(self):
        """extract_linkedin should find a LinkedIn URL in an <a href> tag."""
        html = """
        <html><body>
          <a href="https://www.linkedin.com/company/acme-contracting">Follow us</a>
        </body></html>
        """
        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = extract_linkedin("https://www.acmecontracting.ca")

        assert result == "https://www.linkedin.com/company/acme-contracting"

    def test_extract_linkedin_returns_none_when_no_link(self):
        """extract_linkedin should return None when no LinkedIn link is present."""
        html = "<html><body><p>No social links here.</p></body></html>"
        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = extract_linkedin("https://www.acmecontracting.ca")

        assert result is None

    def test_extract_linkedin_handles_timeout(self):
        """extract_linkedin should return None on request timeout."""
        import requests

        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()

            result = extract_linkedin("https://www.acmecontracting.ca")

        assert result is None

    def test_extract_linkedin_handles_connection_error(self):
        """extract_linkedin should return None on connection error."""
        import requests

        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            result = extract_linkedin("https://www.acmecontracting.ca")

        assert result is None

    def test_extract_linkedin_uses_timeout_on_request(self):
        """extract_linkedin must pass a timeout to requests.get (T-02-02-01 mitigation)."""
        html = "<html><body></body></html>"
        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            extract_linkedin("https://www.acmecontracting.ca")

        call_kwargs = mock_get.call_args
        # timeout must be provided (positional or keyword)
        timeout_set = (
            call_kwargs.kwargs.get("timeout") is not None
            if call_kwargs.kwargs
            else (len(call_kwargs.args) > 1)
        )
        assert timeout_set, "requests.get must be called with a timeout parameter"

    def test_extract_linkedin_only_matches_company_profiles(self):
        """extract_linkedin should only match linkedin.com/company/ URLs."""
        html = """
        <html><body>
          <a href="https://www.linkedin.com/in/john-doe">Personal</a>
          <a href="https://www.linkedin.com/company/acme-contracting">Company</a>
        </body></html>
        """
        with patch("src.processor.enrichment.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = extract_linkedin("https://www.acmecontracting.ca")

        assert result == "https://www.linkedin.com/company/acme-contracting"


# ---------------------------------------------------------------------------
# Task 3: enrich_company
# ---------------------------------------------------------------------------

class TestEnrichCompany:
    """Tests for enrich_company(session, company_id)."""

    def test_enrich_company_updates_website_and_linkedin(self, session):
        """enrich_company should update website_found and linkedin_found when both succeed."""
        company = Company(legal_name="acme contracting ltd")
        session.add(company)
        session.commit()
        session.refresh(company)

        with patch("src.processor.enrichment.find_website") as mock_fw, \
             patch("src.processor.enrichment.extract_linkedin") as mock_el:
            mock_fw.return_value = "https://www.acmecontracting.ca"
            mock_el.return_value = "https://www.linkedin.com/company/acme-contracting"

            enrich_company(session, company.id)

        session.refresh(company)
        assert company.website_found == "https://www.acmecontracting.ca"
        assert company.linkedin_found == "https://www.linkedin.com/company/acme-contracting"

    def test_enrich_company_updates_website_only_when_no_linkedin(self, session):
        """enrich_company should set website_found even when LinkedIn is not found."""
        company = Company(legal_name="building corp bc")
        session.add(company)
        session.commit()
        session.refresh(company)

        with patch("src.processor.enrichment.find_website") as mock_fw, \
             patch("src.processor.enrichment.extract_linkedin") as mock_el:
            mock_fw.return_value = "https://www.buildingcorp.ca"
            mock_el.return_value = None

            enrich_company(session, company.id)

        session.refresh(company)
        assert company.website_found == "https://www.buildingcorp.ca"
        assert company.linkedin_found is None

    def test_enrich_company_skips_linkedin_when_no_website(self, session):
        """enrich_company should not call extract_linkedin when website not found."""
        company = Company(legal_name="ghost corp 123")
        session.add(company)
        session.commit()
        session.refresh(company)

        with patch("src.processor.enrichment.find_website") as mock_fw, \
             patch("src.processor.enrichment.extract_linkedin") as mock_el:
            mock_fw.return_value = None

            enrich_company(session, company.id)

        session.refresh(company)
        assert company.website_found is None
        assert company.linkedin_found is None
        mock_el.assert_not_called()

    def test_enrich_company_does_nothing_for_unknown_id(self, session):
        """enrich_company should handle a non-existent company_id gracefully."""
        # Should not raise
        enrich_company(session, 99999)
