"""
Product processing pipeline.

Overview
--------
Given an `Item` (what the user actually wants) and a scraped `Product`,
`ProductProcessor`:
  1) Cleans/normalizes the product (names, units, price heuristics).
  2) Generates several POS-filtered name variants.
  3) Scores each filtered variant for accuracy against the `Item`.
  4) Aggregates those scores into a single accuracy for the base `Product`.
  5) Maps that accuracy to a `buy_quality_score` using tiered thresholds.

Outputs
-------
Mutates the input `Product` in-place, setting:
  - `product.accuracy_score` (0–100)
  - `product.buy_quality_score` (tiered, up to 1000)

Dependencies (by module/class name)
-----------------------------------
- CurrencyConverter: (held on instance for possible upstream/downstream use)
- UnitConvertor: used by ProductCleaner internally for unit normalization
- ProductCleaner: canonicalizes names, packs, units, and price/accuracy heuristics
- WordFilterer: filters names by part-of-speech for alternate matching views
- FilterScheme: config container for POS sets & weights
- ProductCalculator (as `calc`): provides `set_accuracy(item, product)`
"""

from CurrencyConverter import CurrencyConverter
from Item import Item
from Product import Product
from UnitConvertor import UnitConvertor
from ProductCleaner import ProductCleaner
from WordFilterer import WordFilterer
from FilterScheme import FilterScheme
import ProductCalculator as calc


class ProductProcessor:
    """
    Orchestrates the end-to-end product normalization and scoring pipeline.

    The processor maintains a set of `FILTERSCHEMES`, each defining a POS subset
    (e.g., NOUN-only vs. NOUN+PROPN+ADJ) and a weight. Stricter schemes
    (fewer POS types) generally carry higher weights.
    """

    # POS-filtering schemes used to create multiple "views" of the variant name.
    # Later aggregation favors stricter schemes via higher weights.
    FILTERSCHEMES = [
        FilterScheme(word_type=("NOUN", "PROPN", "ADJ", "ADV"), weight=1.0),
        FilterScheme(word_type=("NOUN", "PROPN", "ADJ"), weight=1.3),
        FilterScheme(word_type=("NOUN", "PROPN"), weight=1.7),
        FilterScheme(word_type=("NOUN",), weight=3.0),
    ]

    def __init__(self):
        """
        Initialize collaborating components used throughout the pipeline.

        Notes:
            - `currency_converter` and `unit_converter` are stored on the instance
              for parity/extensibility, though this class defers unit work to
              `ProductCleaner` and price accuracy to `calc.set_accuracy`.
        """
        self.currency_converter = CurrencyConverter()
        self.unit_converter = UnitConvertor()
        self.cleaner = ProductCleaner()
        self.word_filterer = WordFilterer()

    def process(self, item, product):
        """
        Run the full processing pipeline on a single product.

        Steps:
            1) Clean raw product fields relative to the item context.
            2) Create several POS-filtered variants of the product name.
            3) Compute accuracy for each filtered variant.
            4) Set the product's final accuracy as a weighted average.
            5) Convert the final accuracy into a `buy_quality_score` via thresholds.

        Args:
            item (Item): The target item (brand, variant, quantity, etc.).
            product (Product): The candidate product to evaluate/score.

        Side Effects:
            Mutates `product` (name may be normalized by cleaner; sets
            `accuracy_score` and `buy_quality_score`).
        """
        # 1) Normalize/clean the product data using the item context
        self.clean_product(item, product)

        if self.FILTERSCHEMES:
            # 2) Generate multiple POS-filtered variants of the product name
            filtered_products = self.filter_name(item, product)

            # 3) Compute accuracy per filtered variant
            for filtered_product in filtered_products:
                # `calc.set_accuracy` compares the (filtered) product to the item
                calc.set_accuracy(item, filtered_product[0])

            # 4) Aggregate the accuracies into one final product score
            self.set_average_product_info(product, filtered_products)

        # 5) Map accuracy (0–100) to a tiered buy_quality_score.
        self.map_accuracy_to_quality_score(product)

    def clean_product(self, item, product):
        """
        Normalize product attributes (e.g., casing, noisy tokens, units/prices)
        using `ProductCleaner` with the item as context.

        Args:
            item (Item): Target item (provides brand/variant anchors).
            product (Product): Product to clean in-place.
        """
        self.cleaner.clean(item, product)

    def filter_name(self, item, product):
        """
        Create multiple filtered copies of the product by keeping only certain POS tags.

        Rationale:
            Listings use varied phrasing; by progressively tightening POS sets
            (NOUN+PROPN+ADJ+ADV → NOUN-only), we obtain alternative views that may
            match the item more robustly.

        Args:
            item (Item): Provides context for WordFilterer (e.g., brand/variant).
            product (Product): The base product to clone/filter.

        Returns:
            list[tuple[Product, float]]: Pairs of (filtered_product, weight).
        """
        filtered_items = []
        for scheme in self.FILTERSCHEMES:
            filtered_product = product.copy()
            # `filter_product` mutates `filtered_product`'s name fields in place.
            self.word_filterer.filter_product(item, filtered_product, scheme.word_type)
            filtered_items.append((filtered_product, scheme.weight))
        return filtered_items

    def set_average_product_info(self, product, filtered_products):
        """
        Combine accuracy scores from filtered variants into `product.accuracy_score`.

        Uses a weighted average where stricter filters contribute more.

        Args:
            product (Product): The original product whose `accuracy_score` is set.
            filtered_products (list[tuple[Product, float]]): Filtered variants with weights.
        """
        accuracy_score = 0
        total_weight = 0
        for filtered_product, weight in filtered_products:
            accuracy_score += filtered_product.accuracy_score * weight
            total_weight += weight

        product.accuracy_score = round(accuracy_score / total_weight, 2)

    def map_accuracy_to_quality_score(self, product):
        """
        Map an accuracy score (0–100) to a non-linear `buy_quality_score`.

        Design:
            Higher accuracy is rewarded disproportionately to strongly prefer
            close matches. The mapping is stepped rather than continuous.

        Notes:
            Uses Python 3.10+ structural pattern matching (`match`/`case`).
        """
        # The mapping is intentionally non-linear—higher accuracy gets disproportionately
        # higher "buy quality" to strongly prefer close matches.
        match product.accuracy_score:
            case 100:
                product.buy_quality_score = 1000
            case s if s >= 95:
                product.buy_quality_score = 970
            case s if s >= 90:
                product.buy_quality_score = 930
            case s if s >= 85:
                product.buy_quality_score = 890
            case s if s >= 80:
                product.buy_quality_score = 850
            case s if s >= 75:
                product.buy_quality_score = 810
            case s if s >= 70:
                product.buy_quality_score = 760
            case s if s >= 65:
                product.buy_quality_score = 710
            case s if s >= 60:
                product.buy_quality_score = 660
            case s if s >= 55:
                product.buy_quality_score = 600
            case s if s >= 50:
                product.buy_quality_score = 540
            case s if s >= 45:
                product.buy_quality_score = 480
            case s if s >= 40:
                product.buy_quality_score = 410
            case s if s >= 30:
                product.buy_quality_score = 260
            case s if s >= 20:
                product.buy_quality_score = 110
            case s if s >= 10:
                product.buy_quality_score = 10
            case s if s >= 5:
                product.buy_quality_score = 3
            case s if s >= 3:
                product.buy_quality_score = 1
            case s if s >= 1:
                product.buy_quality_score = 0.1
            case _:
                # For 0 or negative scores, leave buy_quality_score unset.
                pass


if __name__ == "__main__":
    # Example usage / quick smoke test:
    # 1) Build a processor, a sample Item, and a sample Product.
    # 2) Process the product and print the outcome.
    processor = ProductProcessor()
    item = Item(
        "NYX Ombre Lip Duo 1",
        brand_name="NYX",
        variant_name="Ombre Lip Duo 1",
        original_brand_name="",
        original_variant_name="test",
        quantity=1,
        measurements=[],
    )
    product = Product(
        "NYX Professional Ombre Lip Duo Liner & Stick Line & Define "
        "NYX Professional Ombre Lip Duo Liner and Stick Line and Define,",
        web_url="http://example.com",
        buy_price=20.0,
    )
    processor.process(item, product)
    print(product)
