from dataclasses import dataclass
from typing import Iterable, Tuple
from decimal import Decimal, InvalidOperation
import re

@dataclass
class TokenSet:
    good: str
    variant_name_raw: str = ""
    variant_name_normalized: str = ""
    brand_name_raw: str = ""
    brand_name_normalized: str = ""
    original_variant_name_raw: str = ""
    original_variant_name_normalized: str = ""
    original_brand_name_raw: str = ""
    original_brand_name_normalized: str = ""


    def __init__(self, good: str):
        self.good = good
        self.tokenize()


    def tokenize(self):
        self.variant_name_raw, self.variant_name_normalized = self.tokenize_variant_name(self.good)
        self.brand_name_raw, self.brand_name_normalized = self.tokenize_brand_name(self.good)
        self.original_variant_name_raw, self.original_variant_name_normalized = self.tokenize_original_variant_name(self.good)
        self.original_brand_name_raw, self.original_brand_name_normalized = self.tokenize_original_brand_name(self.good)


    def tokenize_variant_name(self, good):
        """
        Tokenize `good.variant_name` into (1) raw tokens and (2) normalized tokens.

        Token rules:
            - Numbers (including decimals) are extracted as separate tokens.
            - Alphabetic sequences (including '*') are extracted as word tokens.
            - Punctuation and miscellaneous symbols are preserved as their own tokens.

        Normalization for the second list:
            - Lowercase.
            - Strip spaces and zeros/periods from tokens (useful for matching patterns
            like "1.0" vs "10" and minor formatting differences).

        Args:
            product: An object with `.variant_name` (string).

        Returns:
            tuple[list[str], list[str]]: (raw_tokens, normalized_tokens_without_decimals)
        """
        pattern = r'\d+(?:\.\d+)?\s*|[^\W\d_]+\s*|[^\w\s]\s*'
        tokens_raw = re.findall(pattern, good.variant_name)
        tokens_normalized = []
        for token in tokens_raw:
            try:
                # Try converting to Decimal to remove trailing zeros safely
                normalized = str(float(token)).rstrip("0").rstrip(".")
            except ValueError:
                # If conversion fails, it's not a number; normalize as a word or symbol
                normalized = token.strip().lower()
            tokens_normalized.append(normalized)
            
        return tokens_raw, tokens_normalized

    def tokenize_brand_name(self, good):
        """
        Tokenize `good.brand_name` into (1) raw tokens and (2) normalized tokens.

        Token rules:
            - Numbers (including decimals) are extracted as separate tokens.
            - Alphabetic sequences (including '*') are extracted as word tokens.
            - Punctuation and miscellaneous symbols are preserved as their own tokens.

        Normalization for the second list:
            - Lowercase.
            - Strip spaces and zeros/periods from tokens (useful for matching patterns
            like "1.0" vs "10" and minor formatting differences).

        Args:
            product: An object with `.brand_name` (string).

        Returns:
            tuple[list[str], list[str]]: (raw_tokens, normalized_tokens_without_decimals)
        """
        pattern = r'\d+(?:\.\d+)?\s*|[^\W\d_]+\s*|[^\w\s]\s*'
        tokens_raw = re.findall(pattern, good.brand_name)
        tokens_normalized = []
        for token in tokens_raw:
            try:
                # Try converting to Decimal to remove trailing zeros safely
                normalized = str(float(token)).rstrip("0").rstrip(".")
            except ValueError:
                # If conversion fails, it's not a number; normalize as a word or symbol
                normalized = token.strip().lower()
            tokens_normalized.append(normalized)
            
        return tokens_raw, tokens_normalized
    
    def tokenize_original_variant_name(self, good):
        """
        Tokenize `good.original_variant_name` into (1) raw tokens and (2) normalized tokens.
        Token rules:
            - Numbers (including decimals) are extracted as separate tokens.
            - Alphabetic sequences (including '*') are extracted as word tokens.
            - Punctuation and miscellaneous symbols are preserved as their own tokens.
        Normalization for the second list:
            - Lowercase.
            - Strip spaces and zeros/periods from tokens (useful for matching patterns
            like "1.0" vs "10" and minor formatting differences).
        Args:
            product: An object with `.original_variant_name` (string).
        Returns:
            tuple[list[str], list[str]]: (raw_tokens, normalized_tokens_without_decimals)
        """
        pattern = r'\d+(?:\.\d+)?\s*|[^\W\d_]+\s*|[^\w\s]\s*'
        tokens_raw = re.findall(pattern, good.original_variant_name)
        tokens_normalized = []
        for token in tokens_raw:
            try:
                # Try converting to Decimal to remove trailing zeros safely
                normalized = str(float(token)).rstrip("0").rstrip(".")
            except ValueError:
                # If conversion fails, it's not a number; normalize as a word or symbol
                normalized = token.strip().lower()
            tokens_normalized.append(normalized)
            
        return tokens_raw, tokens_normalized
    
    def tokenize_original_brand_name(self, good):
        """
        Tokenize `good.original_brand_name` into (1) raw tokens and (2) normalized tokens.
        Token rules:
            - Numbers (including decimals) are extracted as separate tokens.
            - Alphabetic sequences (including '*') are extracted as word tokens.
            - Punctuation and miscellaneous symbols are preserved as their own tokens.
        Normalization for the second list:
            - Lowercase.
            - Strip spaces and zeros/periods from tokens (useful for matching patterns
            like "1.0" vs "10" and minor formatting differences).
        Args:
            product: An object with `.original_brand_name` (string).
        Returns:
            tuple[list[str], list[str]]: (raw_tokens, normalized_tokens_without_decimals)
        """
        pattern = r'\d+(?:\.\d+)?\s*|[^\W\d_]+\s*|[^\w\s]\s*'
        tokens_raw = re.findall(pattern, good.original_brand_name)
        tokens_normalized = []
        for token in tokens_raw:
            try:
                # Try converting to Decimal to remove trailing zeros safely
                normalized = str(float(token)).rstrip("0").rstrip(".")
            except ValueError:
                # If conversion fails, it's not a number; normalize as a word or symbol
                normalized = token.strip().lower()
            tokens_normalized.append(normalized)
            
        return tokens_raw, tokens_normalized