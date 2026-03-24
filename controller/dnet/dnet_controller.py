import logging
from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import QDialog

from worker.dnet.dnet_worker import DnetWorker
from view.dnet_scan_dialog import DnetScanDialog
from view.schema_select_dialog import SchemaSelectDialog
from log_manager.console_widget import MsgType
from view.components.dnet.dnet_widget import DnetWidget

class DnetController(QObject):
    # 크로스 스레드(Cross-thread) 통신을 위한 시그널 정의
    cmd_connect_module = Signal(int)
    cmd_disconnect_module = Signal()
    cmd_connect_slave = Signal(int)

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        
        # DeviceNet 워커 및 백그라운드 스레드 설정
        self.worker = DnetWorker()
        self.worker_thread = QThread(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()
        
        # DLL 로드 시도
        self.worker.initialize()
        
        # 워커와의 시그널 연동 (스레드 충돌 방지)
        self.cmd_connect_module.connect(self.worker.connect_module)
        self.cmd_disconnect_module.connect(self.worker.disconnect_module, Qt.BlockingQueuedConnection)
        self.cmd_connect_slave.connect(self.worker.connect_slave)
        self.worker.log_msg_signal.connect(self.on_dnet_log)

    def connect_module(self, conn_info: dict):
        """
        Dnet 연결 시연 시 팝업 등 제어 파트
        """
        # connection_dialog에서 내부 데이터로 찐 포트명(예: "COM5") 반환
        port_str = conn_info.get("Comport", "COM1")
        port_num = int("".join(filter(str.isdigit, port_str)))

        # 1. 마스터 활성화 (포트 오픈) - 시그널을 통한 안전한 호출
        self.cmd_connect_module.emit(port_num)
        
        # 2. dnet_scan_dialog 띄우기 (스캔 + Slave 선택 화면)
        scan_dialog = DnetScanDialog(self.worker, self.parent_window)
        if scan_dialog.exec() == QDialog.Accepted:

            schema_dialog = SchemaSelectDialog(self.parent_window)
            if schema_dialog.exec() == QDialog.Accepted:
                schema_path = schema_dialog.selected_schema
                
                # 기존에 추가된 위젯이 있다면 제거 (중복 방지)
                while self.parent_window.left_layout.count():
                    child = self.parent_window.left_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

                # 새로운 DnetWidget 추가
                self.dnet_widget = DnetWidget(schema_path)
                self.parent_window.left_layout.addWidget(self.dnet_widget)
                self.dnet_widget.update_ui()
            else:
                # 빈 스키마 파일 만들기
                pass

            mac_id = scan_dialog.selected_mac_id
            print(f"[Controller] 선택된 MAC ID: {mac_id}")
            
            # 3. 타겟 슬레이브 지정 (ONLINE 상태 변경)
            self.cmd_connect_slave.emit(mac_id)
            
            # TODO: 이후 어떤 프로토콜(JSON)을 테스트할지 고르는 UI 연동
        else:
            # 취소 혹은 그냥 닫았을 시 모듈 해제 (DISCONNECTED 상태 복귀)
            self.cmd_disconnect_module.emit()

    def on_dnet_log(self, msg_type, message):
        consoleMsgType : MsgType = MsgType.INFO
        if msg_type == "ERROR":
            consoleMsgType = MsgType.ERROR
        elif msg_type == "WARNING":
            consoleMsgType = MsgType.WARNING
        elif msg_type == "INFO":
            consoleMsgType = MsgType.INFO
        elif msg_type == "TX":
            consoleMsgType = MsgType.TX
        elif msg_type == "RX":
            consoleMsgType = MsgType.RX

        self.parent_window.console.add_message(consoleMsgType, message)

    def shutdown(self):
        """
        프로그램 종료 시 호출하여 모듈과 스레드를 안전하게 닫습니다.
        """
        # 1. 워커 내부의 통신 해제 및 타이머 정지 (BlockingQueuedConnection으로 인해 대기함)
        self.cmd_disconnect_module.emit()
        
        # 2. 워커 스레드 이벤트 큐에 '워커 객체 삭제' 명령(Event)을 맨 앞에 넣음
        self.worker.deleteLater()
        
        # 3. 워커 스레드 이벤트 큐에 '루프 종료' 명령을 그 뒤에 넣고 대기
        self.worker_thread.quit()
        self.worker_thread.wait()

        print("DnetController shutdown")
