"""
Word filtering utilities for product/item normalization.

This module defines `WordFilterer`, which filters and rebuilds the
`variant_name` fields of `Item` and `Product` instances. It retains:
    - function words "for" and "with" (always kept),
    - explicit measurement units (from `UnitConvertor.get_units()`),
    - tokens containing digits (e.g., capacities like "64GB"),
    - tokens whose part-of-speech (POS) is in a caller-provided allowlist
      (`filters`) as determined by spaCy.

External dependencies / expected interfaces
-------------------------------------------
- spaCy model `en_core_web_sm` is loaded at import time as `nlp`.
- `TokenSet(good=...)` must expose:
    * variant_name_raw: List[str]
        Raw tokens as they appear in the source string (may include casing).
    * variant_name_normalized: List[str]
        Normalized/lowercased counterparts aligned by index to raw tokens.
- `UnitConvertor` must implement:
    * get_units() -> Iterable[str]
        Returns a collection of unit strings to be whitelisted.
- `Item` / `Product` must expose:
    * variant_name: str (read/write)
      The string to tokenize (input) and to overwrite (output).
    * For `filter_product`, the provided `item.variant_name` is used to
      whitelist any tokens that already appear in the item’s name.

Behavioral notes
----------------
- The filters applied keep tokens; non-matching tokens are dropped.
- The rebuilt `variant_name` is produced via `"".join(updated_tokens)`.
  If `variant_name_raw` does not include whitespace tokens, the result will
  be a concatenated string without spaces; this mirrors the original logic.
- Per-token POS is computed by running `nlp()` on the token string and taking
  the first token in the returned Doc.

Caveats
-------
- Repeatedly calling `nlp()` on single tokens can be relatively expensive; this
  module preserves that behavior to avoid changing runtime semantics.
- The demo under `if __name__ == "__main__":` calls `filter_product` without the
  required `filters` argument; it will raise a `TypeError` if executed as-is.
  This is left unchanged intentionally per the “no code changes” requirement.
"""

import spacy
import re
from Product import Product
from Item import Item
from TokenSet import TokenSet
from UnitConvertor import UnitConvertor
import spacy
import en_core_web_sm
nlp = en_core_web_sm.load()

class WordFilterer:
    """
    Filters and rebuilds `variant_name` fields for `Item` and `Product` objects
    using unit/number whitelists and spaCy POS-based allowlists.
    """

    def __init__(self):
        """
        Initialize helpers.

        Attributes
        ----------
        unit_convertor : UnitConvertor
            Provides known measurement units to always retain.
        """
        self.unit_convertor = UnitConvertor()

    def filter_item(self, item, filters):
        """
        Filter `item.variant_name` tokens and rewrite `item.variant_name`.

        The method keeps a token if ANY of the following are true:
          1) token_lower is "for" or "with"
          2) token_lower is in `self.unit_convertor.get_units()`
          3) token contains one or more digits (e.g., "64GB", "12")
          4) spaCy POS tag of the token is in `filters` (e.g., {"NOUN", "PROPN", "ADJ"})

        Parameters
        ----------
        item : Item
            An object with a `variant_name` attribute to be tokenized and rewritten.
        filters : Iterable[str]
            POS tags to allow (spaCy `Token.pos_` values), e.g. {"NOUN", "PROPN"}.

        Side Effects
        ------------
        - Overwrites `item.variant_name` with the concatenation of retained tokens
          from `TokenSet(good=item).variant_name_raw`.

        Notes
        -----
        - Tokenization source is `TokenSet`, which must provide aligned raw/normalized
          token lists. Raw tokens are written back verbatim (case/punctuation preserved).
        """
        item_token_set = TokenSet(good=item)
        updated_tokens = []
        for i in range(len(item_token_set.variant_name_raw)):
            token = item_token_set.variant_name_raw[i]
            token_lower = item_token_set.variant_name_normalized[i]
            numbers_in_token = re.findall(r'\d+', token_lower) if token_lower else []
            if token_lower in ["for", "with"] or (token_lower in self.unit_convertor.get_units()) or len(numbers_in_token) > 0:
                updated_tokens.append(token)
                continue
            token_lower_nlp = (nlp(token_lower))
            token_lower_nlp = token_lower_nlp[0] if token_lower_nlp else None
            if (token_lower_nlp and token_lower_nlp.pos_ in filters):
                updated_tokens.append(token)

        item.variant_name = "".join(updated_tokens)

    def filter_product(self, item, product, filters):
        """
        Filter `product.variant_name` tokens and rewrite `product.variant_name`.

        In addition to the rules in `filter_item`, this method also retains any
        token that already appears within `item.variant_name.lower()`. This helps
        ensure the product’s variant string preserves terms present in the item.

        Parameters
        ----------
        item : Item
            Used for cross-checking tokens: if a token from the product name
            appears in `item.variant_name.lower()`, it is retained.
        product : Product
            Target object whose `variant_name` will be filtered and rewritten.
        filters : Iterable[str]
            POS tags to allow (spaCy `Token.pos_` values).

        Side Effects
        ------------
        - Overwrites `product.variant_name` with the concatenation of retained
          raw tokens.

        Notes
        -----
        - Tokens with digits and recognized units are always kept.
        - POS filtering applies only after the whitelist checks.
        """
        product_token_set = TokenSet(good=product)
        updated_tokens = []
        for i in range(len(product_token_set.variant_name_raw)):
            token = product_token_set.variant_name_raw[i]
            token_lower = product_token_set.variant_name_normalized[i]
            numbers_in_token = re.findall(r'\d+', token_lower) if token_lower else []
            if token_lower in ["for", "with"] or (token_lower in item.variant_name.lower()) or (token_lower in self.unit_convertor.get_units()) or len(numbers_in_token) > 0:
                updated_tokens.append(token)
                continue
            token_lower_nlp = (nlp(token_lower))
            token_lower_nlp = token_lower_nlp[0] if token_lower_nlp else None
            if (token_lower_nlp and token_lower_nlp.pos_ in filters):
                updated_tokens.append(token)
        product.variant_name = "".join(updated_tokens)
    
    def is_key_word(self, word):
        """
        Heuristic to determine whether a word is a "key" term.

        Parameters
        ----------
        word : str | None
            A single token string.

        Returns
        -------
        bool
            True if the token’s spaCy POS tag is 'NOUN'; False otherwise.
            Returns False for falsy inputs.
        """
        if not word:
            return False
        token = nlp(word)[0]
        if token.pos_ in ['NOUN']:
            return True
        return False

if __name__ == "__main__":
    # Example usage (left unchanged):
    # NOTE: As written, `filter_product` requires a `filters` argument and will
    # raise a TypeError if run directly. This is intentional to avoid altering code.
    word_filterer = WordFilterer()

    item = Item("IPhone 12", brand_name="", variant_name="IPhone 12", quantity=1)
    product = Product("Apple iPhone 12 64GB 128GB All Colours Unlocked Smartphone A", web_url="", brand_name="", variant_name="Apple iPhone 12 64GB 128GB All Colours Unlocked Smartphone A")
    # Process the text
    word_filterer.filter_product(item, product)

    print(product.variant_name)
