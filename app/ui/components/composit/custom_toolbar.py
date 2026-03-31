from PySide6.QtWidgets import QToolBar, QProxyStyle, QStyle
from PySide6.QtGui import QAction, QPalette
from PySide6.QtCore import QSize

class ToolbarExtensionStyle(QProxyStyle):
    """QToolBar 내부 레이아웃이 확장 버튼 영역을 계산할 때 사용하는 픽셀 단위를 강제 오버라이드합니다."""
    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_ToolBarExtensionExtent:
            return 36 # 기존보다 3배 이상 넓은 36px로 버튼의 물리적 폭을 강제로 확보
        return super().pixelMetric(metric, option, widget)

class CustomToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 시스템(또는 qdarktheme) 스타일 위에 우리의 커스텀 메트릭(PixelMetric)을 덧씌웁니다.
        self.setStyle(ToolbarExtensionStyle(self.style()))

        self.action_connect = QAction("연결", self)
        self.action_new = QAction("새로 만들기", self)
        self.action_load = QAction("불러오기", self)
        self.action_save = QAction("저장하기", self)
        self.action_save_as = QAction("다른 이름으로 저장하기", self)
        self.action_remove = QAction("삭제하기", self)
        
        self.addAction(self.action_connect)
        self.addSeparator()
        self.addAction(self.action_new)
        self.addAction(self.action_load)
        self.addAction(self.action_save)
        self.addAction(self.action_save_as)
        self.addAction(self.action_remove)

        accent_color = self.palette().color(QPalette.ColorRole.Highlight).name()

        self.setStyleSheet(f"""
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

    def set_connect_handler(self, handler):
        self.action_connect.triggered.connect(handler)

    def set_new_handler(self, handler):
        self.action_new.triggered.connect(handler)

    def set_load_handler(self, handler):
        self.action_load.triggered.connect(handler)

    def set_save_handler(self, handler):
        self.action_save.triggered.connect(handler)

    def set_save_as_handler(self, handler):
        self.action_save_as.triggered.connect(handler)

    def set_remove_handler(self, handler):
        self.action_remove.triggered.connect(handler)