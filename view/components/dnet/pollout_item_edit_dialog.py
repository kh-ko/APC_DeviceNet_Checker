from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QDialogButtonBox, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QPushButton, QWidget, QHeaderView
)
from PySide6.QtCore import Qt
from model.dnet.dnet_item_model import BaseDnetItem

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
                    pass  # 숫자가 아닌 경우 무시 (또는 경고 처리 가능)
        return data

class PollOutItemEditDialog(QDialog):
    """
    BaseDnetItem 속성들을 편집하는 다이얼로그.
    Enum과 Bitmap 타입일 경우 전용 테이블 에디터가 나타납니다.
    """
    def __init__(self, item: BaseDnetItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle("아이템 편집")
        self.resize(700, 500)
        
        self.original_item = item
        
        self._init_ui()
        self._load_data()
        
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.form_layout = QFormLayout()
        
        # 1. Name 입력
        self.name_input = QLineEdit()
        self.form_layout.addRow("Name:", self.name_input)
        
        # 2. Type 선택
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "uint8", "int8",  
            "uint16", "int16",
            "uint32", "int32",
            "float"
        ])
        self.type_combo.setEditable(True)
        self.type_combo.currentTextChanged.connect(self._update_visibility)
        self.form_layout.addRow("Type:", self.type_combo)
        
        # 3. UI Type 선택
        self.ui_type_combo = QComboBox()
        self.ui_type_combo.addItems([
            "enum", "number", "real"
        ])
        self.ui_type_combo.setEditable(True)
        self.ui_type_combo.currentTextChanged.connect(self._update_visibility)
        self.form_layout.addRow("UI Type:", self.ui_type_combo)
        
        self.layout.addLayout(self.form_layout)
        
        # 4. Enum 편집기
        self.enum_label = QLabel("<b>Enum 설정</b>")
        self.enum_editor = EnumEditorWidget()
        self.layout.addWidget(self.enum_label)
        self.layout.addWidget(self.enum_editor)
        
        # 5. 하단 확인/취소 버튼
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
    def _load_data(self):
        """기존 item의 데이터를 UI에 채웁니다."""
        self.name_input.setText(self.original_item.name)
        
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
        
        self._update_visibility()

    def _update_visibility(self):
        """선택된 Type과 UI Type에 따라 하단 에디터를 표시/숨김 처리합니다."""
        self.type_combo.blockSignals(True)
        self.ui_type_combo.blockSignals(True)
        
        current_ui_type = self.ui_type_combo.currentText().strip().lower()

        # 하단 에디터 표시/숨김 업데이트 (현재 갱신된 값 기준)
        is_enum = (current_ui_type == "enum")
        
        self.enum_label.setVisible(is_enum)
        self.enum_editor.setVisible(is_enum)

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
                            
        return updated