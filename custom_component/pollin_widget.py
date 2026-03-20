import struct
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QPushButton, QFrame, QGridLayout
from PySide6.QtCore import Signal, Qt

from protocol_model import PollItem


class PollInWidget(QWidget):
    up_clicked = Signal(object) 
    down_clicked = Signal(object)
    enabled_changed = Signal(object, bool) 

    def __init__(self, dev_item: PollItem, parent=None):
        super().__init__(parent)
        self.dev_item = dev_item
        self.bit_labels = []
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        top_layout = QHBoxLayout()

        self.chk_enabled = QCheckBox()
        self.chk_enabled.setChecked(self.dev_item.enabled)
        self.chk_enabled.clicked.connect(self.on_checkbox_clicked)
        self.chk_enabled.checkStateChanged.connect(self.on_checkbox_checkStateChanged)
        top_layout.addWidget(self.chk_enabled)

        self.lbl_name = QLabel(self.dev_item.name)
        self.lbl_name.setMinimumWidth(200)
        top_layout.addWidget(self.lbl_name)

        self.lbl_offset = QLabel()
        self.lbl_offset.setMinimumWidth(80)
        self._update_offset_label()
        top_layout.addWidget(self.lbl_offset)

        self.lbl_type = QLabel(self.dev_item.type)
        self.lbl_type.setMinimumWidth(100)
        top_layout.addWidget(self.lbl_type)

        if self.dev_item.ui_type != "bitmap":
            self.lbl_value = QLabel("-")
            self.lbl_value.setMinimumWidth(120)
            self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_value.setStyleSheet("background-color: #f5f5f5; border: 1px solid #aaa; padding: 2px;")
            top_layout.addWidget(self.lbl_value)

        top_layout.addStretch(1)

        self.btn_up = QPushButton("위로")
        self.btn_up.clicked.connect(self.on_up_clicked)
        top_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("아래로")
        self.btn_down.clicked.connect(self.on_down_clicked)
        top_layout.addWidget(self.btn_down)

        self.main_layout.addLayout(top_layout)

        if self.dev_item.ui_type == "bitmap" and self.dev_item.map:
            self._create_bitmap_table()

    def _create_bitmap_table(self):
        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame { border: 1px solid #ccc; background-color: #fff; }
            QLabel { border: 1px solid #eee; padding: 4px; }
        """)

        grid = QGridLayout(table_frame)
        grid.setSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)

        grid.addWidget(QLabel(""), 0, 0)
        for i in range(8):
            lbl_header = QLabel(f"bit {8-i}")
            lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_header.setStyleSheet("background-color: #e0e0e0; font-weight: bold;")
            grid.addWidget(lbl_header, 0, i + 1)

        for row_idx, map_item in enumerate(self.dev_item.map, start=1):
            # 바이트 이름 라벨
            lbl_byte_name = QLabel(map_item.name)
            grid.addWidget(lbl_byte_name, row_idx, 0)
            
            # 각 비트(0~7) 항목 라벨 (인덱스 0이 MSB(bit 8), 7이 LSB(bit 1))
            for col_idx, bit_text in enumerate(map_item.bits):
                lbl_bit = QLabel(bit_text)
                lbl_bit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(lbl_bit, row_idx, col_idx + 1)
                
                # 향후 통신 데이터 수신 시 색상을 업데이트하기 위해 리스트에 저장
                self.bit_labels.append((map_item.byte_index, col_idx, lbl_bit))
                
        self.main_layout.addWidget(table_frame)
    
    def _update_offset_label(self):
        if(self.dev_item.enabled):
            self.lbl_offset.setText(f"{self.dev_item.offset}")
        else:
            self.lbl_offset.setText("-")

    def on_up_clicked(self):
        self.up_clicked.emit(self)
    
    def on_down_clicked(self):
        self.down_clicked.emit(self)
    
    def on_checkbox_clicked(self, checked: bool):
        self.enabled_changed.emit(self, checked)

    def on_checkbox_checkStateChanged(self, state: int):
        self.dev_item.enabled = state == Qt.CheckState.Checked
        self._update_offset_label()

    def receive_data(self, data: bytes):
        ui_type = self.dev_item.ui_type
        type_str = self.dev_item.type
        offset = self.dev_item.offset

        if ui_type == "bitmap":
            for byte_idx, col_idx, lbl in self.bit_labels:
                # 통신 데이터 범위 내에 존재하는지 확인
                if offset + byte_idx < len(data):
                    val = data[offset + byte_idx]
                    # col_idx: 0(bit 8, MSB) ~ 7(bit 1, LSB)
                    is_set = bool(val & (1 << (7 - col_idx)))
                    
                    if is_set:
                        lbl.setStyleSheet("background-color: #FF5252; color: white; font-weight: bold; border: 1px solid #ccc;")
                    else:
                        lbl.setStyleSheet("background-color: transparent; color: black; border: 1px solid #eee;")
                        
        # 2. Number, Real, Enum인 경우: 파싱하여 value label에 텍스트로 표시
        else:
            val = None
            try:
                # 리틀 엔디안('<')을 기준으로 파싱
                if type_str in ("int8", "uint8"):
                    fmt = '<b' if type_str == "int8" else '<B'
                    val = struct.unpack_from(fmt, data, offset)[0]
                elif type_str in ("int16", "uint16"):
                    fmt = '<h' if type_str == "int16" else '<H'
                    val = struct.unpack_from(fmt, data, offset)[0]
                elif type_str in ("int32", "uint32"):
                    fmt = '<i' if type_str == "int32" else '<I'
                    val = struct.unpack_from(fmt, data, offset)[0]
                elif type_str == "float":
                    val = struct.unpack_from('<f', data, offset)[0]
            except struct.error:
                self.lbl_value.setText("Err")
                return

            if val is not None:
                display_str = str(val)
                # Enum 타입인 경우 값과 일치하는 text 검색
                if ui_type == "enum" and self.dev_item.enum_list:
                    for e in self.dev_item.enum_list:
                        if e.value == val:
                            display_str = e.text
                            break
                # 실수형 출력 포맷 (소수점 4자리 등 필요에 따라 조정)
                elif ui_type == "real" and isinstance(val, float):
                    display_str = f"{val:.4f}"
                    
                self.lbl_value.setText(display_str)

    def set_sequence_num(self, sequence_num: int):
        # sequence_num을 변경한다.
        self.dev_item.sequence_num = sequence_num

    def get_sequence_num(self) -> int:
        # sequence_num을 반환한다.
        return self.dev_item.sequence_num

    def get_enabled(self) -> bool:
        # enabled를 반환한다.
        return self.dev_item.enabled

    def set_offset(self, offset: int):
        # offset을 변경한다.
        self.dev_item.offset = offset
        self._update_offset_label()

    def get_offset(self) -> int:
        # offset을 반환한다.
        return self.dev_item.offset


