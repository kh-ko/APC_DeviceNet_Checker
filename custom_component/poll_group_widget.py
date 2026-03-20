from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from custom_component.pollin_widget import PollInWidget

class PollListWidget(QWidget):
    """여러 개의 PollInWidget을 스크롤 영역 내에서 관리하는 컨테이너 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 내부 위젯들을 리스트로 관리 (순서 추적 및 데이터 브로드캐스팅 용도)
        self.poll_widgets = [] 
        
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 스크롤 영역 생성
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # 내부 위젯 크기에 맞춰 자동 리사이징
        
        # 2. 스크롤 영역 안에 들어갈 빈 캔버스(컨테이너 위젯) 생성
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # 위에서부터 차곡차곡 쌓이도록 설정
        
        # 3. 조립
        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area)

    def populate(self, poll_items: list):
        """JSON 등에서 불러온 아이템 리스트를 UI에 채워 넣습니다."""
        # 기존 위젯 지우기 (초기화)
        self.clear_widgets()
        
        # sequence_num 기준으로 오름차순 정렬 후 추가
        sorted_items = sorted(poll_items, key=lambda x: x.sequence_num)
        for item in sorted_items:
            self.add_poll_widget(item)

    def add_poll_widget(self, poll_item):
        """단일 PollInWidget을 생성하여 레이아웃과 리스트에 추가합니다."""
        widget = PollInWidget(poll_item)
        
        # 커스텀 시그널 연결 (위로, 아래로, 활성화 상태 변경)
        widget.up_clicked.connect(self.on_widget_up)
        widget.down_clicked.connect(self.on_widget_down)
        widget.enabled_changed.connect(self.on_widget_enabled_changed)
        
        self.container_layout.addWidget(widget)
        self.poll_widgets.append(widget)

    def clear_widgets(self):
        """모든 위젯을 레이아웃과 메모리에서 제거합니다."""
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.poll_widgets.clear()

    # --- 시그널 처리 슬롯 ---

    def on_widget_up(self, widget: QWidget):
        """[위로] 버튼 클릭 시 호출됨"""
        idx = self.container_layout.indexOf(widget)
        if idx > 0: # 맨 위가 아닐 때만
            # 1. 레이아웃에서 순서 변경
            self.container_layout.removeWidget(widget)
            self.container_layout.insertWidget(idx - 1, widget)
            
            # 2. 내부 관리 리스트 순서 변경
            self.poll_widgets.pop(idx)
            self.poll_widgets.insert(idx - 1, widget)
            
            # 3. 내부 sequence_num 재정렬
            self._update_sequence_numbers()
            self._recalculate_offsets()

    def on_widget_down(self, widget: QWidget):
        """[아래로] 버튼 클릭 시 호출됨"""
        idx = self.container_layout.indexOf(widget)
        if idx < len(self.poll_widgets) - 1: # 맨 아래가 아닐 때만
            # 1. 레이아웃에서 순서 변경
            self.container_layout.removeWidget(widget)
            self.container_layout.insertWidget(idx + 1, widget)
            
            # 2. 내부 관리 리스트 순서 변경
            self.poll_widgets.pop(idx)
            self.poll_widgets.insert(idx + 1, widget)
            
            # 3. 내부 sequence_num 재정렬
            self._update_sequence_numbers()
            self._recalculate_offsets()

    def _update_sequence_numbers(self):
        """리스트에 배치된 순서대로 모델의 sequence_num을 0부터 다시 갱신합니다."""
        for i, widget in enumerate(self.poll_widgets):
            widget.set_sequence_num(i)
            # 만약 JSON 파일로 다시 저장하는 기능이 있다면, 
            # 이 시점에 변경된 sequence_num 상태가 모델(poll_item)에 반영됩니다.

    def on_widget_enabled_changed(self, widget, enabled: bool):
        self._recalculate_offsets()

    def _get_byte_size(self, type_str: str) -> int:
        """프로토콜 타입 문자열을 분석하여 바이트 단위 크기를 반환합니다."""
        type_str = type_str.lower()
        
        if type_str in ("int8", "uint8"):
            return 1
        elif type_str in ("int16", "uint16"):
            return 2
        elif type_str in ("int32", "uint32", "float"):
            return 4
        elif type_str.startswith("bytes:"):
            # 예: "bytes:15" -> 15 반환
            try:
                return int(type_str.split(":")[1])
            except (IndexError, ValueError):
                return 0
        return 0

    def _recalculate_offsets(self):
        """현재 UI에 배치된 순서와 활성화(enabled) 상태를 기준으로 Offset을 다시 계산합니다."""
        current_offset = 0
        
        for widget in self.poll_widgets:
            if widget.get_enabled():
                # 활성화된 아이템: 현재 오프셋을 부여하고, 자기 타입 크기만큼 누적함
                widget.set_offset(current_offset)
                
                # 다음 아이템을 위해 현재 아이템의 사이즈만큼 오프셋 증가
                size = self._get_byte_size(widget.dev_item.type)
                current_offset += size

    def receive_data(self, data: bytes):
        """DeviceNet에서 읽어온 원시 바이트 데이터를 모든 하위 위젯에 전달합니다."""
        for widget in self.poll_widgets:
            widget.receive_data(data)