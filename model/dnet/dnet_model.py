import json
import os
import logging
from typing import List, Literal, Union
from model.dnet.dnet_item_model import PollInItem, PollOutItem, ExplicitItem
from utils.file_path import get_app_path

class DnetModel:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DnetModel, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 싱글톤이므로 초기화가 여러 번 실행되지 않도록 방어
        if not hasattr(self, 'initialized'):
            self.poll_in_items: List[PollInItem] = []
            self.poll_out_items: List[PollOutItem] = []
            self.explicit_messages: List[ExplicitItem] = []
            self.initialized = True
            self.schema_path = ""

    def load_from_json(self, json_path: str):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.schema_path = json_path

            # 2. Pydantic을 통한 파싱 중복 제거 및 간결화
            self.poll_in_items = self._parse_items(data.get('poll-in', []), PollInItem)
            self.poll_out_items = self._parse_items(data.get('poll-out', []), PollOutItem)
            
            # explicit 혹은 explicit_messages 키 모두 대응
            explicit_data = data.get('explicit', data.get('explicit_messages', []))
            self.explicit_messages = self._parse_items(explicit_data, ExplicitItem)

            # 오프셋 계산
            self.calculate_offset()

        except FileNotFoundError:
            logging.error(f"스키마 파일을 찾을 수 없습니다: {json_path}")
        except json.JSONDecodeError:
            logging.error(f"JSON 형식이 유효하지 않습니다: {json_path}")
        except Exception as e:
            logging.error(f"JSON 로드 중 오류 발생: {e}")

    def save_to_json(self):
        try:
            with open(self.schema_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "poll-in": [item.dict() for item in self.poll_in_items],
                    "poll-out": [item.dict() for item in self.poll_out_items],
                    "explicit": [item.dict() for item in self.explicit_messages]
                }, f, indent=4)
        except Exception as e:
            logging.error(f"JSON 저장 중 오류 발생: {e}")

    def save_as_to_json(self, new_schema_name: str):
        """
        새로운 스키마 파일로 저장
        """
        self.schema_path = os.path.join(get_app_path(), "schema", "dnet", new_schema_name + ".json")
        try:
            with open(self.schema_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "poll-in": [item.dict() for item in self.poll_in_items],
                    "poll-out": [item.dict() for item in self.poll_out_items],
                    "explicit": [item.dict() for item in self.explicit_messages]
                }, f, indent=4)
        except Exception as e:
            logging.error(f"JSON 저장 중 오류 발생: {e}")

        return self.schema_path

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
                logging.warning(f"아이템 파싱 실패: {item.get('name', 'Unknown')} | 에러 내역: {e}")
                
                # 에러가 발생한 항목도 UI에 보여주기 위해 기본값으로 생성하되 에러 플래그 설정
                err_item = model_class()
                err_item.name = item.get('name', 'JSON Parsing Error') # 이름만 최소한으로 보존
                err_item.is_json_parsing_err = True
                err_item.size = 0
                parsed_items.append(err_item)
                
        return parsed_items

    def calculate_offset(self):
        # 오프셋 계산 로직은 기존과 동일하게 유지
        current_offset = 0
        for item in self.poll_in_items:
            item.offset = current_offset if item.enabled else 0
            if item.enabled:
                current_offset += item.size

        current_offset = 0
        for item in self.poll_out_items:
            item.offset = current_offset if item.enabled else 0
            if item.enabled:
                current_offset += item.size