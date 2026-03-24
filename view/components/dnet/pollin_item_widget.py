import struct
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton, QFrame, QTableWidget, QHeaderView, QVBoxLayout, QTableWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
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

        self.root_layout.addWidget(row_widget)

        self.table_widget = QTableWidget()
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
        self.lbl_read_value.setText("Value:")

        # JSON 파싱 에러 인디케이터 (에러면 빨간색, 정상이면 회색)
        if self.item.is_json_parsing_err:
            self.lbl_json_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_json_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")

        self._set_error_state(False)
        # Enable 상태에 따른 UI 활성화/비활성화 처리
        self._apply_enable_style(self.item.enabled)

        if self.item.type.lower() == 'bitmap' and self.item.bitmap:
            self.table_widget.setVisible(True)
            self.table_widget.setColumnCount(9) # Byte이름 + 8개 비트
            self.table_widget.setRowCount(len(self.item.bitmap))
            
            # 헤더 텍스트 (MSB -> LSB 순서)
            headers = ["Byte Name", "Bit 7", "Bit 6", "Bit 5", "Bit 4", "Bit 3", "Bit 2", "Bit 1", "Bit 0"]
            self.table_widget.setHorizontalHeaderLabels(headers)
            
            # 열 너비 자동 맞춤
            header_view = self.table_widget.horizontalHeader()
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # 이름 부분은 여백을 채움
            for i in range(1, 9):
                header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            # JSON에서 파싱된 비트 이름들 채우기
            for row_idx, bmp_item in enumerate(self.item.bitmap):
                # 0열: Byte 이름
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(bmp_item.name))
                
                # 1~8열: 각 Bit의 설명/이름
                for bit_idx, bit_name in enumerate(bmp_item.bits):
                    if bit_idx < 8:
                        cell_item = QTableWidgetItem(bit_name)
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table_widget.setItem(row_idx, bit_idx + 1, cell_item)
            
            # 테이블 높이를 내용에 맞게 동적으로 조정하여 스크롤바 방지
            row_heights = sum(self.table_widget.rowHeight(r) for r in range(self.table_widget.rowCount()))
            header_height = self.table_widget.horizontalHeader().height()
            self.table_widget.setFixedHeight(header_height + row_heights + 10)        

    def update_read_data(self, full_raw_data: bytes, is_error: bool = False):
        """통신 모듈로부터 새로운 데이터를 받았을 때 라벨만 업데이트하는 함수"""

        if is_error or not full_raw_data:
            self._set_error_state(is_error=True)
            return

        end_idx = self.item.offset + self.item.size
        if len(full_raw_data) < end_idx:
            self._set_error_state(is_error=True)
            return

        chunk = full_raw_data[self.item.offset : end_idx]
        parsed_value = ""

        try:
            type_name = self.item.type.lower().strip()
            if type_name == 'bitmap':
                parsed_value = "0x" + chunk.hex().upper()
                
                if self.item.bitmap:
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
                # 3. 타입에 따른 바이트 디코딩 (struct 모듈 활용)
                if type_name in ('uint8', 'byte'):
                    val = struct.unpack('<B', chunk)[0]
                    parsed_value = str(val)
                elif type_name == 'int8':
                    val = struct.unpack('<b', chunk)[0]
                    parsed_value = str(val)
                elif type_name in ('uint16', 'word'):
                    val = struct.unpack('<H', chunk)[0]
                    parsed_value = str(val)
                elif type_name == 'int16':
                    val = struct.unpack('<h', chunk)[0]
                    parsed_value = str(val)
                elif type_name in ('uint32', 'dword'):
                    val = struct.unpack('<I', chunk)[0]
                    parsed_value = str(val)
                elif type_name == 'int32':
                    val = struct.unpack('<i', chunk)[0]
                    parsed_value = str(val)
                elif type_name == 'float':
                    val = struct.unpack('<f', chunk)[0]
                    # 소수점 3자리 정도까지만 출력
                    parsed_value = f"{val:.3f}"
                else:
                    # 알 수 없는 타입은 Hex 형식으로 표시
                    parsed_value = "0x" + chunk.hex().upper()

            # 4. Enum 매핑이 있다면 값 대신 텍스트로 치환 (옵션)
            if self.item.ui_type == 'enum' and self.item.enum_list:
                for enum_item in self.item.enum_list:
                    # parsed_value가 숫자 형태이므로 int로 비교
                    if str(enum_item.value) == parsed_value:
                        parsed_value = f"{parsed_value} ({enum_item.text})"
                        break

            self.lbl_read_value.setText(f"Val: {parsed_value}")
            self._set_error_state(is_error=False)

        except Exception as e:
            self._set_error_state(is_error=True)

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

    def _set_error_state(self, is_error: bool):
        if is_error:
            self.lbl_data_err.setStyleSheet("background-color: red; color: white; border-radius: 3px;")
        else:
            self.lbl_data_err.setStyleSheet("background-color: lightgray; color: black; border-radius: 3px;")