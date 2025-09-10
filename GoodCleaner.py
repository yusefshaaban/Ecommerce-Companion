"""
Module: good_cleaner
--------------------

Utilities for standardising e-commerce product titles by stripping marketing
boilerplate, normalising numbers/units, and producing a cleaned display name.

Primary entry point
-------------------
- GoodCleaner.clean(good): Mutates a Product-like object in place.

Expected `good` / Product interface
-----------------------------------
The cleaner reads and/or writes the following attributes on the `good` object:

- brand_name (str): Brand portion of the title (input).
- variant_name (str): Variant/description portion of the title (input).
- original_name (str): Populated as "<brand_name> <variant_name>" before cleaning (output).
- original_brand_name (str): Set to the (current) brand_name after cleaning (output).
- original_variant_name (str): Set to the cleaned variant_name after cleaning (output).
- name (str): Final cleaned full name "<brand_name> <cleaned variant_name>" (output).

Note: `original_variant_name` is set *after* cleaning by design in this code,
so it contains the cleaned variant (not the raw input). Adjust if your
downstream logic expects otherwise.

Dependencies
------------
- Product: your domain model (only attribute access is used).
- UnitConvertor: must expose `get_units() -> Iterable[str]`, returning unit tokens
  such as ["ml", "g", "kg", "oz", ...]. These will be joined to adjacent numbers
  (e.g., "50 ml" -> "50ml") and lower-cased.

Caveats
-------
- `removal_terms` is a broad, case-insensitive alternation without word boundaries.
  It can remove substrings inside larger words (e.g., "new" inside "Newcastle").
  Add boundaries (e.g., `r'\\bnew\\b'`) if you need stricter matching.
- The numeric normalisation formats each detected number to two decimals,
  then removes trailing ".0" sequences. Examples:
    "10"      -> "10"
    "10.5"    -> "10.50"
    "10.00"   -> "10"
- Special characters are aggressively filtered: only letters, digits, space,
  ".", "=", "-", "&" are preserved before later passes.
"""

import re
from Product import Product
from UnitConvertor import UnitConvertor


class GoodCleaner:
    """
    Clean and normalise product titles.

    Responsibilities
    ----------------
    - Remove marketing and listing terms (e.g., "new", "free shipping").
    - Normalise punctuation and whitespace.
    - Format numbers consistently and join them with units.
    - Replace "&" with "and".
    - Build a canonical `good.name` from brand and cleaned variant.

    Usage
    -----
    >>> cleaner = GoodCleaner()
    >>> product = Product(
    ...     "50 x 50 x 300 x 20 x 1 x2 The Body Shop Strawberry Body Butter - 6 x 50ml x20 = 300.4ml - BUY 2, GET 1 FREE",
    ...     "!",
    ...     25
    ... )
    >>> cleaner.clean(product)
    >>> print(product.name)
    # "<brand> <cleaned variant>"  # actual value depends on UnitConvertor units and regex effects
    """
    def __init__(self):
        # Case-insensitive alternation of terms/phrases to be removed from titles.
        # Note: Some entries are duplicated (e.g., "worldwide", "clearance", "packaging").
        # Duplicates are harmless for regex but can be pruned if desired.
        # Also note the lack of word boundaries—terms may match inside larger words.
        self.removal_terms = '|'.join([
            r'new', r'brand', r'sealed', r'clearance', r'unused', r'by',
            r'free\s+postage', r'free\s+delivery', r'new\s*&\s*unused',
            r'new/unused', r'updated', r'discontinued', r'discounted',
            r'delivery', r'free\s+shipping', r'worldwide', r'free\s+shipping\s+to',
            r'uk', r'worldwide', r'global', r'international', r'local',
            r'original', r'authentic', r'genuine', r'official', r'limited\s+edition',
            r'collectible', r'vintage', r'rare', r'one\s+of\s+a\s+kind', r'seller',
            r'unique', r'lot', r'job\s+lot', r'bulk', r'wholesale', r'clearance',
            r'job\s+lot\s+of', r'job\s+lots', r'job\s+lot\s+of\s+goods', r'job\s+lot\s+of\s+products',
            r'job\s+lot\s+of\s+products\s+and\s+goods', r'for\s+sale', r'for\s+auction',
            r'for\s+bid', r'for\s+purchase', r'for\s+buy', r'for\s+buying', r'for\s+selling',
            r'for\s+resale', r'for\s+wholesale', r'for\s+retail', r'for\s+distribution', r'for\s+collection',
            r'for\s+delivery', r'for\s+shipping', r'free\s+post', r'free\s+ship', r'free\s+shipp',
            r'vegan', r'cruelty free', r'eco friendly', r'euro', r'packaging', r'biodegradable', r'packaging',
            r'plastic free', r'recyclable', r'sustainable', r'organic', r'natural', r'new\s+with\s+tags',
            r'new\s+with\s+box', r'new\s+in\s+box', r'new\s+in\s+packaging', r'new\s+in\s+package',
            r'new\s+in\s+original\s+packaging', r'new\s+in\s+original\s+package', r'new\s+with\s+original\s+packaging', r'new\s+with\s+original\s+package',
            r'new\s+in\s+sealed\s+packaging', r'new\s+in\s+sealed\s+package', r'new\s+with\s+sealed\s+packaging', r'new\s+with\s+sealed\s+package',
            r'new\s+in\s+plastic\s+packaging', r'new\s+in\s+plastic\s+package', r'new\s+with\s+plastic\s+packaging', r'new\s+with\s+plastic\s+package',
            r'new\s+in\s+cellophane', r'new\s+with\s+cellophane', r'new\s+in\s+wrap', r'new\s+with\s+wrap',
            r'new\s+in\s+wrapper', r'new\s+with\s+wrapper', r'new\s+in\s+sealed\s+wrap', r'new\s+with\s+sealed\s+wrap',
            r'never\s+used', r'never\s+opened', r'never\s+been\s+used', r'never\s+been\s+opened', r'never\s+been\s+used\s+or\s+opened'
        ])
        # Used to obtain unit tokens (e.g., "ml", "g"); see `clean_basic` for usage.
        self.unit_convertor = UnitConvertor()

    def clean(self, good):
        """
        Public entry point. Performs in-place cleaning of the provided `good`.

        Parameters
        ----------
        good : Product-like
            Object with `brand_name` and `variant_name` attributes (minimally),
            which will be read and then overwritten as documented in the module docstring.

        Side Effects
        ------------
        - Sets `good.original_name` to the pre-clean "<brand> <variant>".
        - Normalises `good.variant_name`.
        - Sets `good.original_brand_name` and `good.original_variant_name`
          (note: the latter is the *cleaned* variant in this implementation).
        - Sets `good.name` to "<brand> <cleaned variant>".
        """
        self.clean_basic(good)

    def clean_basic(self, good):
        """
        Core cleaning pipeline. Steps (in order):

        1) Seed `original_name` from brand + variant.
        2) Normalise separators: replace hyphens/underscores with spaces.
        3) Strip most special characters, keeping only letters, digits, whitespace,
           and the symbols `. = - &`.
        4) Remove specified marketing/listing terms (case-insensitive).
        5) Tidy periods:
           - Trim leading/trailing dots.
           - Replace dots not followed by a digit with a space (keeps decimals like "10.5").
        6) Number formatting:
           - Find all numeric substrings (`\\d+(?:\\.\\d+)?`).
           - For each unique occurrence (left-to-right), replace with a two-decimal form
             while ensuring we don't step into an existing decimal sequence.
           - Remove trailing ".0" sequences (e.g., "10.00" -> "10").
        7) Join units:
           - Using UnitConvertor.get_units(), collapse the space between a number
             and a following unit token, and lowercase the unit (e.g., "50 ML" -> "50ml").
        8) Remove "RRP <number>" occurrences.
        9) Replace "&" with "and".
        10) Collapse repeated whitespace and trim ends.
        11) Persist results back to the `good` object as described above.
        """

        # Begin cleaning on the variant text only.
        name = good.variant_name.strip()

        # Replace hyphens and underscores with spaces to standardise separators.
        name = re.sub(r'[-_]', ' ', name)

        # Remove broad set of marketing/listing terms and phrases.
        name = re.sub(self.removal_terms, '', name, flags=re.IGNORECASE)

        # Preserve the original concatenated name before any further cleaning.
        good.original_name = f"{good.brand_name} {good.variant_name}".strip()
        good.original_variant_name = good.variant_name.strip()  # note: this is pre-cleaned variant
        good.original_brand_name = good.brand_name.strip()  # note: this is pre-cleaned brand

        # Remove most special characters (keep letters, digits, dot, equals, hyphen, ampersand, spaces).
        name = re.sub(r'[^a-zA-Z0-9.=\-&\s]', ' ', name).strip()

        # Remove leading/trailing dots and replace non-decimal dots with spaces.
        name = re.sub(r'^\.+|\.+$', '', name)
        name = re.sub(r'\.(?!\d)', ' ', name)

        # Detect numbers (integers or decimals). We handle replacements one-by-one in order
        # to avoid reprocessing the same area multiple times.
        numbers = re.findall(r'\d+(?:\.\d+)?', name)

        # Format numbers to two decimals (e.g., "10" -> "10.00", "10.5" -> "10.50"),
        # then later strip redundant ".0" runs.
        for num in numbers:
            name = re.sub(
                r'(^|[^\.\d]){}([^\.\d]|$)'.format(num),
                r'\g<1>{:.2f}\g<2>'.format(float(num)),
                name,
                count=1
            )

        # Remove trailing ".0" sequences, e.g., "10.00" -> "10".
        name = re.sub(r'\.0{1,}', '', name)

        units = list(self.unit_convertor.get_units())
        units_pattern = "|".join(re.escape(u) for u in units)

        # Use lookarounds instead of \b so symbols still work.
        # Requires whitespace before the unit; doesn’t consume preceding number.
        pattern = rf"\s+(?=({units_pattern})(?!\w))"

        unit_re = re.compile(pattern, flags=re.IGNORECASE)

        # Replace the whitespace + unit with the lowercased unit + a space
        name = unit_re.sub(lambda m: m.group(1).lower() + " ", name)

        # Remove "RRP 12.99" style price hints.
        name = re.sub(r'rrp\s*(\d+(?:\.\d+)?)', ' ', name, flags=re.IGNORECASE)

        # Standardise "&" to the word "and" for consistency/searchability.
        name = re.sub('&', ' and ', name, flags=re.IGNORECASE)

        # Collapse extra whitespace and trim.
        name = re.sub(r'\s+', ' ', name).strip()

        # Remove broad set of marketing/listing terms and phrases.
        name = re.sub(self.removal_terms, '', name, flags=re.IGNORECASE)

        # Persist cleaned fields back to the product-like object.
        good.variant_name = name
        good.name = f"{good.brand_name} {good.variant_name}".strip()


if __name__ == "__main__":
    # Example usage (requires a compatible Product implementation).
    cleaner = GoodCleaner()
    product = Product(
        "50 x 50 x 300 x 20 x 1 x2 The Body Shop Strawberry Body Butter - 6 x 50ml x20 = 300.4ml - BUY 2, GET 1 FREE",
        "!",
        25
    )
    cleaner.clean(product)
    print(product.name)  # Prints the cleaned product name
