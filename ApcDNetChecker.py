import ctypes
import os
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QToolBar, QWidget, 
                               QVBoxLayout, QLabel, QStatusBar)
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtCore import Qt
import qdarktheme

# 로그 매니저 가져오기
from log_manager.log_manager import LogManager
from log_manager.console_widget import MsgType

class DNetMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APC DeviceNet Checker")
        self.resize(1000, 800)
        
        # 로그 매니저 초기화
        self.log_manager = LogManager()
        self.log_manager.log("애플리케이션 시작됨", MsgType.INFO)

        # UI 구성
        self._init_ui()
        self._init_toolbar()
        
        # DLL 로드 시 시도
        self._load_dll()

    def _init_ui(self):
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.status_label = QLabel("준비")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Malgun Gothic", 12))
        layout.addWidget(self.status_label)
        
        # 상태바 추가
        self.setStatusBar(QStatusBar(self))

    def _init_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # 연결 액션
        self.connect_action = QAction("연결", self)
        # self.connect_action.setIcon(QIcon.fromTheme("network-connect")) # 테마 아이콘이 없을 수 있음
        self.connect_action.triggered.connect(self.connect_device)
        self.toolbar.addAction(self.connect_action)

        self.toolbar.addSeparator()

        # 로그보기 액션
        self.log_action = QAction("로그보기", self)
        self.log_action.triggered.connect(self.show_log)
        self.toolbar.addAction(self.log_action)

    def _load_dll(self):
        # 1. DLL 파일 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(current_dir, "x64", "I7565DNM.dll")
        
        try:
            self.log_manager.log(f"DLL 로딩 중... ({dll_path})", MsgType.INFO)
            self.dnm_lib = ctypes.WinDLL(dll_path)
            self.log_manager.log("DLL 로드 성공!", MsgType.INFO)
            
            # C언어 함수 형태 정의
            self.dnm_lib.I7565DNM_ActiveModule.argtypes = [ctypes.c_uint8]
            self.dnm_lib.I7565DNM_ActiveModule.restype = ctypes.c_uint32
            
        except OSError as e:
            error_msg = f"DLL 로드 실패. 파일 경로 확인 필요.\n에러: {e}"
            self.log_manager.log(error_msg, MsgType.ERROR)
            self.status_label.setText("DLL 로드 실패")
            self.dnm_lib = None

    def connect_device(self):
        if not self.dnm_lib:
            self.log_manager.log("DLL이 로드되지 않아 연결할 수 없습니다.", MsgType.ERROR)
            return

        PORT_NUMBER = 1 
        self.log_manager.log(f"포트 {PORT_NUMBER}번 DeviceNet 마스터 활성화 시도 중...", MsgType.INFO)
        
        # DLL 함수 호출
        result = self.dnm_lib.I7565DNM_ActiveModule(PORT_NUMBER)
        
        if result == 0:
            self.log_manager.log("=> [성공] I-7565-DNM 모듈이 활성화되었습니다!", MsgType.INFO)
            self.status_label.setText(f"포트 {PORT_NUMBER} 연결됨")
        else:
            self.log_manager.log(f"=> [실패] 모듈 활성화 에러. 에러 코드: {result}", MsgType.ERROR)
            self.status_label.setText(f"연결 실패 (코드: {result})")

    def show_log(self):
        self.log_manager.show_log_window()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # qDarkTheme 적용 (사용자가 이미 설치함)
    qdarktheme.setup_theme()
    
    window = DNetMainWindow()
    window.show()
    
    sys.exit(app.exec())