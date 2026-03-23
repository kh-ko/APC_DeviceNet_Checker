import sys
from PySide6.QtWidgets import QApplication, QMainWindow
import qdarktheme

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 윈도우 기본 설정
        self.setWindowTitle("DeviceNet Checker")
        self.resize(1920, 1080)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 변경된 부분: "light" 테마 적용
    qdarktheme.setup_theme("light")
    
    window = MyWindow()
    window.show()
    
    sys.exit(app.exec())