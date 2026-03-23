import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BitmapItem:
    name: str
    bits: List[str]