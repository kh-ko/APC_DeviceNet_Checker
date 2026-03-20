import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class EnumItem:
    text: str
    value: int

@dataclass
class BitmapItem:
    byte_index: int
    name: str
    bits: List[str]

@dataclass
class PollItem:
    """poll-out 및 poll-in의 각 항목을 담는 클래스"""
    name: str
    sequence_num: int
    enabled: bool
    offset: str
    type: str
    ui_type: str
    enum_list: Optional[List[EnumItem]] = None
    map: Optional[List[BitmapItem]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PollItem':
        enum_list = [EnumItem(**e) for e in data.get("enum_list", [])] if "enum_list" in data else None
        map_list = [BitmapItem(**m) for m in data.get("map", [])] if "map" in data else None
        
        return cls(
            name=data["name"],
            sequence_num=data["sequence_num"],
            enabled=data["enabled"],
            offset=data["offset"],
            type=data["type"],
            ui_type=data["ui_type"],
            enum_list=enum_list,
            map=map_list
        )

@dataclass
class ExplicitMessage:
    """explicit_messages의 각 항목을 담는 클래스"""
    name: str
    class_id: int
    instance_id: int
    attribute_id: Optional[int]
    data_size_bytes: Optional[int]
    access_type: str
    type: str
    ui_type: str
    enum_list: Optional[List[EnumItem]] = None
    map: Optional[List[BitmapItem]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExplicitMessage':
        enum_list = [EnumItem(**e) for e in data.get("enum_list", [])] if "enum_list" in data else None
        map_list = [BitmapItem(**m) for m in data.get("map", [])] if "map" in data else None
        
        return cls(
            name=data["name"],
            class_id=data["class_id"],
            instance_id=data["instance_id"],
            attribute_id=data.get("attribute_id"),
            data_size_bytes=data.get("data_size_bytes"),
            access_type=data["access_type"],
            type=data["type"],
            ui_type=data["ui_type"],
            enum_list=enum_list,
            map=map_list
        )

@dataclass
class DeviceConfig:
    """전체 JSON 데이터를 담는 최상위 루트 클래스"""
    poll_out: List[PollItem]
    poll_in: List[PollItem]
    explicit_messages: List[ExplicitMessage]

    @classmethod
    def from_json_file(cls, filepath: str) -> 'DeviceConfig':
        """JSON 파일을 읽어서 DeviceConfig 객체로 변환합니다."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return cls(
            poll_out=[PollItem.from_dict(item) for item in data.get("poll-out", [])],
            poll_in=[PollItem.from_dict(item) for item in data.get("poll-in", [])],
            explicit_messages=[ExplicitMessage.from_dict(item) for item in data.get("explicit_messages", [])]
        )

# ==========================================
# 🚀 사용 예시 (테스트 코드)
# ==========================================
if __name__ == "__main__":
    # 1. JSON 파일 로드 (예: config.json 파일이 같은 폴더에 있다고 가정)
    # config = DeviceConfig.from_json_file('config.json')
    
    # 임시 테스트용 파싱
    sample_json_string = """
    {
        "poll-out": [
            {
                "name": "Control Mode", "sequence_num": 0, "enabled": true, "offset": "0", 
                "type": "uint8", "ui_type": "enum", 
                "enum_list": [{"text": "CLOSE", "value": 0}, {"text": "OPEN", "value": 1}]
            }
        ],
        "poll-in": [],
        "explicit_messages": [
            {
                "name": "Reset", "class_id": 1, "instance_id": 1, "attribute_id": null,
                "data_size_bytes": null, "access_type": "Exe", "type": "none", "ui_type": "action"
            }
        ]
    }
    """
    
    data_dict = json.loads(sample_json_string)
    
    # 딕셔너리에서 클래스로 변환
    config = DeviceConfig(
        poll_out=[PollItem.from_dict(item) for item in data_dict.get("poll-out", [])],
        poll_in=[PollItem.from_dict(item) for item in data_dict.get("poll-in", [])],
        explicit_messages=[ExplicitMessage.from_dict(item) for item in data_dict.get("explicit_messages", [])]
    )
    
    # 2. 파싱된 데이터 접근 테스트
    print(f"Poll-Out 개수: {len(config.poll_out)}")
    print(f"첫 번째 Poll-Out 이름: {config.poll_out[0].name}")
    print(f"첫 번째 Poll-Out Enum 리스트: {config.poll_out[0].enum_list}")
    
    print(f"Explicit Messages 개수: {len(config.explicit_messages)}")
    print(f"첫 번째 Explicit Message의 Access Type: {config.explicit_messages[0].access_type}")