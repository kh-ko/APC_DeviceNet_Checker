from log_manager.console_widget import ConsoleWidget
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QStatusBar, QSplitter, QTabWidget, QWidget, QVBoxLayout, QLabel, QTextEdit, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
import qdarktheme

from log_manager.console_widget import ConsoleWidget
from main_controller import MainController
from protocol_model import DeviceConfig
from custom_component.pollin_group_widget import PollInListWidget

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 윈도우 기본 설정
        self.setWindowTitle("DeviceNet Checker")
        self.resize(1920, 1080)
        
        self.init_ui()
        
        self.main_controller = MainController(self)
        self.init_connect_signals()

        self.main_controller.refresh_ports()

    def init_ui(self):
        # ==========================================
        # 1. 상단 툴바 (Toolbar) 구성
        # ==========================================
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False) 
        self.addToolBar(toolbar)
        
        # COM 포트 선택을 위한 ComboBox 추가
        self.comport_combo = QComboBox()
        #self.comport_combo.addItems(["COM1", "COM2", "COM3", "COM4"])
        self.comport_combo.setMinimumWidth(100) 
        
        # 툴바에 위젯 추가
        toolbar.addWidget(self.comport_combo)
        toolbar.addSeparator()

        # 액션(버튼) 생성
        self.action_com_refresh = QAction("COM 새로고침", self)
        self.action_connect = QAction("I7565DNM 연결", self)
        self.action_disconnect = QAction("I7565DNM 연결끊기", self)
        self.action_slave_search = QAction("Slave 검색", self)

        # 툴바에 액션 추가
        toolbar.addAction(self.action_com_refresh)
        toolbar.addAction(self.action_connect)
        toolbar.addAction(self.action_disconnect)
        toolbar.addAction(self.action_slave_search)

        # ==========================================
        # 2. 하단 상태 표시줄 (Status Bar) 구성
        # ==========================================
        self.statusBar().showMessage("포트를 검색하고 연결을 준비해 주세요.")

        # ==========================================
        # 3. 중앙 영역 (상하 Splitter) 구성
        # ==========================================
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Splitter 상단: Tab UI 구성 ---
        tab_widget = QTabWidget()
        
        # 첫 번째 탭 (Poll)
        self.tab_poll = QWidget()
        self.layout_poll = QVBoxLayout(self.tab_poll)
        # 두 번째 탭 (Explicit)
        self.tab_explicit = QWidget()
        self.layout_explicit = QVBoxLayout(self.tab_explicit) # 멤버 변수로 저장
        
        tab_widget.addTab(self.tab_poll, "Poll")
        tab_widget.addTab(self.tab_explicit, "Explicit")

        # --- Splitter 하단: 로그 뷰어 용도 구성 ---
        self.log_widget = ConsoleWidget(self)

        # Splitter에 상단(Tab)과 하단 위젯 추가
        main_splitter.addWidget(tab_widget)
        main_splitter.addWidget(self.log_widget)
        
        main_splitter.setSizes([360, 240])
        self.setCentralWidget(main_splitter)

    def init_connect_signals(self):
        self.action_com_refresh.triggered.connect(self.main_controller.refresh_ports)
        self.action_connect.triggered.connect(self.main_controller.connect_device)
        self.action_disconnect.triggered.connect(self.main_controller.disconnect_device)
        self.action_slave_search.triggered.connect(self.main_controller.search_devices)

    def build_contents(self, device_config: DeviceConfig):
        """DeviceConfig 모델을 받아서 동적으로 UI를 구성합니다."""
        
        # 1. 기존 레이아웃 초기화 (다른 설정 로드 시 기존 UI 제거)
        while self.layout_poll.count():
            child = self.layout_poll.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        while self.layout_explicit.count():
            child = self.layout_explicit.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 2. Poll 탭 구성 (상: Poll-Out / 하: Poll-In 분할)
        poll_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        #poll_out_panel = PollOutWidget(device_config.poll_out)
        poll_in_panel = PollInListWidget(device_config.poll_in)
        
        #poll_splitter.addWidget(poll_out_panel)
        poll_splitter.addWidget(poll_in_panel)
        # 상하 1:1 비율로 초기 설정
        poll_splitter.setSizes([400, 400]) 
        
        self.layout_poll.addWidget(poll_splitter)

        # 3. Explicit 탭 구성
        #explicit_panel = ExplicitWidget(device_config.explicit_messages)
        #self.layout_explicit.addWidget(explicit_panel)

    def closeEvent(self, event: QCloseEvent):
        """창의 X 버튼을 누르거나 프로그램이 종료될 때 실행됩니다."""
        print("종료")
        # MainController의 안전 종료 메서드 호출
        if hasattr(self, 'main_controller'):
            self.main_controller.shutdown()
            
        # 정상적으로 창 닫기 이벤트 승인
        event.accept()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 변경된 부분: "light" 테마 적용
    qdarktheme.setup_theme("light")
    
    window = MyWindow()
    window.show()
    
    sys.exit(app.exec())