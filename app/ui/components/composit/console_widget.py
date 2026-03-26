import queue
from enum import Enum, auto
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QListWidget, QListWidgetItem, QCheckBox, QPushButton)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor

class MsgType(Enum):
    INFO = auto()
    ERROR = auto()
    WARNING = auto()
    TX = auto()
    RX = auto()

class ConsoleWidget(QWidget):
    """
    스레드 안전(Thread-safe)하게 메시지를 출력하는 커스텀 콘솔 위젯입니다.
    
    주요 기능:
    - 외부 스레드에서의 안전한 메시지 추가 (Queue + QTimer 활용)
    - 메시지 타입별 색상 표시 및 실시간 필터링
    - UI 렌더링 부하 방지를 위한 일괄(Batch) 처리 및 자동 스크롤
    - 메모리 초과 방지를 위한 오래된 로그 자동 삭제
    """
    MAX_LINES = 20000

    COLOR_MAP = {
        MsgType.INFO: "#00FF00",     # 초록색
        MsgType.ERROR: "#FF3333",    # 빨간색
        MsgType.WARNING: "#FFFF00",  # 노란색
        MsgType.TX: "#3399FF",       # 파란색
        MsgType.RX: "#CC66FF",       # 보라색
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        # 현재 화면에 표시할 메시지 타입 필터 (초기엔 모두 허용)
        self._allowed_filters = set(MsgType)
        
        self._init_ui()
        
        # 외부 스레드에서 UI 스레드로 메시지를 안전하게 전달하기 위한 큐
        self.msg_queue = queue.Queue()
        
        # 큐에 쌓인 메시지를 주기적으로 UI에 반영하는 타이머 설정 (100ms 주기)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._process_message_queue)
        self.update_timer.start(100)

    def _init_ui(self):
        # 1. 메인 레이아웃 구성
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. 상단 필터 및 컨트롤 레이아웃 구성
        self.filter_layout = QHBoxLayout()
        self.filter_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.checkboxes = {}
        for msg_type in MsgType:
            cb = QCheckBox(msg_type.name, self)
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_filters_from_ui)
            
            self.filter_layout.addWidget(cb)
            self.checkboxes[msg_type] = cb
            
        # 여백 추가 및 로그 지우기 버튼 배치
        self.filter_layout.addStretch(1)
        self.clear_btn = QPushButton("Clear Logs", self)
        self.clear_btn.clicked.connect(self.clear_message)
        self.filter_layout.addWidget(self.clear_btn)

        # 3. 하단 로그 출력 리스트 위젯 설정
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: black;
                padding: 5px;
                border: 1px solid #333333;
            }
            QListWidget::item {
                padding: 0px;
            }
        """)

        # 4. 레이아웃 조립
        self.main_layout.addLayout(self.filter_layout)
        self.main_layout.addWidget(self.list_widget)

    def _update_filters_from_ui(self):
        """UI 체크박스 상태를 읽어와 허용된 필터 목록(_allowed_filters)을 갱신합니다."""
        new_filters = {msg_type for msg_type, cb in self.checkboxes.items() if cb.isChecked()}
        self._allowed_filters = new_filters

    # ------------------ API 기능 ------------------

    def add_message(self, msg_type: MsgType, message: str):
        """
        [Thread-Safe] 외부 스레드에서 호출하여 콘솔에 메시지를 추가합니다.
        사전 필터링(Drop-early)을 통해 체크 해제된 메시지는 큐에 넣지 않고 즉시 폐기하여 최적화합니다.
        """
        if msg_type not in self._allowed_filters:
            return

        self.msg_queue.put((msg_type, message))

    def clear_message(self):
        """화면에 표시된 모든 로그를 지우고 대기 중인 큐도 함께 초기화합니다."""
        self.list_widget.clear()
        
        # 큐 내부 데이터 안전하게 비우기
        with self.msg_queue.mutex:
            self.msg_queue.queue.clear()

    # ------------------ 내부 큐 처리 및 렌더링 ------------------

    def _process_message_queue(self):
        """타이머에 의해 주기적으로 호출되어 큐의 메시지를 UI에 일괄 렌더링합니다."""
        if self.msg_queue.empty():
            return

        # 사용자가 과거 로그를 보고 있는지(스크롤을 올렸는지) 확인
        scrollbar = self.list_widget.verticalScrollBar()
        is_scrolled_to_bottom = (self.list_widget.count() == 0) or (scrollbar.value() == scrollbar.maximum())

        # 대량 추가 시 화면 깜빡임 및 렉을 방지하기 위해 렌더링 일시 중단
        self.list_widget.setUpdatesEnabled(False)
        
        added_count = 0
        # UI 응답성을 유지하기 위해 한 번의 타이머 틱(Tick)에서 최대 1000개까지만 처리
        while not self.msg_queue.empty() and added_count < 1000:
            try:
                msg_type, message = self.msg_queue.get_nowait()
            except queue.Empty:
                break

            display_text = f"[{msg_type.name}] {message}"
            item = QListWidgetItem(display_text)
            color_hex = self.COLOR_MAP.get(msg_type, "#FFFFFF")
            item.setForeground(QColor(color_hex))
            
            self.list_widget.addItem(item)
            added_count += 1

        # 메모리 관리: MAX_LINES 초과 시 오래된 로그 삭제
        excess = self.list_widget.count() - self.MAX_LINES
        if excess > 0:
            # 매번 1개씩 지우는 오버헤드를 막기 위해 초과분 + 500개를 한 번에 지움 (버퍼 확보)
            delete_count = excess + 500
            for _ in range(delete_count):
                taken_item = self.list_widget.takeItem(0)
                del taken_item

        # 데이터 추가 및 삭제가 끝난 후 렌더링 재개
        self.list_widget.setUpdatesEnabled(True)

        # 원래 스크롤이 맨 밑에 있었을 경우에만 최신 로그를 따라 자동 스크롤
        if is_scrolled_to_bottom and added_count > 0:
            self.list_widget.scrollToBottom()