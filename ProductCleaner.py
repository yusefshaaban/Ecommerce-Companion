"""
Product cleaning utilities.

This module provides `ProductCleaner`, a concrete cleaner built on top of
`GoodCleaner` that normalizes a `Product` relative to an `Item` reference.
It:
  - Derives brand/variant names from raw strings.
  - Collapses pack/multiplicative expressions (e.g., "6 pack", "4 x 50ml").
  - Converts units in the product name to match the item's units.
  - Adjusts price and accuracy scores based on inferred quantity/size changes.

Dependencies expected from the parent `GoodCleaner`:
  - `self.unit_convertor`: exposes `get_units()` -> set[str] and
    `convert(value: float, from_unit: str, to_unit: str) -> float`.

Notes
-----
- Tokenization for name processing is handled by `TokenSet`, which provides
  both raw and normalized token sequences.
- Numeric detection relies on `str.isdigit()`, so decimals in names are
  expected to be tokenized separately by `TokenSet`.
"""

import re
import numpy as np  # NOTE: Imported but not referenced in this file; kept for parity/consistency with surrounding codebase.
from GoodCleaner import GoodCleaner
from Item import Item
from Product import Product
from TokenSet import TokenSet


class ProductCleaner(GoodCleaner):
    """
    Clean and normalize `Product` metadata relative to an `Item`.

    Primary responsibilities:
      * Populate/normalize brand and variant names.
      * Remove pack/multiplicative terms from the displayed variant name.
      * Convert and align units in the variant name to the item's units.
      * Adjust pricing/accuracy heuristics based on inferred quantity changes.

    The public entry point is `clean(product, item)`.
    """

    def __init__(self):
        """Initialize the cleaner; delegates to `GoodCleaner`."""
        super().__init__()

    def clean(self, item, product):
        """
        Orchestrate the cleaning pass for a single product.

        Args:
            item (Item): The reference item whose brand/measurements drive normalization.
            product (Product): The product to mutate in-place.

        Side Effects:
            Mutates `product` fields: name, brand_name, variant_name,
            listing_price, accuracy_score, original_brand_name, original_variant_name.
        """
        item_units, item_values = self.get_measurements(item)
        self.set_name(product, item)
        self.adjust_quantities(product)
        self.adjust_measurements(product, item_units, item_values)
        super().clean_basic(product)


    def set_name(self, product, item):
        """
        Determine and set canonical brand and variant names for the product.

        Rules:
          * If product has an unset/placeholder variant, seed it from product.name.
          * If product brand is unset/placeholder and the item brand is present:
              - If the item brand appears in the product name, set brand_name to the
                item brand and remove that token from the variant portion.
              - Otherwise leave brand empty (brand unknown).
          * Compose `product.name` as "brand variant" (trimmed).
          * Preserve originals in `original_brand_name`/`original_variant_name`.
        """
        # If blank/placeholder, copy from product.name so we have a working variant.
        if product.variant_name == "" or product.variant_name == "variant":
            product.variant_name = product.name

        if product.brand_name == "" or product.brand_name == "brand":
            if item.brand_name != "":
                if item.brand_name.lower() in product.name.lower():
                    # Snap brand to the item's brand and remove it from the variant.
                    product.brand_name = ""
                    product.brand_name = item.brand_name
                    product.variant_name = re.sub(
                        rf'\b{re.escape(item.brand_name)}\b', '', product.name, flags=re.IGNORECASE
                    ).strip()
                else:
                    # Brand present in item but not found in product name -> unknown brand for product.
                    product.brand_name = ""
            else:
                # No brand data on the item -> unknown brand for product.
                product.brand_name = ""

        product.name = f"{product.brand_name} {product.variant_name}".strip()
        product.original_brand_name = product.brand_name
        product.original_variant_name = product.variant_name

    def get_measurements(self, item):
        """
        Extract item measurements as parallel lists of units and values.

        The `Item.measurements` is expected to be a list of [value, unit] pairs.

        Args:
            item (Item): Source of measurement data.

        Returns:
            tuple[list[str], list[float]]: (item_units, item_values)
                item_units  -> e.g., ["ml", "g"]
                item_values -> e.g., [250.0, 30.0]
        """
        if isinstance(item.measurements, list):
            item_values = [
                float(m[0]) for m in item.measurements
                if isinstance(m, list) and m is not None and len(m) > 0
            ] if item.measurements else []
            item_units = [
                m[1] for m in item.measurements
                if isinstance(m, list) and m is not None and len(m) > 1
            ] if item.measurements else []
        else:
            item_units = []
            item_values = []
        return item_units, item_values

    def adjust_quantities(self, product):
        """
        Detect multiplicative quantity expressions and renormalize price/score.

        Looks for patterns like:
          * "6 pack", "pack of 4"
          * "4 x 50ml", "4 * 50ml", including optional trailing equations
            such as "= 200ml".

        Behavior:
          * Remove these expressions from the variant name for display.
          * Infer a `divisor` (number of units) and scale:
              - listing_price /= divisor ** 0.96
              - accuracy_score *= (1 - (0.03 * divisor ** 0.6))

        Note: Exponents are heuristic dampeners to avoid overly aggressive scaling.
        """
        product_token_set = TokenSet(good=product)
        divisor = self.clean_pack(product, product_token_set)
        divisor = max(divisor, self.clean_x(product, product_token_set))
        product.variant_name = product.variant_name.strip()

        if divisor > 1:
            if product.postage_price > 0:
                product.listing_price = round((product.listing_price - product.postage_price)  / (divisor ** 0.96), 2)
            else:
                product.listing_price = round((product.listing_price - 2.7)  / (divisor ** 0.96), 2)
            product.buy_price = round(product.listing_price - product.postage_price, 2)
            product.accuracy_score = round(
                product.accuracy_score * (1 - (.03 * (divisor ** 0.6))), 2
            )

    def adjust_measurements(self, product, item_units, item_values):
        """
        Convert units in the product name to the item's units and then reconcile values.

        First pass (`convert_product_units`):
          - For each "<number><unit>" in the variant name, convert the unit to the
            corresponding unit from `item_units` (by position), removing the token if
            the item has no corresponding unit.

        Second pass (`convert_values`):
          - If the converted unit matches the item's unit, reconcile the numeric value
            with the item value and scale price/accuracy based on the ratio.
        """
        product_token_set = TokenSet(good=product)
        self.convert_product_units(product, product_token_set, item_units)
        self.convert_values(product, product_token_set, item_units, item_values)

    def clean_pack(self, product, product_token_set):
        """
        Remove 'pack' patterns and return inferred count.

        Handles:
          - "<N> pack x <M><unit>"  -> drops the 'pack' word (keeps the size part).
          - "<N> pack"              -> removes the whole token pair; divisor=N.
          - "pack of <N>"           -> removes the phrase; divisor=N.

        Args:
            product (Product)
            product_token_set (TokenSet)

        Returns:
            int: divisor inferred from the 'pack' pattern (>=1).
        """
        divisor = 1
        for i, token_raw in enumerate(product_token_set.variant_name_normalized):
            if token_raw.strip().lower().isdigit():
                before2_raw = product_token_set.variant_name_raw[i - 2] if i - 2 >= 0 else None
                before2_normalized = product_token_set.variant_name_normalized[i - 2].strip().lower() if i - 2 >= 0 else None
                before_normalized = product_token_set.variant_name_normalized[i - 1].strip().lower() if i - 1 >= 0 else None
                token_raw = product_token_set.variant_name_raw[i]
                after_raw = product_token_set.variant_name_raw[i + 1] if i + 1 < len(product_token_set.variant_name_raw) else None
                after_normalized = product_token_set.variant_name_normalized[i + 1] if i + 1 < len(product_token_set.variant_name_normalized) else None
                after2_raw = product_token_set.variant_name_raw[i + 2] if i + 2 < len(product_token_set.variant_name_raw) else None
                after2_normalized = product_token_set.variant_name_normalized[i + 2] if i + 2 < len(product_token_set.variant_name_normalized) else None

                # e.g., "6 pack x 500ml" -> drop the word "pack".
                if after_raw and after_normalized == 'pack' and after2_raw and after2_normalized == 'x':
                    product.variant_name = re.sub(
                        re.escape(f"{after_raw}"), " ", product.variant_name, count=1, flags=re.IGNORECASE
                    )
                # e.g., "6 pack" -> remove "6 pack" and set divisor=6.
                elif after_raw and after_normalized == 'pack':
                    product.variant_name = re.sub(
                        re.escape(f"{token_raw}{after_raw}"), " ", product.variant_name, count=1, flags=re.IGNORECASE
                    )
                    divisor = int(token_raw)

                # e.g., "pack of 4" -> remove phrase and set divisor=4.
                if before2_normalized and before2_normalized == 'pack' and before_normalized == 'of':
                    product.variant_name = re.sub(
                        re.escape(f"{before2_raw}{before_normalized}{token_raw}"), " ", product.variant_name, count=1, flags=re.IGNORECASE
                    )
                    divisor = int(token_raw)

        product.variant_name = product.variant_name.strip()
        return divisor

    def clean_x(self, product, product_token_set):
        """
        Remove 'x' multiplicative patterns and return inferred count.

        Handles variations such as:
          - "4 x 50ml"
          - "4 x 50 = 200ml"
          - "4 x 50ml = 200ml" (and similar with '*')
          - Lone "x 4"

        Inference:
          - The *first* numeric token adjacent to 'x'/'*' is taken as the divisor
            (to avoid confusing quantity with size).

        Returns:
            int: divisor inferred from the 'x' pattern (>=1).

        Caution:
          The condition `if before_normalized and before_normalized.lower() == 'x' or before_normalized == '*'`
          relies on Python's operator precedence; parentheses would make intent clearer.
        """
        changed = False  # True once the divisor has been set from an 'x' expression.
        divisor = 1
        for i, token_normalized in enumerate(product_token_set.variant_name_normalized):
            if token_normalized.isdigit():
                token_raw = product_token_set.variant_name_raw[i]
                before_raw = product_token_set.variant_name_raw[i - 1] if i - 1 >= 0 else None
                before_normalized = product_token_set.variant_name_normalized[i - 1].strip().lower() if i - 1 >= 0 else None
                after_raw = product_token_set.variant_name_raw[i + 1] if i + 1 < len(product_token_set.variant_name_raw) else None
                after_normalized = product_token_set.variant_name_normalized[i + 1].strip().lower() if i + 1 < len(product_token_set.variant_name_normalized) else None
                after2_raw = product_token_set.variant_name_raw[i + 2] if i + 2 < len(product_token_set.variant_name_raw) else None
                after2_normalized = product_token_set.variant_name_normalized[i + 2].strip().lower() if i + 2 < len(product_token_set.variant_name_normalized) else None
                after3_raw = product_token_set.variant_name_raw[i + 3] if i + 3 < len(product_token_set.variant_name_raw) else None
                after3_normalized = product_token_set.variant_name_normalized[i + 3].strip().lower() if i + 3 < len(product_token_set.variant_name_normalized) else None
                after4_raw = product_token_set.variant_name_raw[i + 4] if i + 4 < len(product_token_set.variant_name_raw) else None
                after4_normalized = product_token_set.variant_name_normalized[i + 4].strip().lower() if i + 4 < len(product_token_set.variant_name_normalized) else None
                after5_raw = product_token_set.variant_name_raw[i + 5] if i + 5 < len(product_token_set.variant_name_raw) else None
                after5_normalized = product_token_set.variant_name_normalized[i + 5].strip().lower() if i + 5 < len(product_token_set.variant_name_normalized) else None
                after6_raw = product_token_set.variant_name_raw[i + 6] if i + 6 < len(product_token_set.variant_name_raw) else None
                after6_normalized = product_token_set.variant_name_normalized[i + 6].strip().lower() if i + 6 < len(product_token_set.variant_name_normalized) else None

                # e.g., "4 x 50ml" or "4 * 50ml"
                if after_normalized and (after_normalized == 'x' or after_normalized == '*'):
                    # e.g., "4 x 50ml = 200ml" (possibly with leftover units trailing)
                    if after3_normalized and after4_normalized and after4_normalized == '=' and after3_normalized in self.unit_convertor.get_units():
                        if after5_normalized and after6_normalized and after6_normalized in self.unit_convertor.get_units():
                            product.variant_name = re.sub(
                                re.escape(f"{token_raw}{after_raw}{after2_raw}{after3_raw}{after4_raw}{after5_raw}{after6_raw}"),
                                f" {after2_raw}{after3_raw} ",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                        else:
                            product.variant_name = re.sub(
                                re.escape(f"{token_raw}{after_raw}{after2_raw}{after3_raw}{after4_raw}{after5_raw}"),
                                f" {after2_raw}{after3_raw} ",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                    # e.g., "4 x 50 = 200ml" or "4 x 50 = 200"
                    if after3_normalized and after3_normalized == '=':
                        if after5_normalized and after5_normalized in self.unit_convertor.get_units():
                            product.variant_name = re.sub(
                                re.escape(f"{token_raw}{after_raw}{after2_raw}{after3_raw}{after4_raw}{after5_raw}"),
                                f" {after2_raw} ",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                        else:
                            product.variant_name = re.sub(
                                re.escape(f"{token_raw}{after_raw}{after2_raw}{after3_raw}{after4_raw}"),
                                f" {after2_raw}",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                    # e.g., "4 x 50ml" or "4 x 50"
                    elif after2_normalized and after2_normalized.isdigit():
                        if after3_normalized and after3_normalized in self.unit_convertor.get_units():
                            pattern = re.escape(f"{token_raw}{after_raw}{after2_raw}{after3_raw}")
                            product.variant_name = re.sub(
                                pattern,
                                " ",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                        else:
                            product.variant_name = re.sub(
                                re.escape(f"{token_raw}{after_raw}{after2_raw}"),
                                " ",
                                product.variant_name, count=1, flags=re.IGNORECASE
                            )
                    # e.g., dangling "4 x"
                    else:
                        product.variant_name = re.sub(
                            re.escape(f"{token_raw}{after_raw}"),
                            " ",
                            product.variant_name, count=1, flags=re.IGNORECASE
                        )

                    # Only set divisor once; avoids misreading size as quantity.
                    if not changed:
                        changed = True
                        divisor = int(token_normalized)

                # e.g., leading "x 4" or "* 4"
                if before_normalized and before_normalized.lower() == 'x' or before_normalized == '*':
                    product.variant_name = re.sub(
                        re.escape(f"{before_raw}{token_raw}"),
                        " ",
                        product.variant_name, count=1, flags=re.IGNORECASE
                    )
                    if not changed:
                        changed = True
                        divisor = int(token_normalized)

        product.variant_name = product.variant_name.strip()
        return divisor

    def convert_product_units(self, product, product_token_set, item_units):
        """
        Convert each numeric+unit token in the variant name to the item's unit list (by position).

        Logic:
          - Walk normalized tokens; when a number is followed by a recognized unit:
              * If there is a corresponding `item_units[units_index]`, convert the value
                to that unit and replace in the name.
              * Otherwise, remove the numeric+unit pair (no corresponding unit on the item).

        Args:
            product (Product)
            product_token_set (TokenSet)
            item_units (list[str]): Target units; consumed in order of appearance.
        """
        units_index = 0
        for i, token_normalized in enumerate(product_token_set.variant_name_normalized):
            if token_normalized.strip().isdigit():
                token_raw = product_token_set.variant_name_raw[i]
                after_raw = product_token_set.variant_name_raw[i + 1] if i + 1 < len(product_token_set.variant_name_raw) else None
                after_normalized = product_token_set.variant_name_normalized[i + 1] if i + 1 < len(product_token_set.variant_name_normalized) else None
                if after_normalized in self.unit_convertor.get_units():
                    if units_index >= len(item_units):
                        # No corresponding unit on the item; drop the pair from the display name.
                        product.variant_name = re.sub(
                            re.escape(f"{token_raw}{after_raw}"), " ", product.variant_name, flags=re.IGNORECASE
                        )
                        continue
                    else:
                        # Replace with the value converted to the item's unit at this index.
                        value = round(
                            self.unit_convertor.convert(float(token_raw.strip()), after_normalized, item_units[units_index]),
                            2
                        )
                        product.variant_name = re.sub(
                            re.escape(f"{token_raw}{after_raw}"),
                            f"{value}{item_units[units_index]}",
                            product.variant_name, flags=re.IGNORECASE
                        )
                        units_index += 1

        product.variant_name = product.variant_name.strip()

    def convert_values(self, product, product_token_set, item_units, item_values):
        """
        Reconcile numeric values (now in the same units) with the item's canonical values.

        For the first occurrence where product unit matches `item_units[0]`:
          - Replace the displayed numeric value with `item_values[0]`.
          - Compute divisor = product_value / item_value and scale:
              * If divisor != 1: listing_price /= divisor ** 0.59
              * If divisor > 1: degrade accuracy_score proportionally
              * If divisor is very large (>=30): accuracy_score -> 0
          - Pop the matched unit/value so subsequent occurrences consider the next pair.

        Args:
            product (Product)
            product_token_set (TokenSet)
            item_units (list[str])
            item_values (list[float])
        """
        for i, token_normalized in enumerate(product_token_set.variant_name_normalized):
            if token_normalized.isdigit():
                token_raw = product_token_set.variant_name_raw[i].strip().lower()
                after_raw = product_token_set.variant_name_raw[i + 1].strip().lower() if i + 1 < len(product_token_set.variant_name_raw) else None
                if len(item_units) > 0:
                    if after_raw and after_raw in item_units:
                        item_value = item_values[0]
                        divisor = float(token_raw) / item_value

                        # Normalize display value to the canonical item value.
                        product.variant_name = re.sub(
                            re.escape(f'{token_raw}{after_raw}'),
                            f'{str(item_value)}{after_raw}',
                            product.variant_name, flags=re.IGNORECASE
                        )

                        # Price scaling heuristic; smaller packs often less cost-efficient,
                        # exponent dampens the adjustment.
                        if divisor != 1:
                            product.listing_price = round(
                                product.listing_price / ((divisor ** .59)),
                                2
                            )

                        # Convert ratios < 1 into > 1 for symmetric accuracy handling.
                        if divisor < 1:
                            divisor = 1 / divisor

                        # Degrade accuracy as the mismatch grows; clamp extreme cases.
                        if divisor > 1:
                            if divisor >= 30:
                                product.accuracy_score = 0
                            else:
                                product.accuracy_score = round(
                                    product.accuracy_score * (1 - (.13 * (divisor ** 0.6))),
                                    2
                                )

                        # Consume the matched unit/value pair.
                        item_units.pop(0)
                        item_values.pop(0)


if __name__ == "__main__":
    # Minimal example to illustrate usage.
    item = Item(
        "John Frieda Volume Lift Conditioner 250.0ml",
        brand_name="John Frieda",
        variant_name="Volume Lift Conditioner 250.0ml",
        quantity=1,
        original_name="John Frieda Volume Lift Conditioner 250.0ml",
        measurements=[[250.0, "ml"]],
    )
    product = Product(
        "John frieda Maybelline Dream Urban Cover Foundation - SPF50 - 30g - Choose Your Shade",
        "1",
        listing_price=13.5,
    )

    cleaner = ProductCleaner()
    cleaner.clean(product, item)

    print(f"Cleaned product name: {product.name}")
    print(f"Adjusted product buy price: {product.listing_price}")
    print(f"Adjusted product accuracy score: {product.accuracy_score}")
