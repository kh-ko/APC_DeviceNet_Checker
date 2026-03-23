from dataclasses import dataclass, field
from typing import List, Optional

from model.enum_item import EnumItem


@dataclass
class PollOutItem:
    # UI에서 활용할 데이터
    enabled: bool = True
    size: int = 0 # uint8 = 1, int8 = 1, uint16 = 2, int16 = 2, uint32 = 4, int32 = 4, float = 4
    offset: int = 0
    written_data: str = ""
    write_ready_data: str = ""
    is_json_parsing_err: bool = False
    is_data_err: bool = False

    # JSON에서 읽어올 데이터
    name: str = ""
    type: str = "" # uint8, int8, uint16, int16, uint32, int32, float   
    ui_type: str = "" # number, real, enum
    enum_list: Optional[List[EnumItem]] = None