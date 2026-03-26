import qdarktheme

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QDialog

from app.model.global_define import NetworkType
from app.model.dnet.dnet_model import DnetModel

from app.ui.components.composit.console_widget import MsgType
from app.ui.network_view import NetworkView
from app.ui.dialog.schema_select_dialog import SchemaSelectDialog
from app.ui.dialog.slave_select_dialog import SlaveSelectDialog


class DnetView(NetworkView):
    """
    DnetModel의 데이터를 읽어와 Poll-In, Poll-Out, Explicit 메시지를 
    탭 형태로 보여주는 커스텀 위젯입니다.
    """
    sig_connect_module = Signal(int)
    sig_scan_slave = Signal()
    sig_connect_slave = Signal(int, int, int)
    sig_disconnect_module = Signal()
    
    sig_add_log = Signal(MsgType, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_dialog = None
        self.scan_progress_dialog = None

    ################################
    # public APIs
    ################################
    def shutdown(self):
        self.sig_add_log.emit(MsgType.INFO, "[DnetView][shutdown]")
        self.sig_disconnect_module.emit()

        #Todo: Service delete -> 쓰레드 종료 -> 종료 대기

        self.on_connect_network_canceled()
        self.on_scan_slave_canceled()

    def connect_network(self, conn_info):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] conn_info: {conn_info.get('Comport', '')}")
        """
        i7564DNM 모듈에 연결하기전에 스키마 파일을 선택 이후 화면을 꾸미고 연결 시도
        """
        dialog = SchemaSelectDialog(NetworkType.DNET.value)
        if dialog.exec() == QDialog.Accepted:
            schema_path = dialog.selected_schema
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] 스키마 파일 선택 취소")
            return

        self.__build_ui(schema_path)

        """
        i7564DNM 모듈에 연결 시도 및 팝업 등 제어 파트
        """
        # connection_dialog에서 내부 데이터로 찐 포트명(예: "COM5") 반환
        port_str = conn_info.get("Comport", "COM1")
        port_num = int("".join(filter(str.isdigit, port_str)))

        self.progress_dialog = QProgressDialog("모듈에 연결 중입니다...", "취소", 0, 0, self)
        self.progress_dialog.setWindowTitle("잠시만 기다려주세요")
        self.progress_dialog.setWindowModality(Qt.WindowModal)  # 다른 UI 조작 차단
        self.progress_dialog.setMinimumDuration(0) # 즉시 표시
        
        # 취소 버튼을 눌렀을 때의 처리 (필요에 따라 연결 취소 시그널 발생 등)
        self.progress_dialog.canceled.connect(self.on_connect_network_canceled)
        
        self.progress_dialog.show()

        # 1. 마스터 활성화 (포트 오픈) - 시그널을 통한 안전한 호출
        self.sig_connect_module.emit(port_num)        

    def create_new_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][create_new_schema]")
        
    def open_select_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][open_select_schema]")
        
    def save_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_schema]")
        
    def save_as_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_as_schema]")
        
    def remove_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][remove_schema]")
        
    ################################
    # Ui signal handlers
    ################################
    @Slot()
    def on_connect_network_canceled(self):
        self.sig_disconnect_module.emit()
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    @Slot()
    def on_scan_slave_canceled(self):
        self.sig_disconnect_module.emit()        
        if self.scan_progress_dialog:
            self.scan_progress_dialog.close()
            self.scan_progress_dialog = None

    ################################
    # Service signal handlers
    ################################
    @Slot(bool)
    def on_connect_network_finished(self, success: bool):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_connect_network_finished] success: {success}")
        self.on_connect_network_canceled()

        if success:
            self.sig_add_log.emit(MsgType.INFO, "모듈에 연결되었습니다.")
        else:
            self.sig_add_log.emit(MsgType.ERROR, "모듈에 연결할 수 없습니다.")
            return

        self.scan_progress_dialog = QProgressDialog("Slave 검색 중입니다.", "취소", 0, 0, self)
        self.scan_progress_dialog.setWindowTitle("잠시만 기다려주세요")
        self.scan_progress_dialog.setWindowModality(Qt.WindowModal)  # 다른 UI 조작 차단
        self.scan_progress_dialog.setMinimumDuration(0) # 즉시 표시
        
        # 취소 버튼을 눌렀을 때의 처리 (필요에 따라 연결 취소 시그널 발생 등)
        self.scan_progress_dialog.canceled.connect(self.on_scan_slave_canceled)
        
        self.scan_progress_dialog.show()

        # 1. 마스터 활성화 (포트 오픈) - 시그널을 통한 안전한 호출
        self.sig_scan_slave.emit()  
        
    @Slot(bool)
    def on_scan_slave_finished(self, found_devices):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_scan_slave_finished] found_devices num: {len(found_devices)}")
        self.on_scan_slave_canceled()

        dialog = SlaveSelectDialog(found_devices)
        if dialog.exec() == QDialog.Accepted:
            mac_id, in_len, out_len = dialog.selected_device_info
            self.sig_connect_slave.emit(mac_id, in_len, out_len)
        else:
            return
        
    ################################
    # private functions
    ################################            
    def __build_ui(self, schema_path):
        model : DnetModel = DnetModel()
        model.load_from_json(schema_path)

        # model의 정보를 바탕으로 UI 구성
        