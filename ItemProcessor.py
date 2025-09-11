"""
This module orchestrates the end-to-end flow of:
1) fetching candidate listings from eBay,
2) normalizing/cleaning the input item,
3) generating several filtered name variants to broaden/target search matching,
4) creating Product objects from raw eBay results,
5) scoring, aggregating, and estimating prices + postage,
6) computing final accuracy and listing estimates for the Item.
This module processes items by fetching product data from eBay, estimating prices, and calculating accuracy scores.
"""


import re
import ItemCalculator as calc
from ItemCleaner import ItemCleaner
from BeautyProductProcessor import BeautyProductProcessor
from EbayRequestHandler import EbayRequestHandler
from CurrencyConverter import CurrencyConverter
from UnitConvertor import UnitConvertor
from ItemNameExtractor import ItemNameExtractor
from ProductProcessor import ProductProcessor
from WordFilterer import WordFilterer
from Item import Item
from Product import Product
from FilterScheme import FilterScheme
from TokenSet import TokenSet

class ItemProcessor():

    FILTERSCHEMES = [
            FilterScheme(word_type=("NOUN", "PROPN", "ADJ", "ADV"), weight=1.0),
            FilterScheme(word_type=("NOUN", "PROPN", "ADJ"), weight=1.3),
            FilterScheme(word_type=("NOUN", "PROPN"), weight=1.7),
            FilterScheme(word_type=("NOUN",), weight=3.0),
        ]
    
    def __init__(
        self,
        ebay_request_handler=None,
        unit_converter=None,
        currency_converter=None,
        item_name_extractor=None,
        product_processor=None,
        cleaner=None,
        word_filterer=None,
    ):
        self.ebay_request_handler = ebay_request_handler or EbayRequestHandler()
        self.currency_converter = currency_converter or CurrencyConverter()
        self.item_name_extractor = item_name_extractor or ItemNameExtractor()
        self.product_processor = product_processor or ProductProcessor()
        self.cleaner = cleaner or ItemCleaner()
        self.word_filterer = word_filterer or WordFilterer()
        self.unit_converter = unit_converter or UnitConvertor()


    def process(self, item, params=None):
        """
        Entry point: processes a single item end-to-end.
        Side effects:
        - Mutates `item` by adding populated `products`, pricing fields, and accuracy score.
        - Prints progress info to stdout.
        """
        
        print(f"Processing item: {item.name}")

        # Fetch up to 10 candidate listings from eBay (using the original item name).
        response_data = self.ebay_request_handler.get_items(f"q={item.name}&limit=10", params=",".join(params.values()))
        found_products = response_data.get('itemSummaries', [])
        num_products_found = len(found_products)
        original_params = params.copy()

        penalty = 0

        if num_products_found < 3:
            params.pop("deliveryCountry")
            params.pop("itemLocationCountry")
            response_data = self.ebay_request_handler.get_items(f"q={item.name}&limit=10", params=",".join(params.values()))
            found_products2 = response_data.get('itemSummaries', [])
            for found_product in found_products2:
                found_product['acc_penalty'] = 0.1
                found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') == 0 if found_product.get('shippingOptions', {}) and found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') else None
            found_products.extend(found_products2)

            num_products_found = len(found_products)
            if num_products_found < 3:
                params['deliveryCountry'] = "deliveryCountry:GB"
                params['itemLocationCountry'] = "itemLocationCountry:GB"
                if original_params['conditions'] == "conditions:{NEW}":
                    params['conditions'] = "conditions:{USED}"
                    penalty = 0.1
                elif original_params['conditions'] == "conditions:{USED}":
                    params['conditions'] = "conditions:{NEW}"
                    penalty = 0.6
                response_data = self.ebay_request_handler.get_items(f"q={item.name}&limit=10", params=",".join(params.values()))
                found_products3 = response_data.get('itemSummaries', [])
                for found_product in found_products3:
                    found_product['acc_penalty'] = penalty
                    found_product['price_penalty'] = penalty
                found_products.extend(found_products3)
                num_products_found = len(found_products)
                if num_products_found < 3:
                    params.pop("deliveryCountry")
                    params.pop("itemLocationCountry")
                    if original_params['conditions'] == "conditions:{NEW}":
                        params['conditions'] = "conditions:{USED}"
                        penalty = 0.1
                    elif original_params['conditions'] == "conditions:{USED}":
                        params['conditions'] = "conditions:{NEW}"
                        penalty = 0.6
                    response_data = self.ebay_request_handler.get_items(f"q={item.name}&limit=10", params=",".join(params.values()))
                    found_products3 = response_data.get('itemSummaries', [])
                    for found_product in found_products3:
                        found_product['acc_penalty'] = penalty + 0.1
                        found_product['price_penalty'] = penalty
                    found_products.extend(found_products3)
                    num_products_found = len(found_products)
                

        # Normalize the item in-place (e.g., stripping noise, standardizing brand/variant).
        self.cleaner.clean(item)

        # Parse measurements (e.g., "60 ml") from the item name/variant and store on the item.
        self.set_measurements(item)

        # Build multiple filtered variants of the name to improve matching robustness later.
        filtered_items = self.filter_name(item)

        # Seed initial products for the original item based on the fetched listings.
        self.initialize_products(item, found_products)

        # For each filtered variant, also initialize products and compute item-level info.
        for filtered_item in filtered_items:
            self.initialize_products(filtered_item[0], found_products)
            self.set_item_info(filtered_item[0])

        # Combine (weighted) signals from the filtered variants back into the original item.
        self.set_average_item_info(item, filtered_items)

        # Compute additional scores at the very end (delegated to ItemCalculator).
        calc.set_scores(item)


    def filter_name(self, item):
        """
        Creates multiple "filtered" copies of the item by keeping subsets of word_type tags.
        Rationale: progressively stricter filters (NOUN+PROPN+ADJ+ADV → only NOUNs) can
        help find better matches when listings use different phrasing.
        """
        filtered_items = []

        for scheme in self.FILTERSCHEMES:
            filtered_item = item.copy()
            self.word_filterer.filter_item(filtered_item, scheme.word_type)
            filtered_items.append((filtered_item, scheme.weight))

        return filtered_items


    def set_average_item_info(self, item, filtered_items):
        """
        Aggregates accuracy scores from the filtered variants back into the main item
        using a weighted average (weights favor stricter filters).
        """
        for i in range(filtered_items[0][0].num_products):
            item.products[i].accuracy_score = round(sum(filtered_item.products[i].accuracy_score * weight for filtered_item, weight in filtered_items) / sum(weight for _, weight in filtered_items), 2)
        # Recompute item-level aggregates after assigning new per-product accuracy scores.
        self.set_item_info(item)


    def set_measurements(self, item):
        """
        Cleans the item name, extracts numeric measurements with units (e.g., "60 ml"),
        and stores them on item.measurements. It also removes duplicate unit tokens
        from variant_name if additional measurements are found later in the string.
        """

        measurements = []
        item_token_set = TokenSet(good=item)

        # Iterate through tokens to find number → unit pairs.
        for i, token_normalized in enumerate(item_token_set.variant_name_normalized):
            if token_normalized.strip().isdigit():
                token_raw = round(float(item_token_set.variant_name_raw[i].strip()), 2)
                after_raw = item_token_set.variant_name_raw[i + 1].strip().lower() if i + 1 < len(item_token_set.variant_name_raw) else None
                after_normalized = item_token_set.variant_name_normalized[i + 1].strip().lower() if i + 1 < len(item_token_set.variant_name_normalized) else None

                # Validate that the "after" token is a known unit.
                if after_normalized and after_normalized in self.unit_converter.get_units():
                    if not measurements:
                        # First occurrence becomes the canonical measurement on the item.
                        measurements.append([token_raw, after_raw])
                    else:
                        # If we already captured a measurement, strip duplicate tokens
                        # from the variant name to avoid confusion (best-effort).
                        item.variant_name = re.sub(
                            re.escape(f"{token_raw}{after_raw}"),
                            "",
                            item.variant_name,
                            count=1,
                            flags=re.IGNORECASE
                        )
        item.measurements = measurements


    def initialize_products(self, item, found_products):
        """
        For each raw found product dict from eBay, build a Product object and add it to the item.
        Finally, sort all products by accuracy_score descending so top matches come first.
        """
        for found_product in found_products:
            product = self.create_product(item, found_product)
            item.add_product(product)

        item.products = list(sorted(item.products, key=lambda x: x.accuracy_score, reverse=True))


    def create_product(self, item, found_product):
        """
        Maps eBay response fields into a Product, converts prices to a base currency,
        and runs downstream product-specific processing to compute accuracy and prices.
        """
        acc_penalty = found_product.get('acc_penalty', 0)
        price_penalty = found_product.get('price_penalty', 0)
        name = found_product.get('title')
        value = found_product.get('price', {}).get('value') * (1 - price_penalty) if found_product.get('price', {}).get('value') else None
        currency = found_product.get('price', {}).get('currency') if found_product.get('price', {}).get('currency') else None
        # Convert listing price into base currency if possible; fallback to 0.
        price = float(self.currency_converter.convert(value, currency) if value and currency else 0)
        web_url = found_product.get('itemWebUrl', '')

        # Safely extract first shipping option if present; otherwise None.
        postage_value = found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') if found_product.get('shippingOptions', {}) and found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('value') else None
        postage_currency = found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('currency') if found_product.get('shippingOptions', {}) and found_product.get('shippingOptions', {})[0].get('shippingCost', {}).get('currency') else None
        postage_price = self.currency_converter.convert(postage_value, postage_currency) if postage_value and postage_currency else 0
        postage_price = float(postage_price) if float(postage_price) else 0

        total_price = round(price + postage_price, 2)

        product = Product(
            name=name,
            brand_name="",
            web_url=web_url,
            total_price=round(total_price, 2),
            buy_price=round(price, 2),
            postage_price=postage_price,
            accuracy_score=(1 - acc_penalty) * 100,  # Initial accuracy before product-level processing.
        )

        # Compute product-level scores/fields (e.g., accuracy_score, buy_price).
        self.product_processor.process(item, product)
        return product


    def set_item_info(self, item):
        """
        Computes item-level price/score from the distribution of product matches.
        Strategy:
        - Build buckets of products with accuracy >= {90, 85, 80, ..., 0}.
        - If the 90+ bucket is sufficiently large (>=6), use it for initial estimates.
        - Otherwise, walk down through adjacent buckets and let ItemCalculator derive
        sell_price/accuracy based on available data.
        """
        if not item.products:
            item.accuracy_score = 0
            return
        
        closest_price, accuracy_score = 0, 0
        accuracy_nums = tuple(range(90, -5, -5))
        all_accuracies = [self.create_accuracy(score, item) for score in accuracy_nums]

        # If we have a healthy 90+ set, evaluate estimates there.
        if len(all_accuracies[0]) >= 6:
            calc.calculate_price_and_score90(item, all_accuracies[0])
        else:
            # Walk through adjacent accuracy bands and let the calculator refine estimates.
            for i in range(len(all_accuracies)-1):
                calc.calculate_price_and_score(item, all_accuracies[i], all_accuracies[i+1], 90 - (i * 5))
                if item.sell_price > 0:
                    # Recompute fees after we have a sell_price; postage may also be adjusted.
                    calc.calculate_buyer_protection_fee(item)
                    calc.calculate_postage_price(item)

                    # total_price = sell + postage + buyer protection (current values).
                    item.total_price = round(item.sell_price + item.postage_price + item.buyer_protection_fee, 2)
                    return


    def create_accuracy(self, score, item):
        """
        Returns products with accuracy >= `score`, sorted by total_price ascending.
        This helps downstream logic reason about "closest" price points for a given confidence level.
        """
        accuracy_sorted = list(sorted(
            filter(lambda p: p.accuracy_score >= score, item.products),
            key=lambda p: p.total_price
        ))

        return accuracy_sorted


if __name__ == "__main__":
    # Example usage: run this module directly to process a sample item
    # and print out the scored candidate products.
    item_processor = ItemProcessor()
    item = Item(name="The Body Shop British Rose Body Butter 50ml", brand_name="The Body Shop", variant_name="British Rose Body Butter 50ml", original_brand_name="The Body Shop", original_variant_name="British Rose Body Butter 50ml", quantity=1, measurements=[[50,'ml']])
    params = {
        "filter": f"filter=",
        "buyingOptions": f"buyingOptions:{{FIXED_PRICE}}",
        "conditions": f"conditions:{{NEW}}",
        "deliveryCountry": f"deliveryCountry:GB",
        "itemLocationCountry": f"itemLocationCountry:GB"
    }
    item_processor.process(item, params)
    n = 0
    for product in item.products:
        print(f"{n}. Product: {product.name}, Listing Price: {product.total_price}, Buy Price: {product.buy_price}, Postage Price: {product.postage_price}, Accuracy Score: {product.accuracy_score}, web_url: {product.web_url}\n")
        n += 1
    print(item)

    # To do: match conditions of job lot to product conditions and filter out products that 
    # do not match.

    # To do: for new items, if no products are found in uk, try global search and 
    # automatically set shipping costs. If still not found search for used products, uk 
    # first and then global.

    # To do: if there are slashes or | after the brand name or variant name, we need to 
    # handle that as it could mean this product is used for multiple items and is not 
    # the item itself. The handling should be very light and not too aggressive because 
    # this is not always the case e.g. iphone 16.