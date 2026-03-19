# 1.개요: App 전체에 걸처 로그를 관리하는 매니저 클래스
# 2.설명: Singleton 패턴을 적용하여 App 전체에 걸처 로그를 관리합니다.
#        LogWindow에 로그를 표시하고, 필요에 따라(추후 구현 예정) 파일에 로그를 저장합니다.
#        그러므로 LogWindow를 생성하는 코드와 LogMessage를 전달 받는 코드가 구현되어야 한다.

from log_manager.log_win import LogWin
from log_manager.console_widget import MsgType

class LogManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LogManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # LogWindow 인스턴스 초기화 (아직 화면에 표시하지 않음)
        self.log_window = None

    def _get_log_window(self):
        # 지연 생성(Lazy Initialization)을 통해 불필요한 리소스 사용 방지
        # 혹은 메인 UI 스레드에서 생성되도록 보장
        if self.log_window is None:
            self.log_window = LogWin()
        return self.log_window

    def log(self, message: str, msg_type: MsgType = MsgType.INFO):
        print(f"[{msg_type.name}] {message}")  # 콘솔에도 출력
        
        # LogWindow가 열려 있을 때만 ConsoleWidget에 메시지를 추가하여 부하 방지
        if self.log_window and hasattr(self.log_window, 'console_widget'):
            self.log_window.console_widget.add_message(msg_type, message)

    def show_log_window(self):
        window = self._get_log_window()
        window.show()
        window.raise_()
        window.activateWindow()