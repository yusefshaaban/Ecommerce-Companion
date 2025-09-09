"""
Lightweight unit conversion utilities.

This module defines `UnitConvertor`, which maps a small set of weight,
volume, length, and data units to a common base per category and performs
conversions by normalizing to that base, then scaling to the target unit.

Base units used per category
----------------------------
- Weight: grams (g)
- Volume: milliliters (ml)
- Length: millimeters (mm)
- Data: bytes (b)

Notes & caveats
---------------
- Conversions across *different* categories (e.g., 'kg' -> 'ml') are
  mathematically computed but semantically meaningless; this class does
  not enforce category checks.
- Unit keys are lowercase and, in one case, contain a space (e.g., "fl oz").
- Data units use binary multiples (1 kb = 1024 b).
"""

class UnitConvertor:
    """
    Provide unit factors and basic conversion using category-specific bases.
    """

    def get_units(self):
        """
        Return the unit-to-base multiplier mapping.

        Returns
        -------
        dict[str, float | int]
            Multipliers to convert a unit to its category base unit:
            - weight -> grams
            - volume -> milliliters
            - length -> millimeters
            - data   -> bytes
        """
        return {
            'kg': 1000,  # kilograms to grams
            'g': 1,      # grams to grams
            'lb': 453.592,  # pounds to grams
            'fl oz': 29.5735,  # fluid ounces to milliliters
            'oz': 28.3495,  # ounces to grams
            'l': 1000,   # liters to milliliters
            'ml': 1,     # milliliters to milliliters
            'm': 1000,   # meters to millimeters
            'cm': 10,    # centimeters to millimeters
            'mm': 1,      # millimeters to millimeters
            'b': 1,       # bytes to bytes
            'kb': 1024,   # kilobytes to bytes
            'gb': 1024**2, # gigabytes to bytes
            'tb': 1024**3  # terabytes to bytes
        }
    
    
    def convert(self, value, from_unit, to_unit):
        """
        Convert a numeric `value` from `from_unit` to `to_unit`.

        Parameters
        ----------
        value : float | int
            Quantity expressed in `from_unit`.
        from_unit : str
            Source unit key (lowercase, e.g., 'kg', 'ml', 'cm', 'kb', 'fl oz').
        to_unit : str
            Target unit key (same convention as above).

        Returns
        -------
        float
            Converted value in `to_unit`.

        Raises
        ------
        ValueError
            If either unit is not supported.

        Notes
        -----
        - The conversion proceeds by normalizing to the category base unit
          via the multiplier table, then dividing by the target multiplier.
        - No validation is performed to ensure `from_unit` and `to_unit`
          belong to the same physical category.
        """
        units = self.get_units()
        if from_unit in units and to_unit in units:
            multiplier = units[from_unit]
            # Convert to the category base unit (g, ml, mm, or b).
            standardized_value = multiplier * value
            # Scale from the base unit to the target unit.
            converted_value = standardized_value / units[to_unit]
            return converted_value
        else:
            raise ValueError(f"Conversion from {from_unit} to {to_unit} is not supported.")


if __name__ == "__main__":
    # Example usage / quick sanity checks
    unit_convertor = UnitConvertor()
    print(unit_convertor.convert(1, 'kg', 'g'))  # Example conversion
    print(unit_convertor.get_units())  # Display available units
