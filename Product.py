import copy
from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class Product:
    name: str
    web_url: str
    listing_price: float = 0.0
    brand_name: str = "brand"
    variant_name: str = "variant"
    original_name: str = "name"
    original_brand_name: str = "brand"
    original_variant_name: str = "variant"
    type: str = "beauty"
    buy_quality_score: float = 0.0
    accuracy_score: float = 100
    quality_score: float = 0.0
    buy_price : float = 0.0
    postage_price: float = 0.0


    def copy(self):
        return copy.deepcopy(self)


    def __str__(self):
        accuracy = int(self.accuracy_score) if self.accuracy_score.is_integer() else self.accuracy_score

        item_str = (
            f"Buy Price = £{self.buy_price:.2f}, "
            f"Postage Price = £{self.postage_price:.2f}, "
            f"Accuracy Score = {accuracy}, "
            f"Web URL = {self.web_url}"
        )
        accuracy = float(accuracy)
        
        return item_str