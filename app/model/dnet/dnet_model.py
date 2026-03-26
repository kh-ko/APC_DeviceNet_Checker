import json
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

class DataType(str, Enum):
    UINT8 = 'uint8' # ui type은 반드시 'number' 이어야 한다.
    INT8 = 'int8' # ui type은 반드시 'number' 이어야 한다.
    UINT16 = 'uint16' # ui type은 반드시 'number' 이어야 한다.
    INT16 = 'int16' # ui type은 반드시 'number' 이어야 한다.
    UINT32 = 'uint32' # ui type은 반드시 'number' 이어야 한다.
    INT32 = 'int32' # ui type은 반드시 'number' 이어야 한다.
    FLOAT = 'float' # ui type은 반드시 'real' 이어야 한다.
    BITMAP = 'bitmap' # ui type은 반드시 'table' 이어야 한다.
    NONE = 'none' # 기존 로직의 Exe 타입 처리를 위한 값
    EMPTY = ''    # 필드 누락 및 예외 처리를 위한 기본값

class DataType(str, Enum):
    UINT8 = 'uint8' # ui type은 반드시 'number' 이어야 한다.
    INT8 = 'int8' # ui type은 반드시 'number' 이어야 한다.
    UINT16 = 'uint16' # ui type은 반드시 'number' 이어야 한다.
    INT16 = 'int16' # ui type은 반드시 'number' 이어야 한다.
    UINT32 = 'uint32' # ui type은 반드시 'number' 이어야 한다.
    INT32 = 'int32' # ui type은 반드시 'number' 이어야 한다.
    FLOAT = 'float' # ui type은 반드시 'real' 이어야 한다.
    BITMAP = 'bitmap' # ui type은 반드시 'table' 이어야 한다.
    NONE = 'none' # 기존 로직의 Exe 타입 처리를 위한 값
    EMPTY = ''    # 필드 누락 및 예외 처리를 위한 기본값

class UiType(str, Enum):
    NUMBER = 'number'
    REAL = 'real'
    ENUM = 'enum'
    TABLE = 'table'
    NONE = 'none' # 기존 로직의 Exe 타입 처리를 위한 값
    EMPTY = ''    # 필드 누락 및 예외 처리를 위한 기본값

class AccessType(str, Enum):
    RO = 'RO'
    WO = 'WO'
    RW = 'RW'
    EXE = 'Exe'
    EMPTY = ''    # 필드 누락 및 예외 처리를 위한 기본값

class EnumItem(BaseModel):
    text: str = ""
    value: int = 0

class BitmapItem(BaseModel):
    name: str = ""
    # bits 는 8개의 비트를 의미한다.
    bits: List[str] = Field(default_factory=list)

class CyclicItem(BaseModel):
    """모든 DNet 아이템이 공유하는 공통 모델"""
    # JSON 매핑 필드 (기본값을 부여하여 누락 시에도 안전하게 처리)
    name: str = ""
    type: DataType = DataType.EMPTY
    ui_type: UiType = UiType.EMPTY
    enum_list: Optional[List[EnumItem]] = None
    bitmap: Optional[List[BitmapItem]] = None

    # JSON에 매핑되지는 않으면 파싱중 오류가 발생한 것을 표시할때 사용한다.
    is_json_parsing_err: bool = False

    @model_validator(mode='after')
    def validate_and_calculate_size(self) -> 'CyclicItem':
        self.is_json_parsing_err = False

        if not self.name.strip():
            self.is_json_parsing_err = True

        if self.type in (DataType.EMPTY, DataType.NONE):
            self.is_json_parsing_err = True

        if self.ui_type in (UiType.EMPTY, UiType.NONE):
            self.is_json_parsing_err = True

        if self.ui_type == UiType.ENUM and not self.enum_list:
            self.is_json_parsing_err = True

        if self.check_bitmap_error():
            self.is_json_parsing_err = True

        if self.check_type_mismatch():
            self.is_json_parsing_err = True

        return self

    # bitmap 타입인 경우 ui_type은 table 이어야 하고, bitmap 리스트의 아이템은 적어도 1개 이상이어야 하고, 각 아이템의 bits는 8개여야 한다.
    def check_bitmap_error(self) -> bool:
        if self.type != DataType.BITMAP:
            return False

        if self.ui_type != UiType.TABLE or not self.bitmap:
            return True
            
        for bit in self.bitmap:
            if not bit.bits or len(bit.bits) != 8:
                return True
        return False

    def check_type_mismatch(self) -> bool:
        # 비어있는 경우는 위에서 이미 에러 처리했으므로 여기선 패스
        if self.type in (DataType.EMPTY, DataType.NONE) or self.ui_type == UiType.EMPTY:
            return False
            
        int_types = (DataType.UINT8, DataType.INT8, DataType.UINT16, DataType.INT16, DataType.UINT32, DataType.INT32)
        
        if self.type in int_types:
            # 정수형은 number 혹은 enum이어야 함
            if self.ui_type not in (UiType.NUMBER, UiType.ENUM):
                return True
        elif self.type == DataType.FLOAT:
            if self.ui_type != UiType.REAL:
                return True
        elif self.type == DataType.BITMAP:
            if self.ui_type != UiType.TABLE:
                return True
                
        return False        

# ----------------- 개별 아이템 모델 (공통 속성 상속) -----------------
class ExplicitItem(CyclicItem):
    service_code: int = -1
    class_id: int = -1
    instance_id: int = -1
    attribute_id: int = -1
    access_type: AccessType = AccessType.EMPTY # EXE일때는 type과 ui_type은 비어있어야 한다. 그렇지 않은 경우는 type과 ui_type은 반드시 있어야 한다.

    @model_validator(mode='after')
    def validate_and_calculate_size(self) -> 'ExplicitItem':
        """ExplicitItem만의 고유한 검증 로직"""
        self.is_json_parsing_err = False

        if not self.name.strip():
            self.is_json_parsing_err = True

        if self.service_code < 0 or self.class_id < 0 or self.instance_id < 0 or self.attribute_id < 0:
            self.is_json_parsing_err = True

        if self.access_type == AccessType.EMPTY:
            self.is_json_parsing_err = True

        if self.access_type == AccessType.EXE:
            if self.type not in (DataType.EMPTY, DataType.NONE) or self.ui_type not in (UiType.EMPTY, UiType.NONE):
                self.is_json_parsing_err = True

            if self.service_code in (14, 16):
                self.is_json_parsing_err = True
        else:
            if self.service_code not in (14, 16):
                self.is_json_parsing_err = True
            
            if self.type in (DataType.EMPTY, DataType.NONE) or self.ui_type in (UiType.EMPTY, UiType.NONE):
                self.is_json_parsing_err = True

        if self.ui_type == UiType.ENUM and not self.enum_list:
            self.is_json_parsing_err = True

        if self.check_bitmap_error():
            self.is_json_parsing_err = True

        if self.check_type_mismatch():
            self.is_json_parsing_err = True

        return self    

class DnetModel:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DnetModel, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 싱글톤이므로 초기화가 여러 번 실행되지 않도록 방어
        if not hasattr(self, 'initialized'):
            self.poll_in_items: List[CyclicItem] = []
            self.poll_out_items: List[CyclicItem] = []
            self.explicit_messages: List[ExplicitItem] = []
            self.initialized = True

    def load_from_json(self, json_path: str) -> Optional[str]:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 2. Pydantic을 통한 파싱 중복 제거 및 간결화
            self.poll_in_items = self._parse_items(data.get('poll-in', []), CyclicItem)
            self.poll_out_items = self._parse_items(data.get('poll-out', []), CyclicItem)
            
            # explicit 혹은 explicit_messages 키 모두 대응
            explicit_data = data.get('explicit', data.get('explicit_messages', []))
            self.explicit_messages = self._parse_items(explicit_data, ExplicitItem)

            return None

        except FileNotFoundError:
            return f"파일을 찾을 수 없습니다: {json_path}"
        except json.JSONDecodeError:
            return f"JSON 형식이 유효하지 않습니다: {json_path}"
        except Exception as e:
            return f"JSON 로드 중 오류 발생: {e}"

    def _parse_items(self, item_list: list, model_class) -> list:
        """
        JSON 리스트를 받아 Pydantic 모델 리스트로 변환합니다.
        에러 발생 시 프로그램이 죽지 않고 해당 아이템만 에러 처리합니다.
        """
        parsed_items = []
        for item in item_list:
            if not isinstance(item, dict):
                continue
                
            try:
                # Pydantic 모델을 통해 자동 매핑 및 타입 검증 (size 계산 포함)
                parsed_item = model_class(**item)
                parsed_items.append(parsed_item)
                
            except Exception as e:
                # 5. Pydantic 검증 에러 (타입 불일치 등) 발생 시 에러 핸들링                
                # 에러가 발생한 항목도 UI에 보여주기 위해 기본값으로 생성하되 에러 플래그 설정
                err_item = model_class()
                err_item.name = item.get('name', 'JSON Parsing Error') # 이름만 최소한으로 보존
                err_item.is_json_parsing_err = True
                err_item.size = 0
                parsed_items.append(err_item)
                
        return parsed_items