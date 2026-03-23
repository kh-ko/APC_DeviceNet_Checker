import sys
from PySide6.QtWidgets import QApplication
import qdarktheme
from view.home_win import HomeWin

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 변경된 부분: "light" 테마 적용
    qdarktheme.setup_theme("light")
    
    window = HomeWin()
    window.show()
    
    sys.exit(app.exec())