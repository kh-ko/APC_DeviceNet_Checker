import os
import sys

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, 
                               QPushButton, QHBoxLayout, QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt, Signal

from utils.file_path import get_app_path

import qdarktheme

from app.file_helper.file_helper import get_dnet_schema_path
from app.model.global_define import NetworkType

from app.ui.components.custom.custom_controls import CustomLabel, CustomPushButton

class SchemaSelectDialog(QDialog):
    def __init__(self, network : NetworkType, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schema 파일 선택")
        self.resize(400, 300)
        
        self.selected_schema = None
        
        # UI 구성
        layout = QVBoxLayout(self)
        
        self.status_label = CustomLabel("Schema 파일을 선택하세요.", self)
        layout.addWidget(self.status_label)
        
        self.schema_list = QListWidget(self)
        layout.addWidget(self.schema_list)
        
        btn_layout = QHBoxLayout()
        self.select_btn = CustomPushButton("선택", self)
        self.select_btn.setEnabled(False)
        self.cancel_btn = CustomPushButton("취소", self)
        
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 시그널 연결
        self.select_btn.clicked.connect(self.on_select_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        self.schema_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Schema 파일 목록 로드
        self.load_schemas(network)
        
    def load_schemas(self, network : NetworkType):
        schema_dir = ""
        
        if network == NetworkType.DNET.value:
            schema_dir = get_dnet_schema_path()
        else:
            return
        # 실행 위치에서 schema/dnet 폴더의 파일 목록을 가져와서 리스트에 추가
        if os.path.exists(schema_dir):
            for filename in os.listdir(schema_dir):
                if filename.endswith(".json"):
                    item = QListWidgetItem(filename)
                    # 윈도우 환경 역슬래시 치환
                    schema_path = os.path.join(schema_dir, filename).replace("\\", "/")
                    item.setData(Qt.UserRole, schema_path)
                    self.schema_list.addItem(item)
        else:
            print(f"[Warning] 스키마 폴더를 찾을 수 없습니다: {schema_dir}")
    
    def on_selection_changed(self):
        if self.schema_list.selectedItems():
            self.select_btn.setEnabled(True)
        else:
            self.select_btn.setEnabled(False)
    
    def on_select_clicked(self):
        selected = self.schema_list.selectedItems()
        if selected:
            print(selected[0].data(Qt.UserRole))
            self.selected_schema = selected[0].data(Qt.UserRole)
            self.accept()
    
    def closeEvent(self, event):
        self.reject()
        super().closeEvent(event)