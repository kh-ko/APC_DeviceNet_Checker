import struct
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, 
    QSizePolicy, QComboBox, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from model.dnet.dnet_item_model import ExplicitItem

class ExplicitItemWidget(QWidget):
    # 리스트 관리자(부모)로 이벤트를 전달할 커스텀 시그널
    sig_edit = Signal(object)
    sig_delete = Signal(object)
    
    # 통신 제어를 위한 시그널 (Controller/Worker 단과 연결)
    sig_req_explicit = Signal(int, int, int, int, bytes)      

    def __init__(self, item: ExplicitItem, parent=None):
        super().__init__(parent)
        self.item = item
        
        self._init_ui()
        self.update_ui_from_data()

    def _init_ui(self):
        # 1. 전체 레이아웃 (위/아래: 메인 Row / 비트맵 테이블)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(5)
        self.root_layout.setAlignment(Qt.AlignTop)

        # 2. 메인 Row 위젯
        row_widget = QWidget()
        row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout = QHBoxLayout(row_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(8)

        # Name 라벨
        self.lbl_name = QLabel()
        self.lbl_name.setMinimumWidth(150)
        self.main_layout.addWidget(self.lbl_name)

        # Class, Inst, Attr 묶음 라벨
        self.lbl_cia = QLabel()
        self.lbl_cia.setMinimumWidth(120)
        self.lbl_cia.setStyleSheet("color: #0055A4; font-weight: bold;")
        self.main_layout.addWidget(self.lbl_cia)

        # Access 라벨
        self.lbl_access = QLabel()
        self.lbl_access.setFixedWidth(50)
        self.main_layout.addWidget(self.lbl_access)

        # Type 및 Size 라벨
        self.lbl_type = QLabel()
        self.lbl_type.setFixedWidth(60)
        self.main_layout.addWidget(self.lbl_type)
        
        self.lbl_size = QLabel()
        self.lbl_size.setFixedWidth(50)
        self.main_layout.addWidget(self.lbl_size)

        # 에러 인디케이터
        self.lbl_json_err = QLabel("JSON")
        self.lbl_json_err.setAlignment(Qt.AlignCenter)
        self.lbl_json_err.setFixedSize(40, 20)
        self.main_layout.addWidget(self.lbl_json_err)

        self.lbl_data_err = QLabel("DATA")
        self.lbl_data_err.setAlignment(Qt.AlignCenter)
        self.lbl_data_err.setFixedSize(40, 20)
        self.lbl_data_err.setVisible(False)
        self.main_layout.addWidget(self.lbl_data_err)

        # --- 데이터 I/O 영역 ---
        self.io_layout = QHBoxLayout()
        self.io_layout.setSpacing(5)

        # Read 데이터 라벨
        self.lbl_read_value = QLabel("Read: -")
        self.lbl_read_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_read_value.setStyleSheet("background-color: #e6f7ff; border: 1px solid #ccc; padding: 2px;")
        self.io_layout.addWidget(self.lbl_read_value)

        # Write 데이터 입력란
        self.input_widget = self._create_input_widget()
        if self.input_widget:
            self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.io_layout.addWidget(self.input_widget)

        self.main_layout.addLayout(self.io_layout)

        # 읽기/보내기 버튼
        self.btn_req_read = QPushButton("읽기")
        self.btn_req_send = QPushButton("보내기")
        self.btn_req_read.setStyleSheet("background-color: #d4edda;")
        self.btn_req_send.setStyleSheet("background-color: #f8d7da;")
        self.btn_req_read.clicked.connect(self._on_read_clicked)
        self.btn_req_send.clicked.connect(self._on_send_clicked)
        self.main_layout.addWidget(self.btn_req_read)
        self.main_layout.addWidget(self.btn_req_send)

        # 제어 버튼 (Edit, Delete)
        self.btn_edit = QPushButton("편집")
        self.btn_delete = QPushButton("삭제")
        self.main_layout.addWidget(self.btn_edit)
        self.main_layout.addWidget(self.btn_delete)

        self.root_layout.addWidget(row_widget)

        # 3. 비트맵 테이블 위젯 (조건부 표시)
        self.table_widget = QTableWidget()
        self.table_widget.setVisible(False)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        table_layout = QHBoxLayout()
        table_layout.setContentsMargins(80, 0, 80, 0)
        table_layout.addWidget(self.table_widget)
        self.root_layout.addLayout(table_layout)

        # 시그널 바인딩
        self.btn_edit.clicked.connect(lambda: self.sig_edit.emit(self))
        self.btn_delete.clicked.connect(lambda: self.sig_delete.emit(self))

    def _create_input_widget(self):
        """ui_type에 따라 콤보박스 또는 텍스트 입력 위젯을 생성합니다."""
        type_name = self.item.type.lower().strip()
        ui_type = self.item.ui_type.lower().strip()

        if type_name in ("none", ""):
            widget = QSpinBox()
            widget.setRange(0, 255)
            return widget

        if ui_type == 'enum' and self.item.enum_list:
            combo = QComboBox()
            for enum_item in self.item.enum_list:
                combo.addItem(enum_item.text, enum_item.value)
            return combo
        elif ui_type == 'real' or type_name == 'float':
            widget = QDoubleSpinBox()
            widget.setRange(-999999999.0, 999999999.0)
            return widget            
        else:
            if type_name == 'uint32':
                widget = QDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(0, 4294967295)
                return widget
            elif type_name == 'int32':
                widget = QDoubleSpinBox()
                widget.setDecimals(0)
                widget.setRange(-2147483648, 2147483647)
                return widget
            else:
                widget = QSpinBox()
                if type_name == 'uint8':
                    widget.setRange(0, 255)
                elif type_name == 'int8':
                    widget.setRange(-128, 127)
                elif type_name == 'uint16':
                    widget.setRange(0, 65535)
                elif type_name == 'int16':
                    widget.setRange(-32768, 32767)
                else:
                    widget.setRange(-32768, 32767)
                return widget

    def update_ui_from_data(self):
        """모델 데이터를 바탕으로 UI 가시성 및 텍스트를 업데이트합니다."""
        self.lbl_name.setText(self.item.name if self.item.name else "Unknown")
        self.lbl_cia.setText(f"C:{self.item.class_id} I:{self.item.instance_id} A:{self.item.attribute_id}")
        self.lbl_access.setText(self.item.access_type)
        self.lbl_type.setText(self.item.type)
        self.lbl_size.setText(f"Sz: {self.item.size}")

        # JSON 파싱 에러
        if self.item.is_json_parsing_err:
            self.lbl_json_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_json_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

        acc = self.item.access_type.upper().strip()
        typ = self.item.type.lower().strip()

        # 1. Read Label: Exe, WO일 때는 숨김
        self.lbl_read_value.setEnabled(acc not in ["EXE", "WO"])

        # 2. Write Input: Exe, RO일 때는 숨김
        if self.input_widget:
            self.input_widget.setEnabled(acc not in ["EXE", "RO"])

        # 3. Read Button: Exe, WO일 때는 숨김
        self.btn_req_read.setEnabled(acc not in ["EXE", "WO"])

        # 4. Send Button: RO일 때는 숨김
        self.btn_req_send.setEnabled(acc != "RO")

        # 5. Bitmap Table: RO이면서 type이 bitmap일 때만 표시
        if acc == "RO" and typ == "bitmap" and self.item.bitmap:
            self.table_widget.setVisible(True)
            self.table_widget.setColumnCount(9)
            self.table_widget.setRowCount(len(self.item.bitmap))
            
            headers = ["Byte Name", "Bit 7", "Bit 6", "Bit 5", "Bit 4", "Bit 3", "Bit 2", "Bit 1", "Bit 0"]
            self.table_widget.setHorizontalHeaderLabels(headers)
            
            header_view = self.table_widget.horizontalHeader()
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for i in range(1, 9):
                header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            for row_idx, bmp_item in enumerate(self.item.bitmap):
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(bmp_item.name))
                for bit_idx, bit_name in enumerate(bmp_item.bits):
                    if bit_idx < 8:
                        cell_item = QTableWidgetItem(bit_name)
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table_widget.setItem(row_idx, bit_idx + 1, cell_item)
            
            row_heights = sum(self.table_widget.rowHeight(r) for r in range(self.table_widget.rowCount()))
            header_height = self.table_widget.horizontalHeader().height()
            self.table_widget.setFixedHeight(header_height + row_heights + 10)
        else:
            self.table_widget.setVisible(False)

    def _on_read_clicked(self):
        """읽기 버튼 클릭 시 시그널 방출"""
        self.sig_req_explicit.emit(14, self.item.class_id, self.item.instance_id, self.item.attribute_id, b"")

    def _on_send_clicked(self):
        """보내기 버튼 클릭 시 입력된 값을 bytes로 패킹하여 시그널 방출"""
        acc = self.item.access_type.upper().strip()
        type_name = self.item.type.lower().strip()
        
        payload = b""
        
        # EXE 명령일 경우 데이터를 보내지 않음
        if acc == "EXE":
            self.sig_req_explicit.emit(5, self.item.class_id, self.item.instance_id, self.item.attribute_id, b"")
        else:
            # 쓰기 명령일 경우 입력값을 bytes로 변환
            if self.input_widget:
                val = 0
                if isinstance(self.input_widget, QComboBox):
                    val = self.input_widget.currentData()
                elif isinstance(self.input_widget, QDoubleSpinBox):
                    val = self.input_widget.value()
                elif isinstance(self.input_widget, QSpinBox):
                    val = self.input_widget.value()

                try:
                    if type_name in ('uint8', 'byte'):
                        payload = struct.pack('<B', int(val))
                    elif type_name == 'int8':
                        payload = struct.pack('<b', int(val))
                    elif type_name in ('uint16', 'word'):
                        payload = struct.pack('<H', int(val))
                    elif type_name == 'int16':
                        payload = struct.pack('<h', int(val))
                    elif type_name in ('uint32', 'dword'):
                        payload = struct.pack('<I', int(val))
                    elif type_name == 'int32':
                        payload = struct.pack('<i', int(val))
                    elif type_name == 'float':
                        payload = struct.pack('<f', float(val))
                except struct.error:
                    pass

            self.sig_req_explicit.emit(16, self.item.class_id, self.item.instance_id, self.item.attribute_id, payload)

    def update_read_data(self, class_id:int, instance_id:int, attribute_id:int, raw_data: bytes, is_error: bool = False):
        """수신한 응답 데이터를 오프셋 없이 그대로 파싱하여 반영합니다."""
        if(self.item.class_id != class_id or self.item.instance_id != instance_id or self.item.attribute_id != attribute_id):
            return

        self.lbl_data_err.setVisible(is_error)
        if is_error or not raw_data:
            self.lbl_read_value.setText("Read: ERROR")
            return

        chunk = raw_data
        parsed_value = ""

        try:
            type_name = self.item.type.lower().strip()
            
            if type_name == 'bitmap':
                parsed_value = "0x" + chunk.hex().upper()
                if self.item.bitmap and self.table_widget.isVisible():
                    for row_idx, byte_val in enumerate(chunk):
                        if row_idx >= self.table_widget.rowCount():
                            break
                        for bit_idx in range(8):
                            is_active = (byte_val >> (7 - bit_idx)) & 1
                            cell_item = self.table_widget.item(row_idx, bit_idx + 1)
                            if cell_item:
                                if is_active:
                                    cell_item.setBackground(QColor("#90EE90"))
                                    cell_item.setForeground(QColor("black"))
                                else:
                                    cell_item.setBackground(QColor("white"))
                                    cell_item.setForeground(QColor("gray"))
            else:
                # 사이즈 체크: 너무 짧은 응답이 왔을 경우 에러 처리
                if len(chunk) < self.item.size and self.item.size > 0:
                    raise ValueError("Data too short")

                parse_chunk = chunk[:self.item.size] if self.item.size > 0 else chunk

                if type_name in ('uint8', 'byte'):
                    val = struct.unpack('<B', parse_chunk[:1])[0]
                    parsed_value = str(val)
                elif type_name == 'int8':
                    val = struct.unpack('<b', parse_chunk[:1])[0]
                    parsed_value = str(val)
                elif type_name in ('uint16', 'word'):
                    val = struct.unpack('<H', parse_chunk[:2])[0]
                    parsed_value = str(val)
                elif type_name == 'int16':
                    val = struct.unpack('<h', parse_chunk[:2])[0]
                    parsed_value = str(val)
                elif type_name in ('uint32', 'dword'):
                    val = struct.unpack('<I', parse_chunk[:4])[0]
                    parsed_value = str(val)
                elif type_name == 'int32':
                    val = struct.unpack('<i', parse_chunk[:4])[0]
                    parsed_value = str(val)
                elif type_name == 'float':
                    val = struct.unpack('<f', parse_chunk[:4])[0]
                    parsed_value = f"{val:.3f}"
                else:
                    parsed_value = "0x" + chunk.hex().upper()

            # Enum 텍스트 변환 적용
            if getattr(self.item, 'ui_type', '') == 'enum' and self.item.enum_list:
                for enum_item in self.item.enum_list:
                    if str(enum_item.value) == parsed_value:
                        parsed_value = f"{parsed_value} ({enum_item.text})"
                        break

            self.lbl_read_value.setText(f"Read: {parsed_value}")

        except Exception as e:
            self.lbl_data_err.setVisible(True)
            self.lbl_read_value.setText(f"Read: PARSE ERR ({chunk.hex().upper()})")