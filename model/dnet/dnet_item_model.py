from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

class EnumItem(BaseModel):
    text: str = ""
    value: int = 0

class BitmapItem(BaseModel):
    name: str = ""
    bits: List[str] = Field(default_factory=list)

class BaseDnetItem(BaseModel):
    """모든 DNet 아이템이 공유하는 공통 모델"""
    # JSON 매핑 필드 (기본값을 부여하여 누락 시에도 안전하게 처리)
    name: str = ""
    type: str = ""
    ui_type: str = ""
    enum_list: Optional[List[EnumItem]] = None
    bitmap: Optional[List[BitmapItem]] = None

    # UI 및 내부 상태 데이터
    enabled: bool = True
    size: int = 0
    offset: int = 0
    is_json_parsing_err: bool = False

    @model_validator(mode='after')
    def validate_and_calculate_size(self) -> 'BaseDnetItem':
        # 이미 파싱 에러 상태로 마킹된 경우 사이즈를 0으로 고정
        #if self.is_json_parsing_err:
        #    self.size = 0
        #    return self

        type_name = self.type.lower().strip()

        if type_name in ('none', ''):
            # 자식 클래스(ExplicitItem)에 access_type 속성이 존재하고, 그 값이 'Exe'인지 확인
            if getattr(self, 'access_type', None) == 'Exe':
                self.size = 0
                self.is_json_parsing_err = False
            else:
                self.size = 0
                self.is_json_parsing_err = True
            return self
                    
        size_map = {
            'uint8': 1, 'int8': 1, 'byte': 1,
            'uint16': 2, 'int16': 2, 'word': 2,
            'uint32': 4, 'int32': 4, 'dword': 4,
            'float': 4
        }

        # 3. Bitmap 크기 계산 방식 유지
        if type_name == 'bitmap':
            self.size = len(self.bitmap) if self.bitmap else 1
            self.is_json_parsing_err = False
            
        # 1. 매핑 테이블에 존재하는 타입일 경우
        elif type_name in size_map:
            self.size = size_map[type_name]
            self.is_json_parsing_err = False
            
        # 1 & 5. 매핑 테이블에 없는 알 수 없는 타입인 경우 에러 처리
        else:
            self.size = 0
            self.is_json_parsing_err = True

        return self

# ----------------- 개별 아이템 모델 (공통 속성 상속) -----------------

class PollInItem(BaseDnetItem):
    data: str = ""

class PollOutItem(BaseDnetItem):
    written_data: str = ""
    write_ready_data: str = ""

class ExplicitItem(BaseDnetItem):
    class_id: int = 0
    instance_id: int = 0
    attribute_id: int = 0
    access_type: str = ""
    read_data: str = ""
    write_data: str = ""