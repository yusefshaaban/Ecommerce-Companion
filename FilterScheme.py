from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class FilterScheme:
    word_type: Tuple[str, ...]
    weight: float