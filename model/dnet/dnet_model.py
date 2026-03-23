import json
import logging
from typing import List, Optional

from model.dnet.pollin_item import PollInItem
from model.dnet.pollout_item import PollOutItem
from model.dnet.explicit_item import ExplicitItem
from model.enum_item import EnumItem
from model.bitmap_item import BitmapItem

class DnetModel:
    def __init__(self):
        self.poll_in_items: List[PollInItem] = []
        self.poll_out_items: List[PollOutItem] = []
        self.explicit_messages: List[ExplicitItem] = []

    def load_from_json(self, json_path: str):
        """
        JSON 파일을 파싱하여 DNet 모델 객체로 로드합니다.
        JSON에 sequence_num, offset, enabled 정보가 없는 경우 자동으로 할당합니다.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 1. poll-in 파싱
                self.poll_in_items = []
                for i, item in enumerate(data.get('poll-in', [])):
                    # enum_list 파싱
                    enum_list = None
                    if 'enum_list' in item:
                        enum_list = [EnumItem(text=e.get('text', ''), value=e.get('value', 0)) for e in item['enum_list']]
                    
                    # bitmap 파싱 (BitmapItem 리스트로 변환)
                    bitmap = None
                    if 'bitmap' in item:
                        bitmap = [BitmapItem(name=b.get('name', ''), bits=b.get('bits', [])) for b in item['bitmap']]
                    
                    # type에 따른 기본 size 계산
                    type_name = item.get('type', '')
                    size = 0
                    if '8' in type_name: size = 1
                    elif '16' in type_name: size = 2
                    elif '32' in type_name or 'float' in type_name: size = 4
                    elif 'bitmap' in type_name: 
                        # 비트맵의 경우 정의된 항목 수(바이트 수)만큼 크기 할당
                        size = len(bitmap) if bitmap else 1
                    
                    # PollInItem 객체 생성 (기본값 사용)
                    poll_in = PollInItem(
                        name=item.get('name', ''),
                        type=type_name,
                        ui_type=item.get('ui_type', ''),
                        size=size,
                        enum_list=enum_list,
                        bitmap=bitmap
                    )
                    self.poll_in_items.append(poll_in)
                
                # 3. poll-out 파싱
                self.poll_out_items = []
                for item in data.get('poll-out', []):
                    # enum_list 파싱
                    enum_list = None
                    if 'enum_list' in item:
                        enum_list = [EnumItem(text=e.get('text', ''), value=e.get('value', 0)) for e in item['enum_list']]
                    
                    # type에 따른 기본 size 계산
                    type_name = item.get('type', '')
                    size = 0
                    if '8' in type_name: size = 1
                    elif '16' in type_name: size = 2
                    elif '32' in type_name or 'float' in type_name: size = 4
                    elif 'bitmap' in type_name: size = 1
                    
                    poll_out = PollOutItem(
                        name=item.get('name', ''),
                        type=type_name,
                        ui_type=item.get('ui_type', ''),
                        size=size,
                        enum_list=enum_list
                    )
                    self.poll_out_items.append(poll_out)
                
                # 4. explicit 파싱
                self.explicit_messages = []
                # JSON 설정 파일에서 "explicit" 혹은 "explicit_messages" 키 모두 대응
                explicit_data = data.get('explicit', data.get('explicit_messages', []))
                for item in explicit_data:
                    # enum_list 파싱
                    enum_list = None
                    if 'enum_list' in item:
                        enum_list = [EnumItem(text=e.get('text', ''), value=e.get('value', 0)) for e in item['enum_list']]
                    
                    # bitmap 파싱 
                    bitmap = None
                    if 'bitmap' in item:
                        bitmap = [BitmapItem(name=b.get('name', ''), bits=b.get('bits', [])) for b in item['bitmap']]
                    
                    # type에 따른 기본 size 계산
                    type_name = item.get('type', '')
                    size = 0
                    if '8' in type_name: size = 1
                    elif '16' in type_name: size = 2
                    elif '32' in type_name or 'float' in type_name: size = 4
                    elif 'bitmap' in type_name: 
                        size = len(bitmap) if bitmap else 1
                        
                    explicit_item = ExplicitItem(
                        name=item.get('name', ''),
                        class_id=item.get('class_id', 0),
                        instance_id=item.get('instance_id', 0),
                        attribute_id=item.get('attribute_id', 0),
                        access_type=item.get('access_type', ''),
                        type=type_name,
                        ui_type=item.get('ui_type', ''),
                        size=size,
                        enum_list=enum_list,
                        bitmap=bitmap
                    )
                    self.explicit_messages.append(explicit_item)

                # 5. 오프셋 계산 및 적용
                self.calculate_offset()
                
        except FileNotFoundError:
            logging.error(f"설정 파일을 찾을 수 없습니다: {json_path}")
        except json.JSONDecodeError:
            logging.error(f"JSON 형식이 유효하지 않습니다: {json_path}")
        except Exception as e:
            logging.error(f"JSON 로드 중 오류 발생: {e}")

    def calculate_offset(self):
        """
        활성(enabled) 상태인 항목들에 대해서만 오프셋을 계산하여 할당합니다.
        비활성 항목은 오프셋을 0으로 설정합니다.
        """
        # poll_in 오프셋 계산
        current_offset = 0
        for item in self.poll_in_items:
            if item.enabled:
                item.offset = current_offset
                current_offset += item.size
            else:
                item.offset = 0

        # poll_out 오프셋 계산
        current_offset = 0
        for item in self.poll_out_items:
            if item.enabled:
                item.offset = current_offset
                current_offset += item.size
            else:
                item.offset = 0

