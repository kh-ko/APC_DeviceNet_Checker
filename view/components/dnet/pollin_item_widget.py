from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal

from model.dnet.dnet_item_model import PollInItem

class PollInItemWidget(QWidget):
    # 부모 위젯(리스트 관리자)에게 이벤트를 전달하기 위한 커스텀 시그널 정의
    sig_move_up = Signal(object)    # 자신(Widget 인스턴스)을 전달
    sig_move_down = Signal(object)
    sig_edit = Signal(object)
    sig_delete = Signal(object)
    sig_enable_changed = Signal(object, bool)

    def __init__(self, item: PollInItem, parent=None):
        super().__init__(parent)
        self.item = item
        
        self._init_ui()
        self.update_ui_from_data()

    def _init_ui(self):
        # 리스트의 한 줄(Row)처럼 보이도록 기본 설정
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)

        # 1. Enable 체크박스 (디폴트 체크)
        self.chk_enable = QCheckBox()
        self.chk_enable.setChecked(True)
        self.chk_enable.stateChanged.connect(self._on_enable_changed)
        self.main_layout.addWidget(self.chk_enable)

        # 2. Name 라벨
        self.lbl_name = QLabel()
        self.lbl_name.setMinimumWidth(200)
        self.main_layout.addWidget(self.lbl_name)

        # 3. Offset 라벨
        self.lbl_offset = QLabel()
        self.lbl_offset.setFixedWidth(70)
        self.main_layout.addWidget(self.lbl_offset)

        # 4. Size 라벨
        self.lbl_size = QLabel()
        self.lbl_size.setFixedWidth(60)
        self.main_layout.addWidget(self.lbl_size)

        # 5. is_json_parsing_err 인디케이터
        self.lbl_json_err = QLabel("JSON")
        self.lbl_json_err.setAlignment(Qt.AlignCenter)
        self.lbl_json_err.setFixedSize(40, 20)
        self.main_layout.addWidget(self.lbl_json_err)

        # 6. is_data_err 인디케이터
        self.lbl_data_err = QLabel("DATA")
        self.lbl_data_err.setAlignment(Qt.AlignCenter)
        self.lbl_data_err.setFixedSize(40, 20)
        self.main_layout.addWidget(self.lbl_data_err)

        # 7. 읽어온 값 표시 라벨
        self.lbl_read_value = QLabel("Value: -")
        self.lbl_read_value.setMinimumWidth(100)
        # 값이 눈에 잘 띄도록 스타일 적용
        self.lbl_read_value.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 2px;")
        self.main_layout.addWidget(self.lbl_read_value)

        # UI 요소들이 왼쪽으로 정렬되도록 빈 공간(Stretch) 추가
        self.main_layout.addStretch(1)

        # 8. 컨트롤 버튼들 (Up, Down, Edit, Delete)
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_edit = QPushButton("편집")
        self.btn_delete = QPushButton("삭제")

        self.btn_up.setFixedWidth(30)
        self.btn_down.setFixedWidth(30)

        self.main_layout.addWidget(self.btn_up)
        self.main_layout.addWidget(self.btn_down)
        self.main_layout.addWidget(self.btn_edit)
        self.main_layout.addWidget(self.btn_delete)

        # 버튼 클릭 이벤트 -> 내부 시그널 발생
        self.btn_up.clicked.connect(lambda: self.sig_move_up.emit(self))
        self.btn_down.clicked.connect(lambda: self.sig_move_down.emit(self))
        self.btn_edit.clicked.connect(lambda: self.sig_edit.emit(self))
        self.btn_delete.clicked.connect(lambda: self.sig_delete.emit(self))

    def update_ui_from_data(self):
        """모델(self.item)의 데이터를 읽어와서 UI 위젯들에 값을 채웁니다."""
        # 기본 정보 세팅
        self.chk_enable.setChecked(self.item.enabled)
        self.lbl_name.setText(self.item.name if self.item.name else "Unknown")
        self.lbl_offset.setText(f"Offset: {self.item.offset}")
        self.lbl_size.setText(f"Size: {self.item.size}")
        self.lbl_read_value.setText(f"Value: {self.item.data}")

        # JSON 파싱 에러 인디케이터 (에러면 빨간색, 정상이면 회색)
        if self.item.is_json_parsing_err:
            self.lbl_json_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_json_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

        # Data 에러 인디케이터 (통신 데이터 이상 등)
        if self.item.is_data_err:
            self.lbl_data_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_data_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")
            
        # Enable 상태에 따른 UI 활성화/비활성화 처리
        self._apply_enable_style(self.item.enabled)

    def update_read_data(self, new_data: str, is_error: bool = False):
        """통신 모듈로부터 새로운 데이터를 받았을 때 라벨만 업데이트하는 함수"""
        self.item.data = new_data
        self.item.is_data_err = is_error
        
        self.lbl_read_value.setText(f"Val: {new_data}")
        if is_error:
            self.lbl_data_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_data_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

    def _on_enable_changed(self, state):
        """체크박스 상태가 변경되었을 때 호출됩니다."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.item.enabled = is_checked
        self._apply_enable_style(is_checked)
        
        # 부모에게 Enable 상태가 변경되었음을 알림 (오프셋 재계산 등이 필요할 수 있음)
        self.sig_enable_changed.emit(self, is_checked)

    def _apply_enable_style(self, is_enabled: bool):
        """아이템이 Disable 되면 위젯을 반투명하게 보이도록 처리합니다."""
        widgets_to_toggle = [
            self.lbl_name, self.lbl_offset, self.lbl_size, 
            self.lbl_json_err, self.lbl_data_err, self.lbl_read_value,
            self.btn_edit
        ]
        for w in widgets_to_toggle:
            w.setEnabled(is_enabled)