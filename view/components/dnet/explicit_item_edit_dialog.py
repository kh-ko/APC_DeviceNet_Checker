from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QDialogButtonBox, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QPushButton, QWidget, QHeaderView, QSpinBox
)
from PySide6.QtCore import Qt
from model.dnet.dnet_item_model import ExplicitItem

class EnumEditorWidget(QWidget):
    """Enum 아이템을 테이블 형태로 편집하는 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Value (숫자)", "Text (설명)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("항목 추가")
        self.btn_remove = QPushButton("선택 항목 삭제")
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
                    data.append({"value": val, "text": txt})
                except ValueError:
                    pass
        return data


class BitmapEditorWidget(QWidget):
    """Bitmap 아이템을 테이블 형태로 편집하는 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["Byte Name", "Bit 7", "Bit 6", "Bit 5", "Bit 4", "Bit 3", "Bit 2", "Bit 1", "Bit 0"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Byte 추가")
        self.btn_remove = QPushButton("선택 Byte 삭제")
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
            data.append({"name": name, "bits": bits})
        return data


class ExplicitItemEditDialog(QDialog):
    """
    ExplicitItem 속성들을 편집하는 다이얼로그.
    Class, Instance, Attribute ID 설정과 Enum/Bitmap 타입 편집을 지원합니다.
    """
    def __init__(self, item: ExplicitItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Explicit 아이템 편집")
        self.resize(700, 600)
        
        self.original_item = item
        
        self._init_ui()
        self._load_data()
        
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        
        # 1. Name 입력
        self.name_input = QLineEdit()
        self.form_layout.addRow("Name:", self.name_input)

        # 2. Class, Instance, Attribute (CIP 주소 체계)
        self.class_id_spin = QSpinBox()
        self.class_id_spin.setRange(1, 65535)
        self.form_layout.addRow("Class ID:", self.class_id_spin)

        self.instance_id_spin = QSpinBox()
        self.instance_id_spin.setRange(0, 65535)
        self.form_layout.addRow("Instance ID:", self.instance_id_spin)

        self.attribute_id_spin = QSpinBox()
        self.attribute_id_spin.setRange(0, 255)
        self.form_layout.addRow("Attribute ID:", self.attribute_id_spin)
        
        # 3. Access Type
        self.access_combo = QComboBox()
        self.access_combo.addItems(["RO", "WO", "RW", "Exe"])
        self.access_combo.currentTextChanged.connect(self._update_visibility)
        self.form_layout.addRow("Access:", self.access_combo)

        # 4. Type 선택
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "none", "uint8", "int8", "uint16", "int16", 
            "uint32", "int32", "float", "bitmap"
        ])
        self.type_combo.setEditable(True)
        self.type_combo.currentTextChanged.connect(self._update_visibility)
        self.form_layout.addRow("Type:", self.type_combo)
        
        # 5. UI Type 선택
        self.ui_type_combo = QComboBox()
        self.ui_type_combo.addItems([
            "action", "enum", "number", "real", "table"
        ])
        self.ui_type_combo.setEditable(True)
        self.ui_type_combo.currentTextChanged.connect(self._update_visibility)
        self.form_layout.addRow("UI Type:", self.ui_type_combo)
        
        self.layout.addLayout(self.form_layout)
        
        # 6. Enum 편집기
        self.enum_label = QLabel("<b>Enum 설정</b>")
        self.enum_editor = EnumEditorWidget()
        self.layout.addWidget(self.enum_label)
        self.layout.addWidget(self.enum_editor)
        
        # 7. Bitmap 편집기
        self.bitmap_label = QLabel("<b>Bitmap 설정</b>")
        self.bitmap_editor = BitmapEditorWidget()
        self.layout.addWidget(self.bitmap_label)
        self.layout.addWidget(self.bitmap_editor)
        
        # 8. 하단 확인/취소 버튼
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
    def _load_data(self):
        """기존 item의 데이터를 UI에 채웁니다."""
        self.name_input.setText(self.original_item.name)
        self.class_id_spin.setValue(self.original_item.class_id)
        self.instance_id_spin.setValue(self.original_item.instance_id)
        self.attribute_id_spin.setValue(self.original_item.attribute_id)

        # Access Type 세팅
        acc_str = self.original_item.access_type
        if self.access_combo.findText(acc_str, Qt.MatchFlag.MatchFixedString) >= 0:
            self.access_combo.setCurrentText(acc_str)
        
        # Type 세팅
        type_str = self.original_item.type.lower()
        if self.type_combo.findText(type_str) >= 0:
            self.type_combo.setCurrentText(type_str)
        else:
            self.type_combo.setEditText(type_str)
            
        # UI Type 세팅
        ui_type_str = self.original_item.ui_type.lower()
        if self.ui_type_combo.findText(ui_type_str) >= 0:
            self.ui_type_combo.setCurrentText(ui_type_str)
        else:
            self.ui_type_combo.setEditText(ui_type_str)
            
        # Enum / Bitmap 에디터 데이터 로드
        self.enum_editor.load_data(self.original_item.enum_list)
        self.bitmap_editor.load_data(self.original_item.bitmap)
        
        self._update_visibility()

    def _update_visibility(self):
        """선택된 Type과 UI Type, Access에 따라 하단 에디터를 표시/숨김 처리합니다."""
        self.access_combo.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.ui_type_combo.blockSignals(True)
        
        current_acc = self.access_combo.currentText().strip()
        current_type = self.type_combo.currentText().strip().lower()
        current_ui_type = self.ui_type_combo.currentText().strip().lower()
        
        # Access가 Exe이면 데이터가 필요 없으므로 none / action으로 강제 매핑
        if current_acc == "Exe":
            self.type_combo.setCurrentText("none")
            self.ui_type_combo.setCurrentText("action")
            current_type = "none"
            current_ui_type = "action"

        # type이 bitmap일 때는 ui_type을 table로 강제
        if current_type == "bitmap":
            self.ui_type_combo.setCurrentText("table")
            current_ui_type = "table"
            
        # type이 bitmap이 아닌데 ui_type이 table로 되어있다면 보정
        elif current_type != "bitmap" and current_ui_type == "table":
            self.type_combo.setCurrentText("uint8")
            self.ui_type_combo.setCurrentText("number")
            current_type = "uint8"
            current_ui_type = "number"

        # 하단 에디터 표시/숨김 업데이트
        is_enum = (current_ui_type == "enum")
        is_bitmap = (current_type == "bitmap")
        
        self.enum_label.setVisible(is_enum)
        self.enum_editor.setVisible(is_enum)
        
        self.bitmap_label.setVisible(is_bitmap)
        self.bitmap_editor.setVisible(is_bitmap)

        self.access_combo.blockSignals(False)
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
                        
        super().accept()

    def get_updated_data(self) -> dict:
        """사용자가 입력한 데이터를 dict 형태로 반환합니다."""
        updated = {
            "name": self.name_input.text().strip(),
            "class_id": self.class_id_spin.value(),
            "instance_id": self.instance_id_spin.value(),
            "attribute_id": self.attribute_id_spin.value(),
            "access_type": self.access_combo.currentText().strip(),
            "type": self.type_combo.currentText().strip(),
            "ui_type": self.ui_type_combo.currentText().strip(),
        }
        
        if self.ui_type_combo.currentText().strip().lower() == "enum":
            updated["enum_list"] = self.enum_editor.get_data()
            
        if self.type_combo.currentText().strip().lower() == "bitmap":
            updated["bitmap"] = self.bitmap_editor.get_data()
                
        return updated