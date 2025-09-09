"""
eBay Buy APIs request handler.

This module provides a thin wrapper around several eBay Buy APIs:
- Identity: OAuth2 client-credentials grant to obtain an access token.
- Browse: item/lot search and item details.
- Marketplace Insights (beta): past sales for a given query.

Environment variables (required)
--------------------------------
- EBAY_PROD_CLIENT_ID
- EBAY_PROD_CLIENT_SECRET
- EBAY_OAUTH_TOKEN
    Note: The class checks for this var at import time. The instance will
    subsequently fetch a fresh token via client-credentials and overwrite
    `self.OAUTH_TOKEN` in __init__.

Conventions & notes
-------------------
- Default marketplace header is GB for most requests, except
  `get_past_items()` which uses EBAY_US (as written).
- `get_items()` uses an API filter with literal curly braces for
  eBay's query syntax (e.g., buyingOptions:{FIXED_PRICE}); those curls
  are part of the string and not Python formatting.
- HTML descriptions are converted to plain text via BeautifulSoup.
- This module intentionally retains unused imports/variables if present
  in the original source, to avoid changing behavior.
"""

import os
import numpy as np
import base64
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup

# Possible keys: 'itemId', 'title', 'itemGroupHref', 'leafCategoryIds', 'categories', 'image', 'price', 'itemGroupType', 'itemHref', 'seller', 'condition', 'conditionId', 'thumbnailImages', 'shippingOptions', 'buyingOptions', 'epid', 'itemWebUrl', 'itemLocation', 'additionalImages', 'adultOnly', 'legacyItemId', 'availableCoupons', 'itemOriginDate', 'itemCreationDate', 'topRatedBuyingExperience', 'priorityListing', 'listingMarketplaceId'

class EbayRequestHandler:
    """
    Handles authentication and requests to eBay Buy endpoints.

    Attributes
    ----------
    OAUTH_TOKEN : str
        Access token used for API calls. Initially validated from env vars
        at class-load time; then refreshed in __init__ via client credentials.
    EBAY_PROD_CLIENT_ID : str
    EBAY_PROD_CLIENT_SECRET : str
        Client credentials loaded from environment.
    encoded_credentials : str
        Base64-encoded "client_id:client_secret" used for token retrieval.
    headers : dict
        Default headers for eBay Buy API calls.
    """
    load_dotenv()
    OAUTH_TOKEN = os.getenv('EBAY_OAUTH_TOKEN')
    # REFRESH_TOKEN = os.getenv('EBAY_REFRESH_TOKEN')
    EBAY_PROD_CLIENT_ID = os.getenv('EBAY_PROD_CLIENT_ID')
    EBAY_PROD_CLIENT_SECRET = os.getenv('EBAY_PROD_CLIENT_SECRET')
    if not EBAY_PROD_CLIENT_ID or not EBAY_PROD_CLIENT_SECRET:
        raise ValueError("EBAY_PROD_CLIENT_ID and EBAY_PROD_CLIENT_SECRET must be set in the environment variables.")
    if not OAUTH_TOKEN:
        raise ValueError("OAUTH_TOKEN is not set in the environment variables.")
    

    def __init__(self):
        """
        Build default auth header with a freshly obtained access token.

        Notes
        -----
        - Uses OAuth2 client-credentials grant to request a bearer token.
        - Sets marketplace context and location to GB by default.
        """
        self.credentials = f"{self.EBAY_PROD_CLIENT_ID}:{self.EBAY_PROD_CLIENT_SECRET}"
        self.encoded_credentials = base64.b64encode(self.credentials.encode()).decode()
        self.OAUTH_TOKEN = self.get_user_access_token()
        self.headers = {
            "Authorization": f"Bearer {self.OAUTH_TOKEN}",
            "Content-Type": "application/json",
            "X-EBAY-C-ENDUSERCTX": "contextualLocation=country%3DGB%2Czip%3DM26%202QP",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"
        }


    def get_user_access_token(self):
        """
        Obtain an OAuth2 access token via the client-credentials grant.

        Returns
        -------
        str
            The access token to be used in Authorization headers.

        Raises
        ------
        Exception
            If the token endpoint returns a non-200 status.
        """
        headers = {
            "Authorization": f"Basic {self.encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        response = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers=headers,
            data=data
        )

        if response.status_code == 200:
            token = response.json().get('access_token')
            return token
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")


    def get_lots(self, parameter):
        """
        Search for lots/items using the Browse API.

        Parameters
        ----------
        parameter : str
            Query string portion (e.g., "q=iphone&limit=10").

        Returns
        -------
        dict
            Parsed JSON response from eBay.

        Raises
        ------
        Exception
            If the response is not 200 OK.

        Notes
        -----
        - Filters results to NEW condition and deliveryCountry=GB.
        """
        url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?{parameter}&filter=conditions:{{NEW}},deliveryCountry:GB"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()  # Return the JSON response
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")
    

    def get_lot_from_id(self, parameter):
        """
        Retrieve a single item/lot by its eBay item ID.

        Parameters
        ----------
        parameter : str
            The item identifier (e.g., "v1|XXXXXXXXX|0").

        Returns
        -------
        dict
            Parsed JSON item object.

        Raises
        ------
        Exception
            If the response is not 200 OK.
        """
        url = f"https://api.ebay.com/buy/browse/v1/item/{parameter}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()  # Return the JSON response
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")


    def get_items(self, name, params=None):
        """
        Search fixed-price items (GB marketplace) using the Browse API.

        Parameters
        ----------
        parameter : str
            Query string portion (e.g., "q=iphone&limit=10").

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        Exception
            If the response is not 200 OK.

        Notes
        -----
        - Filters include:
          buyingOptions:{FIXED_PRICE}, conditions:{NEW},
          deliveryCountry:GB, itemLocationCountry:GB
        """
        url = (
            "https://api.ebay.com/buy/browse/v1/item_summary/search?"
            f"{name}"
            f"&{params}"
        )

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()  # Return the JSON response
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")
        

    def get_lot_description(self, itemId):
        """
        Fetch an item's HTML description and return a plain-text version.

        Parameters
        ----------
        itemId : str
            eBay item identifier.

        Returns
        -------
        str
            Plain-text description extracted from the item's HTML.

        Raises
        ------
        Exception
            If the response is not 200 OK.

        Notes
        -----
        - Uses BeautifulSoup with the built-in 'html.parser'.
        """
        url = f"https://api.ebay.com/buy/browse/v1/item/{itemId}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            html_description = response.json().get('description')
            gfg = BeautifulSoup(html_description, 'html.parser');
            description = gfg.get_text()

            return description
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")   


    def get_past_items(self):
        """
        Example method using Marketplace Insights (beta) to fetch recent sales.

        Behavior
        --------
        - Queries for "iPhone 15" (limit 5) on EBAY_US.
        - Prints title, sold price, sold date, and itemId for each result.

        Notes
        -----
        - This method prints to stdout and returns None.
        - Response JSON is attempted; falls back to raw text on parse failure.
        - Requires the `X-EBAY-C-MARKETPLACE-ID` header to match the target site.
        """
        headers = {
            "Authorization": f"Bearer {self.OAUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }

        params = {
            "q": "iPhone 15",
            "limit": 5,
        }

        url = "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search"

        resp = requests.get(url, headers=headers, params=params)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.ok:
            for item in data.get("itemSales", []):
                print(f"Title: {item['title']}")
                print(f"Sold Price: {item['price']['value']} {item['price']['currency']}")
                print(f"Sold Date: {item['soldDate']}")
                print(f"Item ID: {item['itemId']}")
                print("---")
        else:
            print(f"Error: {resp.status_code} - {data}")



if __name__ == "__main__":
    # Example execution: fetch and print recent sales for a demo query.
    ebay_request_handler = EbayRequestHandler()
    ebay_request_handler.get_past_items()
    # user_access_token = ebay_request_handler.get_user_access_token()
    # ebay_request_handler.check_refresh_token()
