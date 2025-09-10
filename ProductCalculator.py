"""
Utilities for scoring how closely a catalog `product` matches a searched `item`.

All functions operate by **multiplying** `product.accuracy_score` in place using a
set of heuristics that consider exact string matches, case-insensitive matches,
substring inclusion (with and without spaces), token overlap, numerical tokens,
and contextual cues in the original names (e.g., words like "for" or "with").

Inputs are expected to provide at least:
- `item.brand_name`, `item.variant_name`, `item.name`, `item.original_brand_name`,
  `item.original_variant_name`, and `item.copy()`.
- `product.brand_name`, `product.variant_name`, `product.name`, `product.original_brand_name`,
  `product.original_variant_name`, and `product.accuracy_score` (float).

No function here returns a final score; instead they **adjust** `product.accuracy_score`.
"""

import re
from WordFilterer import WordFilterer
from TokenSet import TokenSet

# ------------------------------
# Similarity multiplier constants
# ------------------------------
# The values below are multiplicative factors applied to `product.accuracy_score`
# when certain match conditions are met. Higher means stronger evidence of a match.
EXACT_MATCH_SCORE = 1
EXACT_CASE_INSENSITIVE_MATCH_SCORE = 0.98
EXACT_INCLUSIVE_MATCH_SCORE = 0.85
EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE = 0.83
EXACT_NO_SPACES_MATCH_SCORE = 0.97
EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE = 0.81
EXACT_CLOSENESS_MATCH_SCORE = 0.75
P90_CLOSENESS_MATCH_SCORE = 0.6
P80_CLOSENESS_MATCH_SCORE = 0.56
P70_CLOSENESS_MATCH_SCORE = 0.41
P60_CLOSENESS_MATCH_SCORE = 0.36
P50_CLOSENESS_MATCH_SCORE = 0.3
P40_CLOSENESS_MATCH_SCORE = 0.23
P30_CLOSENESS_MATCH_SCORE = 0.15

def set_accuracy(item, product):
    """
    Top-level orchestrator: adjust `product.accuracy_score` based on how `product`
    matches `item`. First tries exact/inclusive forms of matching; if none apply,
    falls back to a token-based "closeness" strategy.

    Side effects:
        Mutates `product.accuracy_score` in place.
    """
    is_match = calculate_accuracy_is_match(item, product)
    if not is_match:
        calculate_accuracy_no_match(item, product)

def calculate_accuracy_is_match(item, product):
    """
    Apply multiplicative score updates for exact and inclusion-style matches
    between `item.variant_name`/`item.name` and `product.variant_name`/`product.name`.

    The checks proceed roughly as:
        1) Exact match (case-sensitive) on variant.
        2) Exact match (case-insensitive) on variant.
        3) Inclusion (case-sensitive) of item's variant in product's variant.
        4) Inclusion (case-insensitive) of item's name in product's name.
        5) Repeat key checks after stripping spaces and lowercasing.

    Numerical tokens are considered stronger evidence, so matches that include digits
    typically apply a slightly higher multiplier than purely alphabetic matches.

    Returns:
        bool: True if any of the match-based adjustments were applied; otherwise False.

    Notes:
        - Temporary normalization (strip spaces + lowercase) is performed but original
          strings are restored before returning.
        - This function **only** adjusts `product.accuracy_score`; it does not finalize it.
    """
    changed = False
    if item.variant_name == product.variant_name:
        # Prefer exact matches that include digits (often model numbers).
        is_number = any(char.isdigit() for char in item.variant_name)
        if is_number:
            product.accuracy_score *= EXACT_MATCH_SCORE
        else:
            product.accuracy_score *= (EXACT_MATCH_SCORE - .05)
        changed = True
        return changed

    if item.variant_name.lower() == product.variant_name.lower():
        # Case-insensitive exact match on variant.
        is_number = any(char.isdigit() for char in item.variant_name)
        if is_number:
            product.accuracy_score *= EXACT_CASE_INSENSITIVE_MATCH_SCORE
        else:
            product.accuracy_score *= (EXACT_CASE_INSENSITIVE_MATCH_SCORE - .05)
        changed = True
        return changed

    if item.variant_name in product.variant_name:
        # Item variant appears within product variant (case-sensitive).
        adjust_accuracy_for_context(item, product, True)
        item_token_set = TokenSet(good=item)
        product_token_set = TokenSet(good=product)
        adjust_accuracy_for_end(item, product, item_token_set, product_token_set)


        is_number = any(char.isdigit() for char in item.variant_name)
        if is_number:
            product.accuracy_score *= EXACT_INCLUSIVE_MATCH_SCORE
        else:
            is_number = any(char.isdigit() for char in product.variant_name)
            if is_number:
                product.accuracy_score *= (EXACT_INCLUSIVE_MATCH_SCORE - .4)
            else:
                product.accuracy_score *= (EXACT_INCLUSIVE_MATCH_SCORE - .05)

        changed = True
        return changed

    if item.name.lower() in product.name.lower():
        # Item name appears within product name (case-insensitive).
        adjust_accuracy_for_context(item, product, True)
        item_token_set = TokenSet(good=item)
        product_token_set = TokenSet(good=product)
        adjust_accuracy_for_end(item, product, item_token_set, product_token_set)

        is_number = any(char.isdigit() for char in item.name)
        if is_number:
            product.accuracy_score *= EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE
        else:
            is_number = any(char.isdigit() for char in product.name)
            if is_number:
                product.accuracy_score *= (EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE - .4)
            else:
                product.accuracy_score *= (EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE - .05)

        changed = True
        return changed

    # --- Normalize by removing spaces and lowercasing, then re-check inclusive patterns. ---
    item_name_before = item.variant_name
    product_name_before = product.variant_name
    item.variant_name = re.sub(r'[\s]+', '', item.variant_name).lower()
    product.variant_name = re.sub(r'[\s]+', '', product.variant_name).lower()

    if item.variant_name == product.variant_name:
        adjust_accuracy_for_context(item, product, True)

        is_number = any(char.isdigit() for char in item.variant_name)
        if is_number:
            product.accuracy_score *= EXACT_NO_SPACES_MATCH_SCORE
        else:
            product.accuracy_score *= (EXACT_NO_SPACES_MATCH_SCORE - .05)
        changed = True
        # Restore originals before returning.
        item.variant_name = item_name_before
        product.variant_name = product_name_before
        return changed

    if item.variant_name in product.variant_name:
        adjust_accuracy_for_context(item, product, True)

        is_number = any(char.isdigit() for char in item.variant_name)
        if is_number:
            product.accuracy_score *= EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE
        else:
            is_number = any(char.isdigit() for char in product.variant_name)
            if is_number:
                product.accuracy_score *= (EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE - .4)
            else:
                product.accuracy_score *= (EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE - .05)
        # Restore originals before returning.
        item.variant_name = item_name_before
        product.variant_name = product_name_before
        changed = True
        return changed

    # No match detected; restore originals and report False.
    item.variant_name = item_name_before
    product.variant_name = product_name_before
    return changed

def calculate_accuracy_no_match( item, product):
    """
    If no direct/inclusive match was found, compute a token-overlap "closeness"
    measure and adjust `product.accuracy_score` accordingly.

    Strategy (high-level):
        - Tokenize both names into numbers (incl. decimals) and words.
        - Compute proportion of searched tokens that appear in the product.
        - Weight results based on how many numeric tokens are present/matched.

    Side effects:
        Mutates `product.accuracy_score` in place.

    Notes:
        - If `item.brand_name` is non-empty while `product.brand_name` is empty,
          the score is heavily penalized (multiplied by 0.1).
        - If zero tokens match, the score is set to 0 and we return early.
        - Variables `numbers_in_name` and `numbers_match` are scoped inside the
          token loop; as written, their final values reflect only the last
          searched token processed (not totals). This behavior is preserved
          intentionally here.
    """

    item_token_set = TokenSet(good=item)
    product_token_set = TokenSet(good=product)

    adjust_accuracy_for_context(item, product, False)
    adjust_accuracy_for_end(item, product, item_token_set, product_token_set)

    searched_words = item_token_set.variant_name_normalized
    product_name_words = product_token_set.variant_name_normalized

    num_parts_match = 0

    if item.brand_name != "" and product.brand_name == "":
        product.accuracy_score *= .1

    for searched_word in searched_words:
        numbers_in_name = 0
        numbers_match = 0
        is_number = any(char.isdigit() for char in searched_word)
        if is_number:
            numbers_in_name += 1
            if searched_word in product_name_words:
                numbers_match += 1
                num_parts_match += 1
        else:
            if searched_word in product_name_words:
                num_parts_match += 1

    # Compute basic closeness ratio (how much of the query appears in the product).
    if num_parts_match > 0:
        search_closeness = num_parts_match / (len(searched_words))
    else:
        product.accuracy_score = 0
        return

    filtered_product_token_set = [token for token in product_token_set.variant_name_normalized if not token.isdigit()]
    filtered_item_token_set = [token for token in item_token_set.variant_name_normalized if not token.isdigit()]

    if len(filtered_product_token_set) < len(filtered_item_token_set):
        if abs(len(filtered_product_token_set) - num_parts_match) == 1:
            product.accuracy_score *= .97
        elif abs(len(filtered_product_token_set) - num_parts_match) == 2:
            product.accuracy_score *= .92
        elif abs(len(filtered_product_token_set) - num_parts_match) == 3:
            product.accuracy_score *= .87
        else:
            product.accuracy_score *= .8
    else:
        if abs(len(filtered_product_token_set) - num_parts_match) == 1:
            product.accuracy_score *= .75
        elif abs(len(filtered_product_token_set) - num_parts_match) == 2:
            product.accuracy_score *= .7
        elif abs(len(filtered_product_token_set) - num_parts_match) == 3:
            product.accuracy_score *= .65
        else:
            product.accuracy_score *= .6

    # Graduated multipliers by closeness band, with nuanced nudges for numerics.
    if search_closeness == 1:
        if (len(searched_words) // 5) < numbers_in_name:
            product.accuracy_score *= EXACT_CLOSENESS_MATCH_SCORE
        elif (len(searched_words) // 2) < numbers_in_name:
            product.accuracy_score *= (EXACT_CLOSENESS_MATCH_SCORE + .05)
        elif (numbers_in_name > 0):
            product.accuracy_score *= (EXACT_CLOSENESS_MATCH_SCORE - .05)
        else:
            product.accuracy_score *= (EXACT_CLOSENESS_MATCH_SCORE - .25)
    elif search_closeness < .3:
        product.accuracy_score *= .01
    elif search_closeness < .4:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P30_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P30_CLOSENESS_MATCH_SCORE + .02)
            else:
                product.accuracy_score *= (P30_CLOSENESS_MATCH_SCORE - .01)
            if numbers_in_name == numbers_match:
                product.accuracy_score *= .2
        else:
            product.accuracy_score *= (P30_CLOSENESS_MATCH_SCORE - .02)
    elif search_closeness < .5:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P40_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P40_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P40_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= .2
        else:
            product.accuracy_score *= (P40_CLOSENESS_MATCH_SCORE - .05)
    elif search_closeness < .6:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P50_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P50_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P50_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= .2
        else:
            product.accuracy_score *= (P50_CLOSENESS_MATCH_SCORE - .05)
    elif search_closeness < .7:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P60_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P60_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P60_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= P60_CLOSENESS_MATCH_SCORE * .2
        else:
            product.accuracy_score *= (P60_CLOSENESS_MATCH_SCORE - .05)
    elif search_closeness < .8:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P70_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P70_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P70_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= P70_CLOSENESS_MATCH_SCORE * .2
        else:
            product.accuracy_score *= (P70_CLOSENESS_MATCH_SCORE - .05)
    elif search_closeness < .9:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P80_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P80_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P80_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= .2
        else:
            product.accuracy_score *= (P80_CLOSENESS_MATCH_SCORE - .2)
    else:
        if numbers_in_name:
            if (len(searched_words) // 5) < numbers_in_name:
                product.accuracy_score *= P90_CLOSENESS_MATCH_SCORE
            elif (len(searched_words) // 2) < numbers_in_name:
                product.accuracy_score *= (P90_CLOSENESS_MATCH_SCORE + .03)
            else:
                product.accuracy_score *= (P90_CLOSENESS_MATCH_SCORE - .02)
            if numbers_in_name != numbers_match:
                product.accuracy_score *= .2
        else:
            product.accuracy_score *= (P90_CLOSENESS_MATCH_SCORE - .2)


def adjust_accuracy_for_context(item, product, match):
    """
    Adjust the score based on contextual wording around the brand/variant names
    in the *original* product strings (e.g., penalize accessories "for" an item).

    Heuristics:
        - If the words immediately before the brand/variant include "with" or "for"
          and those words are not themselves part of the item's brand/variant, apply
          penalties (stronger penalty for "for").
        - If words immediately after the item name are "keywords" (per `WordFilterer`),
          apply additional penalties (weaker when the match is direct).

    Args:
        item: Object with brand/variant fields and their original values.
        product: Object with original brand/variant strings and an `accuracy_score` float.
        match (bool): True if we already have a direct/inclusive match and are refining
                      by context; False if we are in the looser "no-match" path.

    Notes:
        - The function loops over `part in ["brand", "variant"]` and inspects up to two
          words immediately **before** each occurrence of the item's original part within
          the product's original part.
        - After the loop, it inspects up to two words **after** the *variant* occurrence
          (because `item_name_original_part` / `product.original_variant_name` reflect the
          last loop iteration). This is intentional given the current structure.
        - Calls like `re.sub('with', ..., flags=re.IGNORECASE)` are not assigned; they do
          not mutate the strings (kept as-is to preserve behavior).
        - Multipliers are asymmetric: when `match` is False, penalties are slightly softer.
    """
    for part in ["brand", "variant"]:
        if part == "brand":
            item_name_original_part = item.original_brand_name
            product_name_original_part = product.original_brand_name
        if part == "variant":
            item_name_original_part = item.original_variant_name
            product_name_original_part = product.original_variant_name

        # Identify up to two words immediately BEFORE the item name in product text.
        if match:
            m = re.search(r'((?:\b\w+\s+){0,2})' + re.escape(item_name_original_part), product_name_original_part, re.IGNORECASE)
            words_before = re.findall(r'\w+', m.group(1)) if m else []
        else:
            # For the no-match path, approximate using the first normalized token.
            temp_item = item.copy()
            if part == "brand":
                temp_item.brand_name = item_name_original_part
            else:
                temp_item.variant_name = item_name_original_part

            temp_item_token_set = TokenSet(good=temp_item)
            words_before = re.findall(r'((?:\b\w+\s+){0,2})' + re.escape(temp_item_token_set.variant_name_normalized[0]), product_name_original_part, flags=re.IGNORECASE)

        if len(words_before) == 0 or words_before[0] == "" or words_before[0][0] == "":
            word_before = ""
            word_before2 = ""
        else:
            word_before = words_before[len(words_before) - 1].lower()
            word_before2 = words_before[len(words_before) - 2].lower() if len(words_before) > 1 else ""

        # Penalize contextual accessorial phrases like "with ..." or stronger "for ..."
        if word_before not in item.brand_name.lower() and word_before not in item.variant_name.lower() and word_before == "with":
            if match:
                product.accuracy_score *= .7
            else:
                product.accuracy_score *= .8
        if word_before2 not in item.brand_name.lower() and word_before2 not in item.variant_name.lower() and word_before2 == "with":
            if match:
                product.accuracy_score *= .85
            else:
                product.accuracy_score *= .95
        re.sub('with', '', product_name_original_part, flags=re.IGNORECASE)

        if word_before not in item.brand_name.lower() and word_before not in item.variant_name.lower() and word_before == "for":
            if match:
                product.accuracy_score *= .35
            else:
                product.accuracy_score *= .45
        if word_before2 not in item.brand_name.lower() and word_before2 not in item.variant_name.lower() and word_before2 == "for":
            if match:
                product.accuracy_score *= .5
            else:
                product.accuracy_score *= .6
            re.sub('for', '', product_name_original_part, flags=re.IGNORECASE)

        if "no" in product.original_variant_name.lower() and "no" not in item.original_variant_name.lower():
            product.accuracy_score *= .9
    # --- Inspect words AFTER the item name (variant-focused) and penalize certain keywords. ---
    if match:
        m = re.search(re.escape(item_name_original_part) + r'((?:\s+\w+){0,2})', product.original_variant_name, re.IGNORECASE)
        words_after = re.findall(r'\w+', m.group(1)) if m else []
    else:
        temp_item = item.copy()
        temp_item.variant_name = item_name_original_part

        temp_item_token_set = TokenSet(good=temp_item)
        m = re.search(re.escape(temp_item_token_set.variant_name_normalized[0]) + r'((?:\s+\w+){0,2})', product.original_variant_name, re.IGNORECASE)
        words_after = re.findall(r'\w+', m.group(1)) if m else []

    if len(words_after) == 0 or words_after[0] == "":
        word_after = ""
        word_after2 = ""
    else:
        word_after = words_after[0].lower()
        word_after2 = words_after[1].lower() if len(words_after) > 1 else ""
    word_filterer = WordFilterer()

    # Penalize if following words are "keywords" (e.g., accessory/category terms).
    if word_after not in item.brand_name.lower() and word_after not in item.variant_name.lower() and word_filterer.is_key_word(word_after):
        if match:
            product.accuracy_score *= .7
        else:
            product.accuracy_score *= .85

    if word_after2 not in item.brand_name.lower() and word_after2 not in item.variant_name.lower() and word_filterer.is_key_word(word_after2):
        if match:
            product.accuracy_score *= .85
        else:
            product.accuracy_score *= .97

    if "no" in product.original_variant_name.lower() and "no" not in item.original_variant_name.lower():
        product.accuracy_score *= .9

def adjust_accuracy_for_end(item, product, item_token_set, product_token_set):
    """
    Additional heuristic: if the product name doesn't end with the item variant name,
    apply a small boost to the accuracy score.

    Side effects:
        Mutates `product.accuracy_score` in place.
    """
    if product_token_set.original_variant_name_normalized[-1] == item_token_set.original_variant_name_normalized[-1]:
        product.accuracy_score *= .99
    else:
        word_filterer = WordFilterer()
        filter = word_filterer.get_tag(item_token_set.original_variant_name_normalized[-1])
        if word_filterer.is_key_word(product_token_set.original_variant_name_normalized[-1], [filter]):
            product.accuracy_score *= .95
        else:
            product.accuracy_score *= .85
        filter = word_filterer.get_tag(item_token_set.variant_name_normalized[-1])
        if word_filterer.is_key_word(product_token_set.variant_name_normalized[-1], [filter]):
            product.accuracy_score *= .95
        else:
            product.accuracy_score *= .85
    # print(f"Adjusted for product name: {product.original_variant_name}: {product.accuracy_score}")
