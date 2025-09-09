import re
from GoodCleaner import GoodCleaner

class ItemCleaner(GoodCleaner):
    """
    This class handles the removal of specific terms from product names.
    It uses a regex pattern to match and remove these terms.
    """
    def __init__(self):
        super().__init__()