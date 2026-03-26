import sys
import qdarktheme
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QDialog
from PySide6.QtCore import Qt

from app.ui.components.composit.console_widget import ConsoleWidget
from app.ui.components.composit.custom_toolbar import CustomToolBar
from app.ui.network_view import NetworkView
from app.ui.network_dnet.dnet_view import DnetView
from app.ui.network_select_dialog import NetworkSelectDialog


class HomeWin(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 윈도우 기본 설정
        self.setWindowTitle("User Interface Checker")
        self.resize(1920, 1080)
        
        toolbar = CustomToolBar("메인 툴바", self)
        toolbar.set_connect_handler(self.on_connect_clicked)
        toolbar.set_new_handler(self.on_new_clicked)
        toolbar.set_load_handler(self.on_load_clicked)
        toolbar.set_save_handler(self.on_save_clicked)
        toolbar.set_save_as_handler(self.on_save_as_clicked)
        toolbar.set_remove_handler(self.on_remove_clicked)
        self.addToolBar(toolbar) # 기본적으로 윈도우 상단에 배치됩니다.

        self.setup_body()

        self.curr_network_view : NetworkView = None

    def closeEvent(self, event):
        if self.curr_network_view:
            self.curr_network_view.shutdown()
            
        super().closeEvent(event)

    def setup_body(self):
        # 중앙 위젯 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        
        # 스플리터 생성 (좌/우 분할)
        self.splitter = QSplitter(Qt.Horizontal)
        
        # [왼쪽] 프로토콜/스키마 레이아웃 영역
        self.left_pane = QWidget()
        self.left_pane.setObjectName("LeftPane")
        self.left_layout = QVBoxLayout(self.left_pane)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        # placeholder 등 나중에 추가 가능
        
        # [오른쪽] 실시간 로그 콘솔 영역
        self.console = ConsoleWidget()
        
        # 스플리터에 위젯 추가
        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.console)
        
        # 좌우 비율 설정 (7:3)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        # 최초 로딩 시 왼쪽이 비어있으면 0으로 수축하는 것을 방지하기 위해 강제로 사이즈 지정
        self.splitter.setSizes([1400, 600])
        
        main_layout.addWidget(self.splitter)


    # --- 아래는 버튼 클릭 시 실행될 임시 함수(Slot)들입니다 ---
    def on_connect_clicked(self):
        dialog = NetworkSelectDialog(self)
        
        # 다이얼로그를 실행하고, 사용자가 '연결하기(Ok)'를 눌렀는지 확인
        if dialog.exec() == QDialog.Accepted:
            # 다이얼로그에서 데이터 가져오기
            conn_info = dialog.get_connection_info()
            
            new_network_view = None

            if conn_info["Network"] == "Device Net":
                new_network_view = DnetView(self)
            
            if self.curr_network_view:
                self.curr_network_view.shutdown()
                self.left_layout.removeWidget(self.curr_network_view)

            self.curr_network_view = new_network_view

            if self.curr_network_view:
                self.left_layout.addWidget(self.curr_network_view)

    def on_new_clicked(self):
        if self.curr_network_view:
            self.curr_network_view.create_new_schema()

    def on_load_clicked(self):
        if self.curr_network_view:
            self.curr_network_view.open_select_schema()

    def on_save_clicked(self):
        if self.curr_network_view:
            self.curr_network_view.save_schema()

    def on_save_as_clicked(self):
        if self.curr_network_view:
            self.curr_network_view.save_as_schema()

    def on_remove_clicked(self):
        if self.curr_network_view:
            self.curr_network_view.remove_schema()