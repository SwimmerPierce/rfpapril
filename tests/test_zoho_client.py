import pytest
import time
import requests
from unittest.mock import MagicMock, patch
from src.integrations.zoho.client import ZohoClient

@pytest.fixture
def zoho_client():
    with patch.dict("os.environ", {
        "ZOHO_CLIENT_ID": "test_id",
        "ZOHO_CLIENT_SECRET": "test_secret",
        "ZOHO_REFRESH_TOKEN": "test_refresh"
    }):
        return ZohoClient()

def test_refresh_access_token(zoho_client):
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        token = zoho_client.refresh_access_token()

        assert token == "new_access_token"
        assert zoho_client._access_token == "new_access_token"
        assert zoho_client._token_expires_at > time.time()
        mock_post.assert_called_once()

def test_get_access_token_cached(zoho_client):
    zoho_client._access_token = "cached_token"
    zoho_client._token_expires_at = time.time() + 1000

    token = zoho_client.get_access_token()

    assert token == "cached_token"

def test_request_with_refresh_on_401(zoho_client):
    with patch("requests.request") as mock_request, \
         patch.object(ZohoClient, "refresh_access_token") as mock_refresh:
        
        # First call returns 401, second returns 200
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "ok"}
        
        mock_request.side_effect = [mock_response_401, mock_response_200]
        mock_refresh.return_value = "new_token"
        
        # Mock get_access_token to return initial token
        with patch.object(ZohoClient, "get_access_token", return_value="old_token"):
            result = zoho_client.request("GET", "test_endpoint")

            assert result == {"data": "ok"}
            assert mock_request.call_count == 2
            mock_refresh.assert_called_once()

def test_request_exception_on_failure(zoho_client):
    with patch("requests.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_request.return_value = mock_response
        
        with patch.object(ZohoClient, "get_access_token", return_value="token"):
            with pytest.raises(requests.exceptions.HTTPError):
                zoho_client.request("GET", "fail_endpoint")
