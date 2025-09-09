from ItemProcessor import ItemProcessor
from BeautyProductProcessor import BeautyProductProcessor
from Item import Item


"""
Beauty item processing pipeline.

Overview
--------
This module defines `BeautyItemProcessor`, a specialized `ItemProcessor`
for beauty/cosmetics items. It delegates product lookups and enrichment
to `BeautyProductProcessor`, then relies on the base class logic to
estimate prices, compute per-item quality/accuracy signals, and attach
ranked product candidates.

Dependencies / expected collaborators
------------------------------------
- ItemProcessor
    Base class expected to provide a `.process(item)` method that:
      * enriches `item` with candidate `products`,
      * computes fields like `item.accuracy_score`, `item.price_quality`,
        `item.listing_price`, `item.buyer_protection_fee`, etc.
- BeautyProductProcessor
    Domain-specific product retriever/normalizer for beauty items
    (e.g., queries eBay, normalizes titles, prices, and attributes).
- Item
    Domain object representing an inventory item to be processed.

Key tuning parameters (class attributes)
---------------------------------------
- CHEAPNESS_AGGRESSION (int):
    How aggressively to undercut or bias toward cheaper options during
    price estimation/ranking in the base pipeline (higher = more aggressive).
- PRODUCTS_BELOW_MULTIPLIER (float):
    A multiplier threshold used to filter/weight products that are priced
    below an estimated baseline.
- WORKING_ACC_MINIMUM_LENGTH (int):
    Minimum length for tokens/terms considered when computing a working
    accuracy signal (helps ignore short/low-signal terms).
"""


class BeautyItemProcessor(ItemProcessor):
    """
    Item processor specialized for beauty products.

    Responsibilities
    ----------------
    - Initialize a `BeautyProductProcessor` for fetching/normalizing product
      candidates in the beauty domain.
    - Configure domain-specific hyperparameters that influence downstream
      scoring and filtering performed by the base `ItemProcessor`.
    """

    def __init__(self):
        """
        Initialize the beauty product pipeline components and hyperparameters.

        Attributes
        ----------
        product_processor : BeautyProductProcessor
            Component responsible for searching/normalizing beauty products.
        CHEAPNESS_AGGRESSION : int
            See module docstring for details.
        PRODUCTS_BELOW_MULTIPLIER : float
            See module docstring for details.
        WORKING_ACC_MINIMUM_LENGTH : int
            See module docstring for details.
        """
        super().__init__()
        self.product_processor = BeautyProductProcessor()
        self.CHEAPNESS_AGGRESSION = 5
        self.PRODUCTS_BELOW_MULTIPLIER = .65
        self.WORKING_ACC_MINIMUM_LENGTH = 8


if __name__ == "__main__":
    # Demonstration: process a single beauty item and print ranked products.
    # Note: Running this may perform network requests depending on the
    # implementations of BeautyProductProcessor/ItemProcessor.
    beauty_item_processor = BeautyItemProcessor()
    item = Item(
        "The Body Shop Strawberry Body Butter - 6 x 50ml",
        brand_name="The Body Shop",
        variant_name="Strawberry Body Butter - 6 x 50ml",
        quantity=1,
        original_name="The Body Shop Strawberry Body Butter - 6 x 50ml",
    )
    beauty_item_processor.process(item)
    n = 0
    for product in item.products:
        print(f"{n}. Product: {product.name}, Buy Price: {product.buy_price}, Accuracy Score: {product.accuracy_score}, web_url: {product.web_url}\n")
        n += 1
    print(item)
