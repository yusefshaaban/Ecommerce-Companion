"""
eBay-specific job lot creator.

This module defines `EbayJobLotsCreator`, which:
- Queries eBay's Buy/Browse APIs for items/lots (via `EbayRequestHandler`),
- Builds `JobLot` objects from the API payloads,
- Downloads the listing's image locally,
- Converts listing and postage prices to a base currency (via `CurrencyConverter`),
- Extracts items from the downloaded image or description (via `ItemNameExtractor`),
- Computes lot-level metrics (via `LotProcessor`),
- Persists resulting job lots using methods inherited from `JobLotsCreator`.

Expected collaborators / interfaces
-----------------------------------
JobLotsCreator
    - check_job_lot_exists(id) -> bool
    - write(job_lot) -> None
    - file_handler.refresh_working_job_lots() -> None (used by create_custom)
JobLot
    - __init__(source: str, id: str, name: str, web_url: str)
    - attributes set here: buy_price, description, items
LotProcessor
    - process(jobLot) -> None  (mutates jobLot with computed fields)
EbayRequestHandler
    - get_lots(query_param_str) -> dict
    - get_lot_from_id(item_id) -> dict
    - get_lot_description(item_id) -> str
CurrencyConverter
    - convert(value: float, currency: str) -> float
ItemNameExtractor
    - extract_items(image_path_or_text) -> list[Item]  (this code passes an image path)
    
Notes & caveats
---------------
- `process()` assumes `price` and `currency` are present; otherwise it sets
  `listing_price` to a string ("Price not available") and subsequently adds it
  to a float, which would raise a TypeError if reached. Behavior preserved.
- Image extension is inferred from the URL; file is always saved as JPEG.
- Network and I/O errors are only partially handled; exceptions may propagate.
- `create_custom_from_link` expects a URL containing an "itm/<digits>" pattern.
"""

import re
import requests
from JobLot import JobLot
from LotProcessor import LotProcessor
from EbayRequestHandler import EbayRequestHandler
from CurrencyConverter import CurrencyConverter
from ItemNameExtractor import ItemNameExtractor
from JobLotsCreator import JobLotsCreator
from PIL import Image # type: ignore
from io import BytesIO

class EbayJobLotsCreator(JobLotsCreator):
    """
    Creates and persists job lots based on eBay listings.

    Responsibilities
    ----------------
    - Fetch raw lots from eBay (by query or direct link),
    - De-duplicate against existing stored lots,
    - Transform raw lot data into `JobLot` instances,
    - Enrich with pricing, images, items, and computed metrics,
    - Write to storage via inherited `write`.
    """

    def __init__(self):
        """
        Initialize external dependencies used during lot creation.
        """
        super().__init__()
        self.ebay_request_handler = EbayRequestHandler()
        self.currency_converter = CurrencyConverter()
        self.item_name_extractor = ItemNameExtractor()
        self.lot_processor = LotProcessor()

    def create(self, search, limit = 10):
        """
        Create lots from an eBay search query.

        Parameters
        ----------
        search : str
            Search term passed to the eBay Browse API (e.g., "job lot iphone").
        limit : int, default=10
            Maximum number of item summaries to request.

        Side Effects
        ------------
        - For each unseen lot, builds and processes a `JobLot` and writes it.
        """
        response_data = self.ebay_request_handler.get_lots(f"q={search}&limit={limit}")
        lots = response_data.get('itemSummaries')
        for lot in lots:
            id = str(lot.get('itemId'))
            price = lot.get('price', {}).get('value')
            currency = lot.get('price', {}).get('currency')
            postage_price = lot.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') if lot.get('shippingOptions', {}) else None
            postage_currency = lot.get('shippingOptions', {})[0].get('shippingCost', {}).get('currency') if lot.get('shippingOptions', {}) else None
            # Convert listing price to base currency (if present).
            listing_price = self.currency_converter.convert(price, currency) if price and currency else "Price not available"
            postage_price = self.currency_converter.convert(postage_price, postage_currency) if postage_price and postage_currency else "Postage not available"

            if super().check_job_lot_exists(id, listing_price, postage_price):
                continue
            lot = self.process(lot)
            super().write(lot)

    def create_custom(self, searches):
        """
        Create lots from one or more direct eBay links.

        Parameters
        ----------
        searches : str
            A string that may contain eBay links (comma-separated). If it
            contains a recognized domain (.com, .co.uk, .de, .fr, .es, .it),
            each link will be processed via `create_custom_from_link`.

        Side Effects
        ------------
        - Refreshes working job lots.
        - Writes new processed lots to storage.
        """
        domains = ('.com', '.co.uk', '.de', '.fr', '.es', '.it')
        if any((domain) in searches.lower() for domain in domains):
            links = searches.split(',')
            for link in links:
                self.create_custom_from_link(link)
        else:
            print("No valid eBay links found in the input.")

    def create_custom_from_link(self, link):
        """
        Build and persist a job lot from a single eBay item URL.

        Parameters
        ----------
        link : str
            Full eBay item URL. The numeric item id is extracted from an
            "itm/<digits>" segment and converted to the v1 id format.

        Notes
        -----
        - If the lot payload is found, it is processed and written.
        - If not found, a message is printed.
        """
        link = link.strip()
        if link:
            # Extract numeric item id from the URL.
            item_id = re.findall(r'itm/\d+', link)
            item_id = re.sub(r'itm/', '', item_id[0]) if item_id else None
            item_id = f"v1|{item_id}|0"
            # if super().check_job_lot_exists(item_id):
            #     continue
            response_data = self.ebay_request_handler.get_lot_from_id(item_id)
            # lot = response_data.get('itemSummaries')
            if response_data:
                lot = self.process(response_data)
                super().write(lot)
            else:
                print(f"Lot not found for ID: {item_id}")

    def process(self, lot):
        """
        Transform a raw eBay lot payload into a processed `JobLot`.

        Steps
        -----
        1) Extract core fields (id, title, url, price, currency).
        2) Determine postage price and convert to base currency.
        3) Choose image URL (thumbnail first, falling back to main image).
        4) Download and save the image locally (always as JPEG).
        5) Convert listing price and compute `buy_listing_price` (listing + postage).
        6) Fetch description and extract items (image-based here).
        7) Run `LotProcessor` to compute lot-level metrics.

        Parameters
        ----------
        lot : dict
            Raw eBay item payload as returned by the Browse API.

        Returns
        -------
        JobLot
            The populated and processed job lot instance.

        Caveats
        -------
        - If `value`/`currency` are missing, `listing_price` is set to a string,
          which will cause a TypeError when added to a float; preserved as-is.
        - Image extension is inferred from URL and sanitized for filename; file
          is still saved in JPEG format regardless of URL extension.
        """
        value = lot.get('price', {}).get('value')
        currency = lot.get('price', {}).get('currency')
        postage_value = 0
        postage_currency = 'GBP'
        # Pull first shipping option if present; else `None`.
        postage_value = lot.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') if lot.get('shippingOptions', {}) else None
        postage_currency = lot.get('shippingOptions', {})[0].get('shippingCost', {}).get('currency') if lot.get('shippingOptions', {}) else None
        postage_price = float(self.currency_converter.convert(postage_value, postage_currency)) if postage_value and postage_currency else 0
        # Prefer thumbnail image; fall back to main image.
        if lot.get('thumbnailImages'):
            image = lot.get('thumbnailImages', {})[0].get('imageUrl')
        else:
            image = lot.get('image').get('imageUrl')
        job_lot = JobLot(
                "ebay",
                lot.get('itemId'),
                lot.get('title'),
                lot.get('itemWebUrl')
            )
        print(f"\nprocessing job lot: {job_lot.name}")
        # Extract image extension from URL, default to 'jpeg' if not found
        ext_match = re.search(r'\.(png|jpeg|jpg|gif|webp)(?:\?|$)', image, re.IGNORECASE)
        ext = ext_match.group(1).lower() if ext_match else "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        # Sanitize filename: replace non-alphanumeric with underscores.
        image_path = f"./Operations/Images/{re.sub(r'[^a-zA-Z0-9]', '_', lot.get('title'))}_image.{ext}"
        # Download and persist the image.
        self.download_image(image_path, image)

        # Convert listing price (if present) to base currency.
        listing_price = self.currency_converter.convert(value, currency) if value and currency else "Price not available"

        # Total buy price = listing + postage (rounded).
        job_lot.buy_price = round(listing_price, 2)
        job_lot.buy_postage_price = round(postage_price, 2)
        job_lot.buy_other_fees = 0
        job_lot.buy_listing_price = round(listing_price + postage_price, 2)
        # Retrieve plain-text description via API.
        job_lot.description = self.ebay_request_handler.get_lot_description(job_lot.id)
        # Extract items from the image (as per current pipeline).
        # job_lot.set_items(self.item_name_extractor.extract_items(job_lot.description))
        job_lot.items = self.item_name_extractor.extract_items(image_path)

        job_lot.condition = lot.get('condition', 'New')  # eBay listings are typically new items.
        # Compute lot-level metrics (sell price, profit, rating, etc.).
        self.lot_processor.process(job_lot)
        return job_lot
    
    def download_image(self, path, image_url):
        """
        Download an image and save it as JPEG to `path`.

        Parameters
        ----------
        path : str
            Destination file path (extension included).
        image_url : str
            Source image URL.

        Behavior
        --------
        - Streams the image; converts to RGB; saves as JPEG.
        - On failure, prints a message to stdout.
        """
        response = requests.get(image_url, stream=True)

        if response.status_code == 200:
            # Read image data into memory
            img_data = BytesIO(response.content)
            try:
                img = Image.open(img_data)
                rgb_img = img.convert('RGB')  # Ensure compatibility with JPEG
                rgb_img.save(path, format='JPEG')
            except Exception as e:
                print(f"Failed to convert and save image as JPEG: {e}")
        else:
            print(f"Failed to download image. Status code: {response.status_code}")


if __name__ == "__main__":
    # Example usage: create a lot from a direct eBay link.
    ebay_job_lots_creator = EbayJobLotsCreator()
    jl = ebay_job_lots_creator.create_custom_from_link("https://www.ebay.com/itm/111962319036?_skw=job+lot&itmmeta=01K45K2X3BZZF49N8SEFNMJRQN&hash=item1a117968bc:g:a54AAOSwiAdoJe4x&itmprp=enc%3AAQAKAAAAwFkggFvd1GGDu0w3yXCmi1eh6q2rG2xGnnbqPBpFgbJC9g59Jt1CmFHaCpY%2Bg32rzS7v%2BKDlPtsUDMLU2rDG88aib%2F9TS%2B9eH8%2FuWToPy%2BqjEcY5Wt0Atz3wvbE%2BA8vph4k%2BCCynn9G74eA%2FhP%2FAhuxzfzAJZMxK%2F1NTvmUaHSfU4FUAIcw6IKU3aV29fKlTbNT%2FJ8ykBx5RDIoMvp4ULGZCjqh40AY9o%2B%2BlC10vdwW41makpbHfFqcDghp0e_")
