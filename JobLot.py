from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class JobLot:
    type: str
    id: int
    name: str
    web_url: str
    description: str = None
    condition: str = "New"
    items: List[Any] = field(default_factory=list)
    buy_price: float = 0
    buy_postage_price: float = 0
    buy_other_fees: float = 0
    buy_listing_price: float = 0
    sell_price: float = 0
    postage_price: float = 0
    other_fees: float = 0
    sell_listing_price: float = 0
    profit: float = 0
    accuracy_score: float = 0
    rating: float = 0
    

    def get_item_info(self):
        for item in self.get_items():
            print(item)

    def __str__(self):
        accuracy = int(self.accuracy_score) if self.accuracy_score.is_integer() else self.accuracy_score
        rating = int(self.rating) if self.rating.is_integer() else self.rating

        item_str = (
            f"Lot Name = {self.name}, "
            f"Rating = {rating}, "
            f"Profit = £{self.profit:.2f}, "
            f"Accuracy Score = {accuracy}, "
            f"Buy Listing Price = £{self.buy_listing_price:.2f}, "
            f"Sell Price = £{self.sell_price:.2f}, "
            f"Web URL = {self.web_url}"
        )

        accuracy = float(accuracy)
        rating = float(rating)

        return item_str