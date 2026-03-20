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