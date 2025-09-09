"""
Simple currency conversion helper using the Frankfurter API.

Overview
--------
`CurrencyConverter` provides a single method, `convert`, which converts a
numeric `amount` from a given `from_currency` into GBP by calling:

    https://api.frankfurter.app/latest?amount={amount}&from={from_currency}&to=GBP

Key points
----------
- If `from_currency` is already "GBP", the method returns `amount` as a float
  without making a network call.
- Otherwise, it performs a GET request to the Frankfurter API and extracts the
  GBP rate from the JSON response.
- On non-200 responses, it raises an `Exception` with the status code and body.

Dependencies
------------
- `requests` must be installed and importable.

Caveats
-------
- This implementation does not cache results and makes a network call per
  conversion (except when converting from GBP).
- Any network issues, API downtime, or unexpected response formats will raise.
- The API expects ISO 4217 currency codes (e.g., "USD", "EUR", "GBP").
"""

import requests

class CurrencyConverter:
    """
    Convert amounts from a source currency to GBP using the Frankfurter API.
    """
    def convert(self, amount, from_currency):
        """
        Convert `amount` from `from_currency` into GBP.

        Parameters
        ----------
        amount : float | int | str
            The numeric amount to convert. It is interpolated directly into the
            API query string; the result is cast to float before returning.
        from_currency : str
            ISO 4217 currency code (e.g., "USD", "EUR", "GBP").

        Returns
        -------
        float
            Converted amount in GBP.

        Raises
        ------
        Exception
            If the HTTP response status is not 200 OK, includes status code
            and response body in the message.
        """
        # Short-circuit if already GBP to avoid a network call.
        if from_currency == "GBP":
            return float(amount)

        # Query Frankfurter for conversion to GBP.
        response = requests.get(
            f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency}&to=GBP"
        )

        if response.status_code == 200:
            # Extract GBP value from the 'rates' object and return as float.
            return float(response.json()['rates']['GBP'])
        else:
            # Surface HTTP errors explicitly to the caller.
            raise Exception(f"Error: {response.status_code} - {response.text}")
