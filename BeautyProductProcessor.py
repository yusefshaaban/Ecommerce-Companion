from ProductProcessor import ProductProcessor

"""
Beauty domain product processor.

This module defines `BeautyProductProcessor`, a thin specialization of the
generic `ProductProcessor` that configures domain-specific scoring weights
used when comparing items to candidate products (e.g., from marketplaces).
The constants below represent relative scores assigned to different kinds
of string matches between an item’s normalized name and a product’s name.

Scoring constants overview
--------------------------
Higher values indicate stronger evidence of a correct match. These weights
are consumed by the base `ProductProcessor` (e.g., during ranking/aggregation).

Exactness-based weights
- EXACT_MATCH_SCORE:
    Perfect, case-sensitive full-string match.
- EXACT_CASE_INSENSITIVE_MATCH_SCORE:
    Perfect match ignoring case only.
- EXACT_INCLUSIVE_MATCH_SCORE:
    Item string appears exactly (case-sensitive) as a substring of the product.
- EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE:
    Item appears as a substring of the product, case-insensitive.
- EXACT_NO_SPACES_MATCH_SCORE:
    Exact match after removing spaces (case-sensitive).
- EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE:
    Substring match ignoring case and spaces.

Closeness-based weights (fuzzy/partial similarity tiers)
- EXACT_CLOSENESS_MATCH_SCORE:
    Very strong similarity (near-exact).
- P85_CLOSENESS_MATCH_SCORE:
    ~85% similarity tier.
- P70_CLOSENESS_MATCH_SCORE:
    ~70% similarity tier.
- P50_CLOSENESS_MATCH_SCORE:
    ~50% similarity tier.
- P33_CLOSENESS_MATCH_SCORE:
    ~33% similarity tier.

Notes
-----
- The specific algorithms (tokenization, normalization, distance metric) are
  defined by `ProductProcessor`; this class only sets the weights.
- Adjust these constants to tune precision/recall for beauty products.
"""

class BeautyProductProcessor(ProductProcessor):
    """
    Beauty-focused specialization of `ProductProcessor` that supplies
    match-scoring weights appropriate for cosmetics/beauty titles.
    """

    # --- Exactness-based weights ---
    EXACT_MATCH_SCORE = 1
    EXACT_CASE_INSENSITIVE_MATCH_SCORE = 0.98
    EXACT_INCLUSIVE_MATCH_SCORE = 0.85
    EXACT_INCLUSIVE_CASE_INSENSITIVE_MATCH_SCORE = 0.83
    EXACT_NO_SPACES_MATCH_SCORE = 0.97
    EXACT_INCLUSIVE_CASE_INSENSITIVE_NO_SPACES_MATCH_SCORE = 0.81

    # --- Closeness (fuzzy) similarity tiers ---
    EXACT_CLOSENESS_MATCH_SCORE = 0.6
    P85_CLOSENESS_MATCH_SCORE = 0.35
    P70_CLOSENESS_MATCH_SCORE = 0.2
    P50_CLOSENESS_MATCH_SCORE = 0.11
    P33_CLOSENESS_MATCH_SCORE = 0.06

    def __init__(self):
        """
        Initialize the base `ProductProcessor` with beauty-specific weights.
        """
        super().__init__()
