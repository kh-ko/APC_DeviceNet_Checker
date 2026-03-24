import struct
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton, QVBoxLayout, QSizePolicy, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from model.dnet.dnet_item_model import PollOutItem

class PollOutItemWidget(QWidget):
    # 부모 위젯(리스트 관리자)에게 이벤트를 전달하기 위한 커스텀 시그널 정의
    sig_move_up = Signal(object)    # 자신(Widget 인스턴스)을 전달
    sig_move_down = Signal(object)
    sig_edit = Signal(object)
    sig_delete = Signal(object)
    sig_enable_changed = Signal(object, bool)

    def __init__(self, item: PollOutItem, parent=None):
        super().__init__(parent)
        self.item = item
        
        self._init_ui()
        self.update_ui_from_data()

    def _init_ui(self):
        # 리스트의 한 줄(Row)처럼 보이도록 기본 설정
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(5)
        self.root_layout.setAlignment(Qt.AlignTop)

        row_widget = QWidget()
        row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout = QHBoxLayout(row_widget)
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

        # 7. Value 입력 및 표시 레이아웃 (1:1 비율)
        value_layout = QHBoxLayout()
        value_layout.setSpacing(5)

        # 7-1. 읽어온(또는 작성된) 값 표시 라벨
        self.lbl_written_value = QLabel("Value: -")
        self.lbl_written_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_written_value.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 2px;")
        value_layout.addWidget(self.lbl_written_value, 1)

        # 7-2. 사용자 입력 위젯 (enum이면 콤보박스, 아니면 LineEdit)
        self.input_widget = self._create_input_widget()
        self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        value_layout.addWidget(self.input_widget, 1)

        self.main_layout.addLayout(value_layout)

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

        self.root_layout.addWidget(row_widget)

        # 버튼 클릭 이벤트 -> 내부 시그널 발생
        self.btn_up.clicked.connect(lambda: self.sig_move_up.emit(self))
        self.btn_down.clicked.connect(lambda: self.sig_move_down.emit(self))
        self.btn_edit.clicked.connect(lambda: self.sig_edit.emit(self))
        self.btn_delete.clicked.connect(lambda: self.sig_delete.emit(self))

    def _create_input_widget(self):
        """ui_type에 따라 콤보박스 또는 텍스트 입력 위젯을 생성합니다."""
        type_name = self.item.type.lower().strip()
        ui_type = self.item.ui_type.lower().strip()

        if ui_type == 'enum' and self.item.enum_list:
            combo = QComboBox()
            for enum_item in self.item.enum_list:
                combo.addItem(enum_item.text, enum_item.value)
            return combo
        elif ui_type == 'real' or type_name == 'float':
            widget = QDoubleSpinBox()
            widget.setRange(-999999999.0, 999999999.0) # float 표현을 위한 충분히 큰 범위
            return widget            
        else:
            if type_name in ('uint32'):
                widget = QDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(0, 4294967295)
                return widget
            elif type_name == 'int32':
                widget = QDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(-2147483648, 2147483647)
                return widget
            # 8비트, 16비트 정수는 일반 QSpinBox 사용
            else:
                widget = QSpinBox()
                if type_name in ('uint8'):
                    widget.setRange(0, 255)
                elif type_name == 'int8':
                    widget.setRange(-128, 127)
                elif type_name in ('uint16'):
                    widget.setRange(0, 65535)
                elif type_name == 'int16':
                    widget.setRange(-32768, 32767)
                else:
                    widget.setRange(-32768, 32767) # 알 수 없는 타입의 기본값
                return widget

    def update_ui_from_data(self):
        """모델(self.item)의 데이터를 읽어와서 UI 위젯들에 값을 채웁니다."""
        # 기본 정보 세팅
        self.chk_enable.setChecked(self.item.enabled)
        self.lbl_name.setText(self.item.name if self.item.name else "Unknown")
        self.lbl_offset.setText(f"Offset: {self.item.offset}")
        self.lbl_size.setText(f"Size: {self.item.size}")
        self.lbl_written_value.setText("Value:")

        # JSON 파싱 에러 인디케이터
        if self.item.is_json_parsing_err:
            self.lbl_json_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_json_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

        # Enable 상태에 따른 UI 활성화/비활성화 처리
        self._apply_enable_style(self.item.enabled)

    def write_apply(self):
        """입력 위젯의 값을 가져와 lbl_written_value에 적용합니다."""
        parsed_value = ""
        val = None

        if isinstance(self.input_widget, QComboBox):
            val = self.input_widget.currentData()
            text = self.input_widget.currentText()
            parsed_value = f"{val} ({text})"
            
        elif isinstance(self.input_widget, QLineEdit):
            text = self.input_widget.text().strip()
            parsed_value = text
            try:
                # float 타입일 때 캐스팅
                if self.item.type.lower() == 'float':
                    val = float(text)
                else:
                    # 정수형 타입 (0으로 주면 10진수/16진수 모두 자동 파싱)
                    val = int(text, 0) if text else 0
            except ValueError:
                val = 0

        # 모델에 전송 준비 데이터 세팅
        self.item.write_ready_data = str(val) if val is not None else ""
        
        # 라벨 업데이트
        self.lbl_written_value.setText(f"Val: {parsed_value}")

    def _on_enable_changed(self, state):
        """체크박스 상태가 변경되었을 때 호출됩니다."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.item.enabled = is_checked
        self._apply_enable_style(is_checked)
        
        # 부모에게 Enable 상태가 변경되었음을 알림
        self.sig_enable_changed.emit(self, is_checked)

    def _apply_enable_style(self, is_enabled: bool):
        """아이템이 Disable 되면 위젯을 비활성화 처리합니다."""
        widgets_to_toggle = [
            self.lbl_name, self.lbl_offset, self.lbl_size, 
            self.lbl_json_err, self.lbl_written_value,
            self.input_widget
        ]
        for w in widgets_to_toggle:
            w.setEnabled(is_enabled)