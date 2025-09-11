import copy
from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class Item:
    name: str
    brand_name: str
    variant_name: str
    quantity: int
    name_certainty: float = 1.0
    original_name: str = "name"
    original_brand_name: str = "brand"
    original_variant_name: str = "variant"
    type: str = "beauty"
    measurements: List[Any] = field(default_factory=list)
    accuracy_score: float = 100.0
    products: List[Any] = field(default_factory=list)
    total_price: float = 0.0
    sell_price: float = 0.0
    sell_cost: float = 0.0
    buyer_protection_fee: float = 0.0
    postage_price: float = 0.0
    price_quality: float = 0.0
    num_products: int = 0


    def copy(self):
        return copy.deepcopy(self)


    def add_product(self, product):
        self.products.append(product)


    def __str__(self):
        accuracy = int(self.accuracy_score) if self.accuracy_score.is_integer() else self.accuracy_score
        certainty = int(self.name_certainty) if self.name_certainty.is_integer() else self.name_certainty
        quantity = int(self.quantity) if self.quantity.is_integer() else self.quantity

        item_str = (
            f"Item Name = {self.original_name}, "
            f"Quantity = {quantity}, "
            f"Total Price = £{self.total_price:.2f}, "
            f"Sell Price = £{self.sell_price:.2f}, "
            f"Buyer Protection Fee = £{self.buyer_protection_fee:.2f}, "
            f"Postage Price = £{self.postage_price:.2f}, "
            f"Accuracy Score = {accuracy}, "
            f"Name Certainty = {100 * certainty}%"
        )
        accuracy = float(accuracy)
        certainty = float(certainty)

        return item_str