from enum import Enum
import struct
from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton, QFrame, QTableWidget, QHeaderView, QVBoxLayout, QTableWidgetItem, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.utils.math_utils import format_sigfigs_width_hex

from app.model.dnet.dnet_model import CyclicItem, ExplicitItem, AccessType, DataType, UiType

from app.ui.components.custom.custom_controls import CustomComboBox, CustomLineEdit, CustomPushButton, CustomCheckBox, CustomTableWidget, CustomLabel, CustomSpinBox, CustomDoubleSpinBox

class ItemType(str, Enum):
    PollIn = 'PollIn' 
    PollOut = 'PollOut'
    Explicit = 'Explicit'
    

class ItemWidget(QWidget):
    # 부모 위젯(리스트 관리자)에게 이벤트를 전달하기 위한 커스텀 시그널 정의
    sig_move_up = Signal(object)    # 자신(Widget 인스턴스)을 전달
    sig_move_down = Signal(object)
    sig_edit = Signal(object)
    sig_delete = Signal(object)
    sig_enable_changed = Signal(object, bool)
    sig_req_write_explicit = Signal(int, int, int, bytes)      
    sig_req_read_explicit = Signal(int, int, int)
    sig_req_execute_explicit = Signal(int, int, int, int)

    def __init__(self, item : CyclicItem, type:ItemType, parent=None):
        super().__init__(parent)

        self.chk_enabled = True
        self.item_type = type
        self.name = item.name
        self.type = item.type
        self.ui_type = item.ui_type
        self.enum_list = item.enum_list
        self.bitmap = item.bitmap
        self.is_json_parsing_err = item.is_json_parsing_err
        self.service_code = -1
        self.class_id = -1
        self.instance_id = -1
        self.attribute_id = -1
        self.access_type = AccessType.EMPTY
        
        if self.item_type == ItemType.Explicit:
            explicitItem : ExplicitItem = item
            self.service_code = explicitItem.service_code
            self.class_id = explicitItem.class_id
            self.instance_id = explicitItem.instance_id
            self.attribute_id = explicitItem.attribute_id
            self.access_type = explicitItem.access_type

        self.offset = 0
        self.size = self._calculate_size()        
        
        self._init_ui()
        self._update_ui_from_data()

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
        if self.item_type != ItemType.Explicit:
            self.chk_enable = CustomCheckBox()
            self.chk_enable.setChecked(True)
            self.chk_enable.stateChanged.connect(self._on_enable_changed)
            self.main_layout.addWidget(self.chk_enable)

        # 2. Name 라벨
        self.lbl_name = CustomLabel()
        self.lbl_name.setMinimumWidth(200)
        self.main_layout.addWidget(self.lbl_name)

        # 3. 라벨 1 ( offset 또는 service code)
        self.lbl_01 = CustomLabel()
        self.lbl_01.setFixedWidth(70)
        self.main_layout.addWidget(self.lbl_01)

        # 4. 라벨 2 ( size 또는 class id, instance id, attribute id)
        self.lbl_02 = CustomLabel()
        self.lbl_02.setFixedWidth(60)
        self.main_layout.addWidget(self.lbl_02)

        if self.item_type == ItemType.Explicit:
            self.lbl_01.setVisible(False)
            self.lbl_02.setFixedWidth(130)

        # 5. is_json_parsing_err 인디케이터
        self.lbl_json_err = CustomLabel("JSON")
        self.lbl_json_err.setAlignment(Qt.AlignCenter)
        self.lbl_json_err.setFixedSize(40, 20)
        self.main_layout.addWidget(self.lbl_json_err)

        # 6. is_data_err 인디케이터
        self.lbl_data_err = CustomLabel("DATA")
        self.lbl_data_err.setAlignment(Qt.AlignCenter)
        self.lbl_data_err.setFixedSize(40, 20)
        self.main_layout.addWidget(self.lbl_data_err)

        # 7. Value 입력 및 표시 레이아웃 (1:1 비율)
        self.value_layout = QHBoxLayout()
        self.value_layout.setSpacing(5)

        # 7-1. 읽어온(또는 작성된) 값 표시 라벨
        self.lbl_written_value = CustomLabel("Value: -")
        self.lbl_written_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_written_value.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 2px;")
        self.value_layout.addWidget(self.lbl_written_value, 1)

        # 7-2. 사용자 입력 위젯 (enum이면 콤보박스, 아니면 LineEdit)
        self.input_widget = None

        if self.item_type == ItemType.PollOut:
            self.input_widget = self._create_input_widget()
        elif self.item_type == ItemType.Explicit:
            if self.access_type == AccessType.RW or self.access_type == AccessType.WO:
                self.input_widget = self._create_input_widget()

        if self.input_widget:
            self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.value_layout.addWidget(self.input_widget, 1)

        self.main_layout.addLayout(self.value_layout)

        # 8. 컨트롤 버튼들 (Up, Down, Edit, Delete)
        if self.item_type == ItemType.Explicit:
            self.btn_req_read = CustomPushButton("읽기")
            self.btn_req_send = CustomPushButton("보내기")
            self.main_layout.addWidget(self.btn_req_read)
            self.main_layout.addWidget(self.btn_req_send)
            self.btn_req_read.clicked.connect(self.on_req_read_clicked)
            self.btn_req_send.clicked.connect(self.on_req_send_clicked)
        else:
            self.btn_up = CustomPushButton("▲")
            self.btn_down = CustomPushButton("▼")
            self.btn_up.setFixedWidth(30)
            self.btn_down.setFixedWidth(30)
            self.main_layout.addWidget(self.btn_up)
            self.main_layout.addWidget(self.btn_down)
            self.btn_up.clicked.connect(lambda: self.sig_move_up.emit(self))
            self.btn_down.clicked.connect(lambda: self.sig_move_down.emit(self))

        self.btn_edit = CustomPushButton("편집")
        self.btn_delete = CustomPushButton("삭제")
        self.main_layout.addWidget(self.btn_edit)
        self.main_layout.addWidget(self.btn_delete)
        self.btn_edit.clicked.connect(lambda: self.sig_edit.emit(self))
        self.btn_delete.clicked.connect(lambda: self.sig_delete.emit(self))

        self.root_layout.addWidget(row_widget)

        self.table_widget = CustomTableWidget()
        self.table_widget.setVisible(False) # Bitmap 타입이 아니면 숨김
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # 읽기 전용
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.NoSelection) # 선택 불가
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        table_layout = QHBoxLayout()
        table_layout.setContentsMargins(80, 0, 80, 0) # 좌, 상, 우, 하
        table_layout.addWidget(self.table_widget)
        
        # ✨ 3. 테이블 위젯 대신, 테이블을 감싼 레이아웃을 root_layout에 추가합니다.
        self.root_layout.addLayout(table_layout)

    def _calculate_size(self):
        
        if self.type == DataType.EMPTY or self.type == DataType.NONE:
            if self.item_type == ItemType.Explicit:
                # 자식 클래스(ExplicitItem)에 access_type 속성이 존재하고, 그 값이 'Exe'인지 확인
                if self.access_type != AccessType.EXE:
                    self.is_json_parsing_err = True
            return 0
                    
        size_map = {
            'uint8': 1, 'int8': 1, 'byte': 1,
            'uint16': 2, 'int16': 2, 'word': 2,
            'uint32': 4, 'int32': 4, 'dword': 4,
            'float': 4
        }

        # 3. Bitmap 크기 계산 방식 유지
        if self.type == DataType.BITMAP:
            return len(self.bitmap) if self.bitmap else 1
            
        # 1. 매핑 테이블에 존재하는 타입일 경우
        elif self.type in size_map:
            return size_map[self.type]
            
        # 1 & 5. 매핑 테이블에 없는 알 수 없는 타입인 경우 에러 처리
        else:
            return 0

    def _create_input_widget(self):
        """ui_type에 따라 콤보박스 또는 텍스트 입력 위젯을 생성합니다."""

        if self.type == DataType.EMPTY or self.type == DataType.NONE:
            widget = CustomSpinBox()
            widget.setRange(0, 255)
            return widget

        if self.ui_type == UiType.ENUM and self.enum_list:
            combo = CustomComboBox()
            for enum_item in self.enum_list:
                # 객체나 dict 모두 지원하도록 getattr/get 활용
                text = getattr(enum_item, 'text', "") if not isinstance(enum_item, dict) else enum_item.get('text', "")
                value = getattr(enum_item, 'value', 0) if not isinstance(enum_item, dict) else enum_item.get('value', 0)
                combo.addItem(text, value)
            return combo
        elif self.ui_type == UiType.REAL:
            widget = CustomDoubleSpinBox()
            widget.setRange(-999999999.0, 999999999.0)
            return widget            
        else:
            if self.type == DataType.UINT32:
                widget = CustomDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(0, 4294967295)
                return widget
            elif self.type == DataType.INT32:
                widget = CustomDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(-2147483648, 2147483647)
                return widget
            else:
                widget = CustomDoubleSpinBox()
                widget.setDecimals(0)
                if self.type == DataType.UINT8:
                    widget.setRange(0, 255)
                elif self.type == DataType.INT8:
                    widget.setRange(-128, 127)
                elif self.type == DataType.UINT16:
                    widget.setRange(0, 65535)
                elif self.type == DataType.INT16:
                    widget.setRange(-32768, 32767)
                else:
                    widget.setRange(-32768, 32767)
                return widget


    def _update_ui_from_data(self):
        # 기본 정보 세팅
        self.lbl_name.setText(self.name if self.name else "Unknown")

        if self.item_type != ItemType.Explicit:
            self.lbl_01.setText(f"Offset: {self.offset}")
            self.lbl_02.setText(f"Size: {self.size}")
        else:
            self.lbl_02.setText(f"SC: {self.service_code} CI: {self.class_id}, II: {self.instance_id}, AI: {self.attribute_id}")

        # JSON 파싱 에러 인디케이터 (에러면 빨간색, 정상이면 회색)
        if self.is_json_parsing_err:
            self.lbl_json_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_json_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

        self._set_error_state(False)
        # Enable 상태에 따른 UI 활성화/비활성화 처리
        self._apply_enable_style(self.chk_enabled)

        if self.type == DataType.BITMAP and self.bitmap:
            self.table_widget.setVisible(True)
            self.table_widget.setColumnCount(9) # Byte이름 + 8개 비트
            self.table_widget.setRowCount(len(self.bitmap))
            
            # 헤더 텍스트 (MSB -> LSB 순서)
            headers = ["Byte Name", "Bit 7", "Bit 6", "Bit 5", "Bit 4", "Bit 3", "Bit 2", "Bit 1", "Bit 0"]
            self.table_widget.setHorizontalHeaderLabels(headers)
            
            # 열 너비 자동 맞춤
            header_view = self.table_widget.horizontalHeader()
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # 이름 부분은 여백을 채움
            for i in range(1, 9):
                header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            # JSON에서 파싱된 비트 이름들 채우기
            for row_idx, bmp_item in enumerate(self.bitmap):
                name = getattr(bmp_item, 'name', "") if not isinstance(bmp_item, dict) else bmp_item.get('name', "")
                bits = getattr(bmp_item, 'bits', []) if not isinstance(bmp_item, dict) else bmp_item.get('bits', [])
                
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(name))
                
                # 1~8열: 각 Bit의 설명/이름
                for bit_idx, bit_name in enumerate(bits):
                    if bit_idx < 8:
                        cell_item = QTableWidgetItem(bit_name)
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table_widget.setItem(row_idx, bit_idx + 1, cell_item)
            
            # 테이블 높이를 내용에 맞게 동적으로 조정하여 스크롤바 방지
            row_heights = sum(self.table_widget.rowHeight(r) for r in range(self.table_widget.rowCount()))
            header_height = self.table_widget.horizontalHeader().height()
            self.table_widget.setFixedHeight(header_height + row_heights + 10)        

    def refresh_ui(self):
        self.offset = 0
        self.size = self._calculate_size()        

        if self.input_widget:
            self.value_layout.removeWidget(self.input_widget)
            self.input_widget.deleteLater()
            self.input_widget = None

        if self.item_type == ItemType.PollOut:
            self.input_widget = self._create_input_widget()
        elif self.item_type == ItemType.Explicit:
            if self.access_type == AccessType.RW or self.access_type == AccessType.WO:
                self.input_widget = self._create_input_widget()

        if self.input_widget:
            self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.value_layout.addWidget(self.input_widget, 1)

        self._update_ui_from_data()

        self.sig_enable_changed.emit(self, self.chk_enabled)

    def update_read_data(self, full_raw_data: bytes, is_error: bool = False):
        """통신 모듈로부터 새로운 데이터를 받았을 때 라벨만 업데이트하는 함수"""
        if self.chk_enable.isChecked() == False:
            return

        if is_error or not full_raw_data:
            self._set_error_state(is_error=True)
            return

        end_idx = self.offset + self.size
        if len(full_raw_data) < end_idx:
            self._set_error_state(is_error=True)
            return

        chunk = full_raw_data[self.offset : end_idx]
        parsed_value = ""

        try:
            if self.type == DataType.BITMAP:
                parsed_value = "0x" + chunk.hex(' ').upper()
                
                if self.bitmap:
                    for row_idx, byte_val in enumerate(chunk):
                        if row_idx >= self.table_widget.rowCount():
                            break
                        
                        # 각 Byte의 8개 Bit(7~0)를 검사
                        for bit_idx in range(8):
                            # MSB(Bit 7)가 JSON bits 배열의 0번 인덱스에 매핑된다고 가정
                            # 비트 검사: byte_val의 (7 - bit_idx)번째 비트가 1인지 확인
                            is_active = (byte_val >> (7 - bit_idx)) & 1
                            
                            cell_item = self.table_widget.item(row_idx, bit_idx + 1)
                            if cell_item:
                                if is_active:
                                    cell_item.setBackground(QColor("#90EE90")) # Light Green
                                    cell_item.setForeground(QColor("black"))
                                else:
                                    cell_item.setBackground(QColor("white"))
                                    cell_item.setForeground(QColor("gray")) # 꺼진 비트는 흐리게
                                    
            # 2. 일반 타입 바이트 디코딩 (struct 모듈 활용)
            else:
                val, parsed_value = format_sigfigs_width_hex(self.type.value, chunk, 6)

            # 4. Enum 매핑이 있다면 값 대신 텍스트로 치환 (옵션)
            if self.ui_type == UiType.ENUM and self.enum_list:
                for enum_item in self.enum_list:
                    e_value = getattr(enum_item, 'value', None) if not isinstance(enum_item, dict) else enum_item.get('value')
                    e_text = getattr(enum_item, 'text', "") if not isinstance(enum_item, dict) else enum_item.get('text', "")
                    
                    if e_value == val:
                        parsed_value = f"{parsed_value}:{e_text}"
                        break

            self.lbl_written_value.setText(f"Val: {parsed_value}")
            self._set_error_state(is_error=False)

        except Exception as e:
            self._set_error_state(is_error=True)

    def get_bytes_data(self, buffer:bytearray):
        if buffer is None:
            return

        if self.chk_enabled == False:
            return

        val = None

        if isinstance(self.input_widget, CustomComboBox):
            val = self.input_widget.currentData()
        elif isinstance(self.input_widget, CustomDoubleSpinBox):
            val = self.input_widget.value()
        elif isinstance(self.input_widget, CustomSpinBox):
            val = self.input_widget.value()
        else:
            val = 0

        if self.offset + self.size > len(buffer):
            return

        try:
            payload = b""
            if self.type == DataType.UINT8:
                payload = struct.pack('<B', int(round(val)))
            elif self.type == DataType.INT8:
                payload = struct.pack('<b', int(round(val)))
            elif self.type == DataType.UINT16:
                payload = struct.pack('<H', int(round(val)))
            elif self.type == DataType.INT16:
                payload = struct.pack('<h', int(round(val)))
            elif self.type == DataType.UINT32:
                payload = struct.pack('<I', int(round(val)))
            elif self.type == DataType.INT32:
                payload = struct.pack('<i', int(round(val)))
            elif self.type == DataType.FLOAT:
                payload = struct.pack('<f', float(val))

            # 생성된 payload를 data_buffer의 offset 위치에 복사 (Little Endian 기준)
            copy_len = min(len(payload), self.size)
            buffer[self.offset : self.offset + copy_len] = payload[:copy_len]

        except (struct.error, ValueError, TypeError):
            pass  # 패킹 에러 발생 시 해당 항목은 무시

    def _on_enable_changed(self, state):
        """체크박스 상태가 변경되었을 때 호출됩니다."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.chk_enabled = is_checked
        self._apply_enable_style(is_checked)
        
        # 부모에게 Enable 상태가 변경되었음을 알림 (오프셋 재계산 등이 필요할 수 있음)
        self.sig_enable_changed.emit(self, is_checked)

    def on_req_read_clicked(self):
        self.sig_req_read_explicit.emit(self.class_id, self.instance_id, self.attribute_id)

    def on_req_send_clicked(self):
        if self.access_type == AccessType.EXE:
            self.sig_req_execute_explicit(self.service_code, self.class_id, self.instance_id, self.attribute_id)
        else:
            buffer = bytearray(self.size)
            self.get_bytes_data(buffer)
            final_bytes = bytes(buffer)
            self.sig_req_write_explicit.emit(self.class_id, self.instance_id, self.attribute_id, final_bytes)
        

    def _apply_enable_style(self, is_enabled: bool):
        """아이템이 Disable 되면 위젯을 반투명하게 보이도록 처리합니다."""
        widgets_to_toggle = [
            self.lbl_name, self.lbl_01, self.lbl_02, 
            self.lbl_json_err, self.lbl_data_err, self.lbl_written_value
        ]
        for w in widgets_to_toggle:
            w.setEnabled(is_enabled)

    def _set_error_state(self, is_error: bool):
        if is_error:
            self.lbl_data_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_data_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

    def set_offset(self, offset: int):
        self.offset = offset

        if self.item_type != ItemType.Explicit:
            self.lbl_01.setText(f"Offset: {self.offset}")

    def make_json(self):
        def to_dict(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            return obj

        enum_list_data = [to_dict(e) for e in self.enum_list] if self.enum_list else None
        bitmap_data = [to_dict(b) for b in self.bitmap] if self.bitmap else None

        if self.item_type == ItemType.Explicit:
            return {
                "name": self.name,
                "type": self.type,
                "ui_type": self.ui_type,
                "enum_list": enum_list_data,
                "bitmap": bitmap_data,
                "service_code": self.service_code,
                "class_id": self.class_id,
                "instance_id": self.instance_id,
                "attribute_id": self.attribute_id,
                "access_type": self.access_type,
            }
        else:
            # Poll-In, Poll-Out용 JSON 데이터
            return {
                "name": self.name,
                "type": self.type,
                "ui_type": self.ui_type,
                "enum_list": enum_list_data,
                "bitmap": bitmap_data,
            }
