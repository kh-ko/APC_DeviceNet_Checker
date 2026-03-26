import qdarktheme

from PySide6.QtCore import QObject, QThread, Signal, Qt, Slot
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QDialog, QHBoxLayout, QTabWidget, QWidget, QVBoxLayout, QScrollArea, QFormLayout, QTableWidgetItem, QHeaderView, QDialogButtonBox

from app.model.dnet.dnet_model import CyclicItem, ExplicitItem, AccessType, DataType, UiType, EnumItem, BitmapItem

from app.ui.components.custom.custom_controls import CustomComboBox, CustomLineEdit, CustomPushButton, CustomCheckBox, CustomTableWidget, CustomLabel, CustomSpinBox, CustomDoubleSpinBox, CustomDialogButtonBox

from app.ui.network_dnet.item_widget import ItemWidget, ItemType

class EnumEditorWidget(QWidget):
    """Enum 아이템을 테이블 형태로 편집하는 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = CustomTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Value (숫자)", "Text (설명)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_add = CustomPushButton("항목 추가")
        self.btn_remove = CustomPushButton("선택 항목 삭제")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        layout.addLayout(btn_layout)
        
        self.btn_add.clicked.connect(lambda: self.add_row("", ""))
        self.btn_remove.clicked.connect(self.remove_row)

    def add_row(self, value, text):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(value)))
        self.table.setItem(row, 1, QTableWidgetItem(str(text)))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def load_data(self, enum_list):
        self.table.setRowCount(0)
        if enum_list:
            for item in enum_list:
                self.add_row(item.value, item.text)

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            val_item = self.table.item(row, 0)
            txt_item = self.table.item(row, 1)
            if val_item and txt_item:
                try:
                    val = int(val_item.text().strip())
                    txt = txt_item.text().strip()
                    data.append(EnumItem(value=val, text=txt))
                except ValueError:
                    pass  # 숫자가 아닌 경우 무시 (또는 경고 처리 가능)
        return data


class BitmapEditorWidget(QWidget):
    """Bitmap 아이템을 테이블 형태로 편집하는 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = CustomTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["Byte Name", "Bit 7", "Bit 6", "Bit 5", "Bit 4", "Bit 3", "Bit 2", "Bit 1", "Bit 0"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_add = CustomPushButton("Byte 추가")
        self.btn_remove = CustomPushButton("선택 Byte 삭제")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        layout.addLayout(btn_layout)
        
        self.btn_add.clicked.connect(lambda: self.add_row("", ["0"] * 8))
        self.btn_remove.clicked.connect(self.remove_row)

    def add_row(self, name, bits):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(name)))
        for i in range(8):
            bit_val = bits[i] if i < len(bits) else "0"
            cell_item = QTableWidgetItem(str(bit_val))
            cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, i + 1, cell_item)

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def load_data(self, bitmap_list):
        self.table.setRowCount(0)
        if bitmap_list:
            for item in bitmap_list:
                self.add_row(item.name, item.bits)

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            bits = []
            for i in range(8):
                bit_item = self.table.item(row, i + 1)
                bits.append(bit_item.text().strip() if bit_item else "0")
            data.append(BitmapItem(name=name, bits=bits))
        return data


class ItemEditDialog(QDialog):
    """
    BaseDnetItem 속성들을 편집하는 다이얼로그.
    Enum과 Bitmap 타입일 경우 전용 테이블 에디터가 나타납니다.
    """
    def __init__(self, item: ItemWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("아이템 편집")
        self.resize(700, 500)
        
        self.original_item : ItemWidget = item
        
        self._init_ui()
        
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.form_layout = QFormLayout()
        
        # 1. Name 입력
        self.name_input = CustomLineEdit()
        self.name_input.setText(self.original_item.name)
        self.form_layout.addRow("Name:", self.name_input)
        
        if self.original_item.item_type == ItemType.Explicit:
            # 2. Class, Instance, Attribute (CIP 주소 체계)
            self.class_id_spin = CustomSpinBox()
            self.class_id_spin.setRange(1, 65535)
            self.class_id_spin.setValue(self.original_item.class_id)
            self.form_layout.addRow("Class ID:", self.class_id_spin)

            self.instance_id_spin = CustomSpinBox()
            self.instance_id_spin.setRange(0, 65535)
            self.instance_id_spin.setValue(self.original_item.instance_id)
            self.form_layout.addRow("Instance ID:", self.instance_id_spin)

            self.attribute_id_spin = CustomSpinBox()
            self.attribute_id_spin.setRange(0, 255)
            self.attribute_id_spin.setValue(self.original_item.attribute_id)
            self.form_layout.addRow("Attribute ID:", self.attribute_id_spin)

            self.service_code_spin = CustomSpinBox()
            self.service_code_spin.setRange(0, 255)
            self.service_code_spin.setValue(self.original_item.service_code)
            self.form_layout.addRow("Service Code:", self.service_code_spin)
        
            # 3. Access Type
            self.access_combo = CustomComboBox()
            self.access_combo.addItems(["RO", "WO", "RW", "Exe"])
            self.access_combo.setCurrentText(self.original_item.access_type)
            self.access_combo.currentTextChanged.connect(self._update_access_type)
            self.form_layout.addRow("Access:", self.access_combo)

        # 4. Type 선택
        self.type_combo = CustomComboBox()
        if self.original_item.item_type == ItemType.Explicit:
            self.type_combo.addItems(["none", "uint8", "int8", "uint16", "int16", "uint32", "int32", "float", "bitmap"])
        elif self.original_item.item_type == ItemType.PollIn:
            self.type_combo.addItems(["uint8", "int8", "uint16", "int16", "uint32", "int32", "float", "bitmap"])
        elif self.original_item.item_type == ItemType.PollOut:
            self.type_combo.addItems(["uint8", "int8", "uint16", "int16", "uint32", "int32", "float"])

        type_str = self.original_item.type.lower()
        if self.type_combo.findText(type_str) >= 0:
            self.type_combo.setCurrentText(type_str)
        else:
            self.type_combo.setEditText(type_str)

        self.type_combo.setEditable(True)
        self.type_combo.currentTextChanged.connect(self._update_data_type)
        self.form_layout.addRow("Type:", self.type_combo)
        
        # 3. UI Type 선택
        self.ui_type_combo = CustomComboBox()
        if self.original_item.item_type == ItemType.Explicit:
            self.ui_type_combo.addItems(["action", "enum", "number", "real", "table"])
        elif self.original_item.item_type == ItemType.PollIn:
            self.ui_type_combo.addItems(["enum", "number", "real", "table"])
        elif self.original_item.item_type == ItemType.PollOut:
            self.ui_type_combo.addItems(["enum", "number", "real"])
        
        ui_type_str = self.original_item.ui_type.lower()
        if self.ui_type_combo.findText(ui_type_str) >= 0:
            self.ui_type_combo.setCurrentText(ui_type_str)
        else:
            self.ui_type_combo.setEditText(ui_type_str)
        self.ui_type_combo.setEditable(True)
        self.ui_type_combo.currentTextChanged.connect(self._update_ui_type)
        self.form_layout.addRow("UI Type:", self.ui_type_combo)
        
        self.layout.addLayout(self.form_layout)
        
        # 4. Enum 편집기
        self.enum_label = CustomLabel("<b>Enum 설정</b>")
        self.enum_editor = EnumEditorWidget()
        self.enum_editor.load_data(self.original_item.enum_list)
        self.layout.addWidget(self.enum_label)
        self.layout.addWidget(self.enum_editor)
        
        # 5. Bitmap 편집기
        self.bitmap_label = CustomLabel("<b>Bitmap 설정</b>")
        self.bitmap_editor = BitmapEditorWidget()
        self.bitmap_editor.load_data(self.original_item.bitmap)
        self.layout.addWidget(self.bitmap_label)
        self.layout.addWidget(self.bitmap_editor)
        
        # 6. 하단 확인/취소 버튼
        self.button_box = CustomDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self._update_access_type()      
            

    def _update_visibility_enum_bitmap(self):
        """선택된 Type과 UI Type에 따라 하단 에디터를 표시/숨김 처리합니다."""
        
        current_type = self.type_combo.currentText().strip().lower()
        current_ui_type = self.ui_type_combo.currentText().strip().lower()

        # 하단 에디터 표시/숨김 업데이트 (현재 갱신된 값 기준)
        is_enum = (current_ui_type == "enum")
        is_bitmap = (current_type == "bitmap")
        
        self.enum_label.setVisible(is_enum)
        self.enum_editor.setVisible(is_enum)
        
        self.bitmap_label.setVisible(is_bitmap)
        self.bitmap_editor.setVisible(is_bitmap)

        # 상태 업데이트 완료 후 시그널 차단 해제
        self.type_combo.blockSignals(False)
        self.ui_type_combo.blockSignals(False)

    def accept(self):
        """확인 버튼 클릭 시 Enum Value들의 숫자 변환 여부 등 검증"""
        if self.ui_type_combo.currentText().strip().lower() == "enum":
            for row in range(self.enum_editor.table.rowCount()):
                val_item = self.enum_editor.table.item(row, 0)
                if val_item:
                    try:
                        int(val_item.text().strip())
                    except ValueError:
                        QMessageBox.warning(self, "입력 오류", f"{row+1}번째 Enum 항목의 Value는 숫자여야 합니다.")
                        return

        self.original_item.name = self.name_input.text().strip()
        self.original_item.type = DataType(self.type_combo.currentText().strip())
        self.original_item.ui_type = UiType(self.ui_type_combo.currentText().strip())
        self.original_item.enum_list = self.enum_editor.get_data()
        self.original_item.bitmap = self.bitmap_editor.get_data()

        if self.original_item.item_type == ItemType.Explicit:
            self.original_item.service_code = self.service_code_spin.value()
            self.original_item.class_id     = self.class_id_spin.value()
            self.original_item.instance_id  = self.instance_id_spin.value()
            self.original_item.attribute_id = self.attribute_id_spin.value()
            self.original_item.access_type  = AccessType(self.access_combo.currentText().strip())

        self.original_item.refresh_ui()
        super().accept()

    def get_updated_data(self) -> dict:
        """
        사용자가 입력한 데이터를 dict 형태로 반환합니다.
        """
        updated = {
            "name": self.name_input.text().strip(),
            "type": self.type_combo.currentText().strip(),
            "ui_type": self.ui_type_combo.currentText().strip(),
        }
        
        if self.ui_type_combo.currentText().strip().lower() == "enum":
            updated["enum_list"] = self.enum_editor.get_data()
            
        if self.type_combo.currentText().strip().lower() == "bitmap":
            updated["bitmap"] = self.bitmap_editor.get_data()
                
        return updated

    def _update_access_type(self):
        """Access Type에 따라 데이터 타입과 UI 타입을 제한합니다."""
        if not hasattr(self, 'access_combo'): 
            self._update_data_type()
            return
        
        self.type_combo.blockSignals(True)
        self.ui_type_combo.blockSignals(True)
        
        access_type = self.access_combo.currentText().strip().lower()

        # 콤보박스 아이템 활성화/비활성화 헬퍼 함수
        def set_type_only(allowed_list):
            for i in range(self.type_combo.count()):
                text = self.type_combo.itemText(i).lower()
                item = self.type_combo.model().item(i)
                if item: item.setEnabled(text in allowed_list)

        if access_type == "exe":
            set_type_only(["none"])
            self.type_combo.setCurrentText("none")
        elif access_type in ("ro", "rw"):
            set_type_only(["uint8", "int8", "uint16", "int16", "uint32", "int32", "float", "bitmap"])
            if self.type_combo.currentText().lower() in ("none"):
                self.type_combo.setCurrentText("uint8")
        elif access_type == "wo":
            set_type_only(["uint8", "int8", "uint16", "int16", "uint32", "int32", "float"])
            if self.type_combo.currentText().lower() in ("none", "bitmap"):
                self.type_combo.setCurrentText("uint8")

        self.type_combo.blockSignals(False)
        self.ui_type_combo.blockSignals(False)

        self._update_data_type()


    def _update_data_type(self):
        """데이터 타입(Type) 변경 시 UI 타입을 강제하거나 제한합니다."""
        self.type_combo.blockSignals(True)
        self.ui_type_combo.blockSignals(True)
        
        current_type = self.type_combo.currentText().strip().lower()

        # UI Type 전체 활성화 후 조건에 따라 비활성화
        def set_ui_only(allowed_list):
            for i in range(self.ui_type_combo.count()):
                text = self.ui_type_combo.itemText(i).lower()
                item = self.ui_type_combo.model().item(i)
                if item: item.setEnabled(text in allowed_list)

        if current_type == "none":
            set_ui_only(["action"])
            self.ui_type_combo.setCurrentText("action")
        elif current_type == "float":
            set_ui_only(["real"])
            self.ui_type_combo.setCurrentText("real")
        elif current_type == "bitmap":
            set_ui_only(["table"])
            self.ui_type_combo.setCurrentText("table")
        elif current_type in ("uint8", "int8", "uint16", "int16", "uint32", "int32"):
            set_ui_only(["number", "enum"])
            if self.ui_type_combo.currentText().lower() not in ("number", "enum"):
                self.ui_type_combo.setCurrentText("number")
        else:
            set_ui_only(["action", "enum", "number", "real", "table"])

        self._update_visibility_enum_bitmap()
        self.type_combo.blockSignals(False)
        self.ui_type_combo.blockSignals(False)

    def _update_ui_type(self):
        """UI 타입 변경 시 하단 편집기 노출 여부만 업데이트합니다."""
        self._update_visibility_enum_bitmap()
