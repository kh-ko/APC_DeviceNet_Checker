from app.ui.components.composit.console_widget import MsgType
import sys
import qdarktheme
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QDialog
from PySide6.QtCore import Qt, QThread, QMetaObject
from PySide6.QtGui import QCloseEvent

from app.model.global_define import NetworkType

from app.network_service.dnet_i7565dnm_svc import DnetI7565DNMSvc

from app.ui.components.composit.console_widget import ConsoleWidget
from app.ui.components.composit.custom_toolbar import CustomToolBar
from app.ui.network_view import NetworkView
from app.ui.network_dnet.dnet_view import DnetView
from app.ui.dialog.network_select_dialog import NetworkSelectDialog


class HomeWin(QMainWindow):
    def __init__(self):
        super().__init__()

        self.dnet_svc = DnetI7565DNMSvc()

        self.dnet_thread = QThread()
        self.dnet_svc.moveToThread(self.dnet_thread)
        
        # 윈도우 기본 설정
        self.setWindowTitle("User Interface Checker")
        self.resize(1920, 1080)
        
        toolbar = CustomToolBar(self)
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
        self.console.add_message(MsgType.INFO, "[HomeWin][on_connect_clicked]")

        dialog = NetworkSelectDialog(self)
        
        # 다이얼로그를 실행하고, 사용자가 '연결하기(Ok)'를 눌렀는지 확인
        if dialog.exec() == QDialog.Accepted:
            self.console.add_message(MsgType.INFO, f"[HomeWin][on_connect_clicked] {NetworkType.DNET.value} 선택됨")

            # 다이얼로그에서 데이터 가져오기
            conn_info = dialog.get_connection_info()
            
            if self.curr_network_view:
                self.curr_network_view.shutdown()
                self.left_layout.removeWidget(self.curr_network_view)
                self.curr_network_view.deleteLater()
            
            new_network_view = None

            if conn_info["Network"] == NetworkType.DNET.value:
                new_network_view = DnetView(self)
            
            self.curr_network_view = new_network_view

            if self.curr_network_view:
                self.curr_network_view.sig_add_log.connect(self.console.add_message)
                self.left_layout.addWidget(self.curr_network_view)
                self.curr_network_view.connect_network(conn_info)

    def on_new_clicked(self):
        self.console.add_message(MsgType.INFO, "[HomeWin][on_new_clicked]")
        if self.curr_network_view:
            self.curr_network_view.create_new_schema()

    def on_load_clicked(self):
        self.console.add_message(MsgType.INFO, "[HomeWin][on_load_clicked]")
        if self.curr_network_view:
            self.curr_network_view.open_select_schema()

    def on_save_clicked(self):
        self.console.add_message(MsgType.INFO, "[HomeWin][on_save_clicked]")
        if self.curr_network_view:
            self.curr_network_view.save_schema()

    def on_save_as_clicked(self):
        self.console.add_message(MsgType.INFO, "[HomeWin][on_save_as_clicked]")
        if self.curr_network_view:
            self.curr_network_view.save_as_schema()

    def on_remove_clicked(self):
        self.console.add_message(MsgType.INFO, "[HomeWin][on_remove_clicked]")
        if self.curr_network_view:
            self.curr_network_view.remove_schema()

    def closeEvent(self, event: QCloseEvent):
        """프로그램 종료 시 스레드와 하드웨어 자원을 안전하게 해제합니다."""
        
        # 스레드가 생성되어 있고, 현재 실행 중인지 확인
        if hasattr(self, 'dnet_thread') and self.dnet_thread.isRunning():
            
            # 1. 워커 스레드 컨텍스트에서 disconnect_module 실행 (매우 중요)
            # BlockingQueuedConnection을 사용하면 워커 스레드에서 정리가 끝날 때까지 메인 스레드가 잠시 대기합니다.
            QMetaObject.invokeMethod(self.dnet_svc, "disconnect_module", Qt.BlockingQueuedConnection)
            
            # 2. 워커 스레드의 이벤트 루프 종료 요청
            self.dnet_thread.quit()
            
            # 3. 스레드가 완전히 종료될 때까지 대기 (최대 3초)
            # 3000ms 동안 기다려보고, 그래도 안 끝나면 강제 진행하여 앱이 무한 대기(프리징)하는 것을 방지합니다.
            self.dnet_thread.wait(3000)
        
        # 정상적으로 창 닫기 이벤트 수락
        event.accept()