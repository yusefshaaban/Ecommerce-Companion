"""
Lot processing utilities.

This module defines `LotProcessor`, which aggregates and scores a "job lot"
of items (e.g., beauty items) by delegating per-item processing to
`BeautyItemProcessor` and then computing lot-level metrics.

Expected interfaces
-------------------
jobLot:
    - buy_price: float | None
        Purchase price for the entire lot (None if unknown).
    - items: Iterable[item]
        A collection of item objects with the attributes below.
    - (attributes set by this processor)
        sell_price: float
        postage_price: float
        listing_price: float
        profit: float
        accuracy_score: float
        rating: float

item (each element in jobLot.items):
    - quantity: int
    - listing_price: float
    - buyer_protection_fee: float
    - postage_price: float
    - price_quality: float
        A quality signal used for ranking/scoring.
    - accuracy_score: float
        Per-item identification/estimation confidence.
    - (attributes possibly added/updated by BeautyItemProcessor)

Notes on calculations
---------------------
- Total sell price = Σ (listing_price + buyer_protection_fee) * quantity
- Total postage price = Σ postage_price * quantity
- Lot accuracy score = (Σ accuracy_score * quantity) / total_quantity
- Total score = Σ price_quality * quantity, then lightly normalized by
  multiplying by (num_items ** 0.1) to slightly penalize smaller lots.
- Profit = total_sell_price - (buy_listing_price + total_postage_price)
  (If buy_listing_price is None, profit defaults to 0.)
- Rating = round( total_score * profit ** 1.2, 2 ) if profit > 0 else 0

Side effects
------------
- Mutates `jobLot.items` by sorting in descending order of `price_quality`.
- Writes computed lot-level attributes back onto `jobLot`.

All monetary values are assumed to be in the same currency.
"""

from BeautyItemProcessor import BeautyItemProcessor
from datetime import datetime


class LotProcessor:
    """
    Aggregates per-item metrics into lot-level metrics and ranking.

    This processor:
    1) Runs `BeautyItemProcessor.process` on each item.
    2) Accumulates weighted totals across the lot.
    3) Sorts items by `price_quality` (descending) for presentation.
    4) Computes and assigns lot-level fields on `jobLot`:
       sell_price, postage_price, listing_price, profit,
       accuracy_score, rating.
    """

    def __init__(self):
        """
        Initialize the lot processor and its underlying item processor.
        """
        self.item_processor = BeautyItemProcessor()

    def process(self, jobLot):
        """
        Compute lot-level metrics and annotate the provided `jobLot`.

        Parameters
        ----------
        jobLot : object
            An object with:
              - buy_price: float | None
              - items: iterable of item objects (see module docstring
                       for expected item attributes).

        Returns
        -------
        None
            Results are written back onto `jobLot`:
              - jobLot.sell_price (float)
              - jobLot.postage_price (float)
              - jobLot.listing_price (float)
              - jobLot.profit (float)
              - jobLot.accuracy_score (float)
              - jobLot.rating (float)
            Also sorts `jobLot.items` in-place by `price_quality` desc.

        Notes
        -----
        - If `jobLot.buy_price` is None, profit and rating default to 0.
        - A slight normalization (num_items ** 0.1) dampens the influence
          of very large lots on the total score.
        """
        # Sort items for presentation/consumption by descending price_quality.
        jobLot.items = sorted(jobLot.items, key=lambda x: x.price_quality, reverse=True)

        total_accuracy_score = 0
        total_sell_price = 0
        total_postage_price = 0
        total_other_fees = 0
        total_score = 0
        num_items = 0

        # Process each item and accumulate weighted sums.
        for item in jobLot.items:
            # Allow the item processor to fill/adjust item-level fields.
            params = {
                "filter": f"filter=",
                "buyingOptions": f"buyingOptions:{{FIXED_PRICE}}",
                "conditions": f"conditions:{jobLot.condition.upper()}",
                "deliveryCountry": f"deliveryCountry:GB",
                "itemLocationCountry": f"itemLocationCountry:GB"
            }
            self.item_processor.process(item, params)

            # Weighted accuracy and scoring by quantity.
            total_accuracy_score += item.accuracy_score * item.quantity
            total_sell_price += (item.sell_price) * item.quantity
            total_postage_price += item.postage_price * item.quantity
            total_other_fees += item.buyer_protection_fee * item.quantity
            total_score += item.price_quality * item.quantity
            num_items += item.quantity
        
        jobLot.sell_price = round(total_sell_price, 2)
        jobLot.postage_price = round(total_postage_price, 2)
        jobLot.listing_price = round(total_sell_price + total_postage_price + total_other_fees, 2)

        # Slightly normalize the total score to avoid over-favoring smaller lots.
        if num_items > 0:
            total_score *= (num_items ** .1)

        # Profit calculation; if buy_listing_price is unknown, profit defaults to 0.
        jobLot.profit = round(total_sell_price - (jobLot.buy_listing_price) if jobLot.buy_listing_price is not None else 0, 2)

        # Rating rewards lots, and making sure rating always computes
        if jobLot.profit <= 0:
            n = -1
        else:
            n = 1
        jobLot.rating = round(n * ((total_score) * ((n * (jobLot.profit)) ** 1.2)), 2) if jobLot.profit != 0 else 0

        # Average (quantity-weighted) accuracy across the lot.
        jobLot.accuracy_score = round(total_accuracy_score / num_items, 2) if num_items != 0 else 0

        current_date = datetime.now().strftime("%d_%m_%Y")

        jobLot.date_created = current_date