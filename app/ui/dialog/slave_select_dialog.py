import qdarktheme

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QHBoxLayout, QListWidgetItem)
from PySide6.QtCore import Qt

from app.ui.components.custom.custom_controls import CustomLabel, CustomPushButton 


class SlaveSelectDialog(QDialog):
    def __init__(self, found_devices, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Slave 리스트")
        self.resize(400, 300)
        
        self.selected_device_info = None
        
        # UI 구성
        layout = QVBoxLayout(self)        
        self.device_list = QListWidget(self)
        layout.addWidget(self.device_list)
        
        btn_layout = QHBoxLayout()
        self.connect_btn = CustomPushButton("이 장치와 연결", self)
        self.connect_btn.setEnabled(False) # 선택 전에는 비활성화
        self.cancel_btn = CustomPushButton("취소", self)
        
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        poll_devices = [dev for dev in found_devices if dev["type"] == 1]
        for dev in poll_devices:
            mac_id = dev["mac_id"]
            dev_type = dev["type"]
            in_len = dev["in_len"]
            out_len = dev["out_len"]
            
            # 리스트 아이템 생성 및 MAC ID 데이터 심기
            list_text = f"MAC ID: {mac_id} (Type: {dev_type}, In: {in_len}B, Out: {out_len}B)"
            item = QListWidgetItem(list_text)
            item.setData(Qt.UserRole, (mac_id, in_len, out_len))
            self.device_list.addItem(item)

        
        # 시그널 연결 (버튼 이벤트)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        self.device_list.itemSelectionChanged.connect(self.on_selection_changed)        
        

    def on_selection_changed(self):
        # 아이템 클릭 시 '연결' 버튼 활성화
        if self.device_list.selectedItems():
            self.connect_btn.setEnabled(True)
        else:
            self.connect_btn.setEnabled(False)
            
    def on_connect_clicked(self):
        selected = self.device_list.selectedItems()
        if selected:
            # 선택된 아이템의 MAC ID 가져오기
            self.selected_device_info = selected[0].data(Qt.UserRole)
            self.accept() # 다이얼로그 성공적으로 닫기
