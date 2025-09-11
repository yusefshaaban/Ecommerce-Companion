"""
Pricing & scoring heuristics for candidate products.

This module estimates sell price, postage, and accuracy-derived scores for an
`Item` based on a working set of matched `Product` instances. All functions
**mutate their inputs in place** (notably `item` and possibly `product`s).

Key concepts
------------
- "Working set": a list of `Product` objects considered similar enough to the
  `Item` to be informative (accuracy thresholding happens upstream).
- "Closest price": not a distance metric; we pick a **cheap quantile** from the
  sorted buy prices, controlled by `CHEAPNESS_AGGRESSION`.
- Standardization penalty: large spreads in accuracy scores reduce confidence.

Version notes
-------------
- Uses Python 3.10+ structural pattern matching in `calculate_postage_price`.
"""

# Standard library / third-party imports
import numpy as np
from Product import Product  # Expects fields: total_price, postage_price, buy_price, accuracy_score, etc.

# --- Tunable heuristics / business rules ---
CHEAPNESS_AGGRESSION = 4           # Lower => choose a cheaper quantile when picking "closest" price (index len//N of sorted list).
PRODUCTS_BELOW_MULTIPLIER = 0.8    # Keep products with accuracy > score * PRODUCTS_BELOW_MULTIPLIER.
WORKING_ACC_MINIMUM_LENGTH = 8     # Minimum size of the working set before trusting computed price/score.
STANDARDIZE_STRENGTH = 50          # 0–99. Higher values -> WEAKER spread penalty (exponent = 1 - strength/100).


def calculate_price_and_score90(item, accuracy90):
    """
    Seed an item's sell price, accuracy, postage, and product count from ~90%-accuracy matches.

    WARNING: This function sorts and therefore mutates the `accuracy90` list in place.

    Args:
        item: The Item to be updated (fields mutated: sell_price, accuracy_score, postage_price, num_products).
        accuracy90 (list[Product]): Products assumed to be ~90% accurate matches, ideally pre-sorted by quality.

    Side Effects:
        - Mutates `item`.
        - Sorts `accuracy90` ascending by `accuracy_score`.

    Notes:
        - Uses the first element's listing price as the "closest" price **before** sorting.
        - The spread multiplier below **increases** the score when the spread is large:
          (max/min) ** 0.5 > 1 if max > min. If you intended to *downweight* large spreads,
          invert the ratio (min/max) instead.
    """
    # Initial (naive) average of accuracy scores across the provided products.
    accuracy_score = sum(p.accuracy_score for p in accuracy90) / len(accuracy90)

    # Heuristic anchor: treat the first product as "closest" and use its listing price.
    # (Assumes incoming `accuracy90` is pre-sorted by descending similarity/quality.)
    closest_price = accuracy90[0].total_price

    # Collect positive postage prices and average them.
    postage_prices = [p.postage_price for p in accuracy90 if p.postage_price > 0]
    estimated_postage_price = sum(postage_prices) / len(postage_prices) if postage_prices else 0

    # Recompute average accuracy after sorting ascending (for later min/max operations).
    accuracy90.sort(key=lambda p: p.accuracy_score)
    accuracy_score = sum(p.accuracy_score for p in accuracy90) / len(accuracy90) if accuracy90 else 0

    # Spread-based *boost* (see note above).
    accuracy_score *= (
        (max(p.accuracy_score for p in accuracy90) / max(1, min(p.accuracy_score for p in accuracy90))) ** 0.5
        if accuracy90 else 1
    )

    # Persist initial estimates on the item (rounded to 2 decimals).
    item.sell_price = round(closest_price, 2)
    item.accuracy_score = round(accuracy_score, 2)
    item.postage_price = round(estimated_postage_price, 2)
    item.num_products = len(accuracy90)


def calculate_price_and_score(item, accuracy_above, working_accuracy, score):
    """
    Build/augment a working set and, if enough data, compute item's price, accuracy, and postage.

    Strategy:
        - If there are products with accuracy above `score` (or `score` is small),
          create a synthetic "temp" product that anchors prices between a median-ish
          of the "below" group and the above-group mean (incl. postage).
        - Duplicate `accuracy_above` into the working set to increase its influence.
        - If the working set is large enough, compute final attributes; otherwise, zero them.

    Args:
        item: Item to mutate (sell_price, accuracy_score, postage_price, num_products).
        accuracy_above (list[Product]): Products with accuracy > `score` (context-dependent).
        working_accuracy (list[Product]): The working set to be extended/consumed (mutated).
        score (float): Current reference accuracy (0–100).

    Side Effects:
        - Mutates `item`, `working_accuracy`.
        - Creates a temporary `Product` instance appended to `working_accuracy`.
    """
    item.num_products = len(working_accuracy)

    # If we have above-threshold items OR a very low score, anchor and amplify the working set.
    if accuracy_above or score <= 30:
        # Select products from the item's full list that clear the (multiplied) accuracy threshold.
        products_below = list(
            sorted(
                (p for p in item.products if p.accuracy_score > score * PRODUCTS_BELOW_MULTIPLIER),
                key=lambda p: p.total_price,
            )
        )

        # Extract prices/postage from those filtered products.
        products_below_prices = [p.total_price for p in products_below]
        postage_below_prices = [p.postage_price for p in products_below]

        # If `score` is nonzero but no qualifying "below" products exist, return early.
        if not products_below_prices and score != 0:
            return

        # Pseudo-median: for len > 1, this picks the left-middle element ((n//2)-1), not a true median.
        products_below_prices_median = (
            products_below_prices[(len(products_below_prices) // 2) - 1]
            if len(products_below_prices) > 1 else (products_below_prices[0] if products_below_prices else 0)
        )
        products_below_postage_prices_median = (
            postage_below_prices[(len(postage_below_prices) // 2) - 1]
            if len(postage_below_prices) > 1 else (postage_below_prices[0] if postage_below_prices else 0)
        )

        # Anchor a synthetic product price halfway toward the above-mean (incl. postage),
        # falling back to the below-group medians when `accuracy_above` is empty.
        if len(accuracy_above) > 0:
            price_above_mean = round(float(np.mean([p.total_price + p.postage_price for p in accuracy_above])), 2)
            temp_product_total_price = round(
                products_below_prices_median + abs((products_below_prices_median - price_above_mean) / 2), 2
            )
            temp_product_postage_price = 0
        else:
            temp_product_total_price = products_below_prices_median
            temp_product_postage_price = products_below_postage_prices_median

        # Add a synthetic product to bias the working set toward a sensible midpoint.
        temp_product = Product(
            "temp", "web_url",
            total_price=temp_product_total_price,
            accuracy_score=score,
            postage_price=temp_product_postage_price,
        )

        # Heuristic weighting: double-count the above-threshold set, plus the anchor.
        working_accuracy.extend(accuracy_above)
        working_accuracy.extend(accuracy_above)
        working_accuracy.append(temp_product)

    # Compute final attributes only when we have enough datapoints (or score==0).
    if len(working_accuracy) >= WORKING_ACC_MINIMUM_LENGTH or score == 0:
        set_item_attributes(item, working_accuracy)
    else:
        # Not enough data—zero everything and return.
        item.sell_price = 0
        item.accuracy_score = 0
        item.postage_price = 0
        item.num_products = 0


def set_item_attributes(item, working_accuracy):
    """
    From a working set of products, derive:
      - a "closest" (cheap-quantile) buy_price as the sell price,
      - an adjusted accuracy score (with spread penalty applied via `adjust_accuracy_for_diffs`),
      - and a representative postage estimate.

    Args:
        item: Item to mutate.
        working_accuracy (list[Product]): Products used for aggregation (mutated: postage/buy_price set if missing).
    """
    closest_price, accuracy_score, avg_postage_price = 0, 0, 0

    # Sort by listing price to enable cheap-quantile selection and postage quantile.
    working_accuracy.sort(key=lambda p: p.total_price)

    # Representative (low-ish) postage as a quantile index into sorted positives.
    # With CHEAPNESS_AGGRESSION=4, this approximates the ~25th percentile.
    postage_prices = [p for p in (prod.postage_price for prod in working_accuracy) if p > 0]
    avg_postage_price = postage_prices[(len(postage_prices) // CHEAPNESS_AGGRESSION)] if postage_prices else 0

    # Impute zero/missing postage with `avg_postage_price` and compute buy_price = listing - postage.
    for product in working_accuracy:
        if product.postage_price == 0:
            product.postage_price = avg_postage_price

        product.buy_price = round(product.total_price - product.postage_price, 2)
        product.total_price = round(product.buy_price + product.postage_price, 2)

    # Keep item.products in sync for downstream consumers.
    for product in item.products:
        if product.postage_price == 0:
            product.postage_price = avg_postage_price

        product.buy_price = round(product.total_price - product.postage_price, 2)
        product.total_price = round(product.buy_price + product.postage_price, 2)

    # Pick a "closest" price as a cheap quantile of buy prices (aggressive undercutting).
    closest_price = working_accuracy[(len(working_accuracy) // CHEAPNESS_AGGRESSION)].buy_price if working_accuracy else 0

    # Baseline average of accuracy scores across the working set.
    accuracy_score = (
        sum(p.accuracy_score for p in working_accuracy) / len(working_accuracy) if working_accuracy else 0
    )

    # Penalize for large spreads between min and max accuracies.
    adjust_accuracy_for_diffs(item, working_accuracy, accuracy_score)

    item.sell_price = round(closest_price, 2)
    item.accuracy_score = round(item.accuracy_score, 2)  # adjusted inside `adjust_accuracy_for_diffs`
    item.postage_price = round(avg_postage_price, 2)


def adjust_accuracy_for_diffs(item, working_accuracy, accuracy_score):
    """
    Downweight the accuracy score when the spread between min and max accuracy is large.

    Mechanism:
        ratio = min/max (i.e., in (0, 1]). The final multiplier is:
            ratio ** (1 - STANDARDIZE_STRENGTH/100)

        Because 1 - STANDARDIZE_STRENGTH/100 shrinks as STANDARDIZE_STRENGTH grows,
        **higher STANDARDIZE_STRENGTH produces a weaker penalty**.

    Args:
        item: Item whose `accuracy_score` is set here.
        working_accuracy (list[Product]): Source of min/max accuracy.
        accuracy_score (float): Baseline average accuracy prior to spread adjustment.
    """
    max_accuracy = max((p.accuracy_score for p in working_accuracy), default=1)
    min_accuracy = min((p.accuracy_score for p in working_accuracy), default=1)

    # Avoid division by zero in pathological cases.
    if min_accuracy == 0:
        min_accuracy = 1
    if max_accuracy == 0:
        max_accuracy = 1

    # Spread ratio expressed as (min/max) in (0, 1], where 1 -> no spread.
    accuracy_dif = min_accuracy / max_accuracy if working_accuracy else 1

    # Apply square-root-like damping controlled by STANDARDIZE_STRENGTH.
    item.accuracy_score = accuracy_score * (accuracy_dif ** (1 - (STANDARDIZE_STRENGTH / 100)))


def calculate_buyer_protection_fee(item):
    """
    Apply a buyer-protection fee schedule to `item.sell_price`.

    The computed fee is stored in `item.buyer_protection_fee` and then subtracted
    from `item.sell_price` (netting out the fee).

    Tiers:
        <= £20      : £0.10 + 7%
        <= £300     : £1.50 + 4% of amount over £20
        <= £4000    : £12.70 + 2% of amount over £300
        >  £4000    : £86.70 flat
    """
    flat_fee = 0.1
    if item.sell_price <= 20:
        item.buyer_protection_fee = round(flat_fee + 0.07 * item.sell_price, 2)
    elif item.sell_price <= 300:
        item.buyer_protection_fee = round(1.5 + (0.04 * (item.sell_price - 20)), 2)
    elif item.sell_price <= 4000:
        item.buyer_protection_fee = round(12.7 + (0.02 * (item.sell_price - 300)), 2)
    else:
        item.buyer_protection_fee = 86.7

    # Net the fee out of the sell price.
    item.sell_price = round(item.sell_price - item.buyer_protection_fee, 2)


def calculate_postage_price(item):
    """
    If `item.postage_price` is unset/zero, estimate it from the first measurement tuple
    `(value, unit)` using a simple tiered table.

    Requires Python 3.10+ due to `match`/`case`.

    Args:
        item: Item to mutate (reads `measurements`, sets `postage_price`).
    """
    if item.postage_price > 0:
        return
    else:
        if len(item.measurements) > 0:
            match item.measurements[0][1]:
                case 'ml':
                    item.postage_price = 1.55 if item.measurements[0][0] <= 50 else 2.7
                case 'l':
                    item.postage_price = 1.55 if item.measurements[0][0] <= 0.05 else 2.7
                case 'g':
                    if item.measurements[0][0] <= 100:
                        item.postage_price = 1.55
                    elif item.measurements[0][0] <= 200:
                        item.postage_price = 2.7
                    else:
                        item.postage_price = 3.29
                case 'kg':
                    if item.measurements[0][0] <= 0.1:
                        item.postage_price = 1.55
                    elif item.measurements[0][0] <= 0.2:
                        item.postage_price = 2.7
                    else:
                        item.postage_price = 3.29
                case _:
                    # Default fallback when unit is unrecognized.
                    item.postage_price = 1.55
        else:
            # No measurements provided—use a general fallback.
            item.postage_price = 1.7


def set_scores(item):
    """
    Finalize the item's scoring metrics.

    Steps:
        1) Nonlinear compression of accuracy into a 0–100 band (sqrt curve).
        2) Small-sample penalties (n=1..3).
        3) Apply a name-certainty penalty to accuracy.
        4) Compute `price_quality`: higher when accuracy is high and price is low.

    Args:
        item: Item to mutate (reads accuracy_score, num_products, name_certainty, total_price).
    """
    # (1) Nonlinear compression: keep ordering but reduce extremes.
    item.accuracy_score = 100 * ((item.accuracy_score / 100) ** 0.5)

    # (2) Penalize low sample sizes (1..3) since accuracy is less reliable.
    if item.num_products == 1:
        item.accuracy_score *= 0.7
    elif item.num_products == 2:
        item.accuracy_score *= 0.85
    elif item.num_products == 3:
        item.accuracy_score *= 0.95

    # Round for presentation/storage consistency.
    item.accuracy_score = round(item.accuracy_score, 2)

    # (3) Reduce effective accuracy when name certainty is low.
    certainty_penalty = item.accuracy_score - item.accuracy_score ** (float(item.name_certainty) ** 0.5)

    # (4) A normalized "value" metric: higher accuracy and lower price => higher score.
    item.price_quality = (
        ((item.accuracy_score - certainty_penalty) / item.total_price) ** 1.1 if item.total_price > 0 else 0
    )
