import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EnumItem:
    text: str
    value: int