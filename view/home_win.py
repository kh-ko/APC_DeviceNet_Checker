import sys
import qdarktheme
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QDialog
from PySide6.QtGui import QAction, QPalette

from view.connection_dialog import ConnectDialog


class HomeWin(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 윈도우 기본 설정
        self.setWindowTitle("DeviceNet Checker")
        self.resize(1920, 1080)

        self.setup_toolbar()

    def setup_toolbar(self):
        toolbar = QToolBar("메인 툴바", self)
        self.addToolBar(toolbar) # 기본적으로 윈도우 상단에 배치됩니다.
        
        # 2. 액션(버튼) 생성
        action_connect = QAction("연결", self)
        action_new = QAction("새로 만들기", self)
        action_load = QAction("불러오기", self)
        action_save = QAction("저장하기", self)
        action_save_as = QAction("다른 이름으로 저장하기", self)
        
        # 3. 툴바에 액션 추가
        toolbar.addAction(action_connect)
        toolbar.addSeparator() # 시각적으로 구분하기 위해 구분선 추가
        toolbar.addAction(action_new)
        toolbar.addAction(action_load)
        toolbar.addAction(action_save)
        toolbar.addAction(action_save_as)

        accent_color = self.palette().color(QPalette.ColorRole.Highlight).name()

        toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {accent_color};
                border: none; /* 툴바 테두리 제거로 깔끔하게 */
            }}
            QToolButton {{
                color: white; /* 글자색 하얀색 */
                padding: 6px 12px; /* 버튼 내부 여백 */
                font-size: 14px; /* 글자 크기 (필요시 조절) */
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.2); /* 마우스를 올렸을 때 살짝 밝아지는 효과 */
                border-radius: 4px; /* 버튼 모서리를 둥글게 */
            }}
            QToolBar::separator {{
                background-color: rgba(255, 255, 255, 0.4); /* 반투명 흰색으로 부드럽게 */
                width: 1px; /* 세로줄 두께 */
                margin: 8px 6px; /* 위아래 8px, 좌우 6px 여백 (버튼 높이에 맞춤) */
            }}
        """)
        
        # 4. 버튼 클릭 이벤트(Signal) 연결
        # 버튼을 눌렀을 때 실행될 함수(Slot)를 연결합니다.
        action_connect.triggered.connect(self.on_connect_clicked)
        action_new.triggered.connect(self.on_new_clicked)
        action_load.triggered.connect(self.on_load_clicked)
        action_save.triggered.connect(self.on_save_clicked)
        action_save_as.triggered.connect(self.on_save_as_clicked)

    # --- 아래는 버튼 클릭 시 실행될 임시 함수(Slot)들입니다 ---
    def on_connect_clicked(self):
        # 다이얼로그 객체 생성 (self를 부모로 지정하여 화면 중앙에 뜨게 함)
        dialog = ConnectDialog(self)
        
        # 다이얼로그를 실행하고, 사용자가 '연결하기(Ok)'를 눌렀는지 확인
        if dialog.exec() == QDialog.Accepted:
            # 다이얼로그에서 데이터 가져오기
            conn_info = dialog.get_connection_info()
            
            if conn_info["Network"] == "Device Net":
                

    def on_new_clicked(self):
        print("새 프로젝트를 만듭니다.")

    def on_load_clicked(self):
        print("파일을 불러옵니다.")

    def on_save_clicked(self):
        print("파일을 저장합니다.")

    def on_save_as_clicked(self):
        print("다른 이름으로 파일을 저장합니다.")