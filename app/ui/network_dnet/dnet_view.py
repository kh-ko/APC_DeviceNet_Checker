import qdarktheme

from PySide6.QtCore import QObject, QThread, Signal, Qt, Slot
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QDialog, QHBoxLayout, QTabWidget, QWidget, QVBoxLayout

from app.model.global_define import NetworkType
from app.model.dnet.dnet_model import DnetModel

from app.network_service.dnet_i7565dnm_svc import DnetI7565DNMSvc

from app.ui.components.composit.console_widget import MsgType
from app.ui.components.custom.custom_controls import CustomSpinBox, CustomLabel, CustomPushButton
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

        self.dnet_svc = DnetI7565DNMSvc()

        self.dnet_svc.sig_add_log.connect(self.sig_add_log)
        self.dnet_svc.sig_connect_network_finished.connect(self.on_connect_network_finished)
        self.dnet_svc.sig_connect_slave_finished.connect(self.on_connect_slave_finished)
        self.dnet_svc.sig_scan_slave_finished.connect(self.on_scan_slave_finished)

        self.sig_connect_module.connect(self.dnet_svc.connect_module)
        self.sig_scan_slave.connect(self.dnet_svc.search_devices)
        self.sig_connect_slave.connect(self.dnet_svc.connect_slave)
        self.sig_disconnect_module.connect(self.dnet_svc.disconnect_module)



    ################################
    # public APIs
    ################################
    def shutdown(self):
        self.sig_add_log.emit(MsgType.INFO, "[DnetView][shutdown]")
        self.sig_disconnect_module.emit()

        self.on_connect_network_canceled()
        self.on_scan_slave_canceled()

    def connect_network(self, conn_info):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] conn_info: {conn_info.get('Comport', '')}")

        """
        i7564DNM 모듈에 연결 
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

    def on_connect_slave_finished(self, success: bool):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_connect_slave_finished] success: {success}")
        self.on_connect_slave_canceled()

        if success:
            self.sig_add_log.emit(MsgType.INFO, "Slave에 연결되었습니다.")
        else:
            self.sig_add_log.emit(MsgType.ERROR, "Slave에 연결할 수 없습니다.")
            return

        """
        스키마 파일을 선택하여 화면을 구성한다.
        """
        dialog = SchemaSelectDialog(NetworkType.DNET.value)
        if dialog.exec() == QDialog.Accepted:
            schema_path = dialog.selected_schema
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] 스키마 파일 선택 취소")
            return

        self.__build_ui(schema_path)
        
    ################################
    # private functions
    ################################            
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 상단 컨트롤 패널 추가 ---
        self.top_control_layout = QHBoxLayout()
        self.top_control_layout.setContentsMargins(5, 5, 5, 5)
        self.top_control_layout.setSpacing(10)

        # 1. 이름 라벨
        # 모델에 이름 속성이 있다면 self.dnet_model.name 등으로 변경 가능합니다.
        self.lbl_name = CustomLabel("이름 : DNET 장치") 
        self.top_control_layout.addWidget(self.lbl_name)
        
        # 2. 사이클 주기 입력 (ms)
        self.top_control_layout.addWidget(CustomLabel("사이클 주기:"))
        self.spin_cycle = CustomSpinBox()
        self.spin_cycle.setRange(1, 10000) # 1ms ~ 10000ms 범위 설정
        self.spin_cycle.setValue(100)      # 기본값 100ms
        self.spin_cycle.setSuffix(" ms")   # 숫자 뒤에 'ms' 텍스트 표시
        self.top_control_layout.addWidget(self.spin_cycle)
        
        # 3. Polling 시작 버튼
        self.btn_start_polling = CustomPushButton("Polling 시작")
        self.btn_start_polling.clicked.connect(self._on_start_polling_clicked)
        self.top_control_layout.addWidget(self.btn_start_polling)
        
        # 4. Polling 중지 버튼
        self.btn_stop_polling = CustomPushButton("Polling 중지")
        self.btn_stop_polling.clicked.connect(self._on_stop_polling_clicked)
        self.top_control_layout.addWidget(self.btn_stop_polling)
        
        # 5. Out 데이터 쓰기 버튼
        self.btn_write_out = CustomPushButton("Out 데이터 쓰기")
        self.btn_write_out.clicked.connect(self._on_write_out_clicked)
        self.top_control_layout.addWidget(self.btn_write_out)
        
        # 남는 우측 여백을 밀어주어 위젯들을 좌측 정렬되게 함
        self.top_control_layout.addStretch() 
        
        # 메인 레이아웃에 상단 컨트롤 패널 추가 (탭 위젯보다 먼저 추가되어야 상단에 위치함)
        self.main_layout.addLayout(self.top_control_layout)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget(self)
        self.main_layout.addWidget(self.tab_widget)
        
        # 각 통신 영역별 스크롤 가능한 탭 생성
        self.poll_in_tab, self.poll_in_layout = self._create_scrollable_tab()
        self.poll_out_tab, self.poll_out_layout = self._create_scrollable_tab()
        self.explicit_tab, self.explicit_layout = self._create_scrollable_tab()
        
        self.tab_widget.addTab(self.poll_in_tab, "Poll-In (RX)")
        self.tab_widget.addTab(self.poll_out_tab, "Poll-Out (TX)")
        self.tab_widget.addTab(self.explicit_tab, "Explicit")

    def __build_ui(self, schema_path):
        model : DnetModel = DnetModel()
        model.load_from_json(schema_path)

        # model의 정보를 바탕으로 UI 구성
        