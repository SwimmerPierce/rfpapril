import os
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ZohoClient:
    def __init__(self):
        self.client_id = os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        self.accounts_url = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
        self.api_url = os.getenv("ZOHO_API_URL", "https://www.zohoapis.com/crm/v2")
        
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        
        return self.refresh_access_token()

    def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token."""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Zoho credentials missing from environment variables.")
            
        url = f"{self.accounts_url}/oauth/v2/token"
        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if "access_token" not in data:
            raise ValueError(f"Failed to refresh access token: {data}")
            
        self._access_token = data["access_token"]
        # expires_in is usually 3600 seconds
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        
        return self._access_token

    def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to the Zoho CRM API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Zoho-oauthtoken {self.get_access_token()}"
        kwargs["headers"] = headers
        
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 401:
            # Token might have expired, refresh and retry once
            headers["Authorization"] = f"Zoho-oauthtoken {self.refresh_access_token()}"
            response = requests.request(method, url, **kwargs)
            
        response.raise_for_status()
        
        # Some endpoints might return 204 No Content
        if response.status_code == 204:
            return {}
            
        return response.json()

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        return self.request("POST", endpoint, json=json, **kwargs)

    def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        return self.request("PUT", endpoint, json=json, **kwargs)
