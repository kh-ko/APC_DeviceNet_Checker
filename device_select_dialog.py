from PySide6.QtWidgets import QDialog, QListWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class DeviceSelectDialog(QDialog):
    def __init__(self, devices, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Slave 장치 선택")
        self.resize(350, 300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("통신할 Slave 장치를 선택하세요:"))
        
        # 리스트 위젯 생성
        self.list_widget = QListWidget()
        for dev in devices:
            item_text = (f"MAC ID: {dev['mac']:02d} "
                         f"(Type: 0x{dev['type']:02X}, In:{dev['in_len']}, Out:{dev['out_len']})")
            self.list_widget.addItem(item_text)
            
            # 리스트 아이템에 MAC ID 데이터를 숨겨서 저장 (나중에 꺼내쓰기 위함)
            self.list_widget.item(self.list_widget.count()-1).setData(Qt.ItemDataRole.UserRole, dev['mac'])
            
        layout.addWidget(self.list_widget)
        
        # 버튼 레이아웃
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("선택")
        self.cancel_btn = QPushButton("취소")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 이벤트 연결
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.list_widget.itemDoubleClicked.connect(self.accept) # 더블클릭해도 선택되도록

    def get_selected_mac(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.ItemDataRole.UserRole)
        return None