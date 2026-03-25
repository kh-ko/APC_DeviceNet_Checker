from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, 
                               QPushButton, QHBoxLayout, QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt, Signal
from worker.dnet.dnet_worker import DnetWorker

class DnetScanDialog(QDialog):
    cmd_search_devices = Signal()
    cmd_stop_search = Signal()

    def __init__(self, worker: DnetWorker, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeviceNet 장치 스캔")
        self.resize(400, 300)
        
        self.worker: DnetWorker = worker
        self.selected_device_info = None
        
        # UI 구성
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("네트워크를 스캔하는 중...", self)
        layout.addWidget(self.status_label)
        
        self.device_list = QListWidget(self)
        layout.addWidget(self.device_list)
        
        btn_layout = QHBoxLayout()
        self.rescan_btn = QPushButton("다시 스캔", self)
        self.connect_btn = QPushButton("이 장치와 연결", self)
        self.connect_btn.setEnabled(False) # 선택 전에는 비활성화
        self.cancel_btn = QPushButton("취소", self)
        
        btn_layout.addWidget(self.rescan_btn)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 시그널 연결 (버튼 이벤트)
        self.rescan_btn.clicked.connect(self.start_scan)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        self.device_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Worker 시그널 연결 (스캔 결과 수신)
        self.worker.device_search_complete_signal.connect(self.on_scan_completed)
        self.worker.log_msg_signal.connect(self.on_worker_log)
        
        # 내부 Signal을 Worker의 Slot에 연결 (안전한 스레드 호출 위함)
        self.cmd_search_devices.connect(self.worker.search_devices)
        self.cmd_stop_search.connect(self.worker.stop_search)
        
        # 창이 켜지면서 바로 자동 스캔
        self.start_scan()
        
    def start_scan(self):
        self.device_list.clear()
        self.status_label.setText("네트워크 스캔 중입니다. 잠시만 기다려주세요...")
        self.rescan_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)
        # 스레드가 분리되어 있으므로 Signal을 통해 간접 호출해야 QTimer 충돌이 없습니다.
        self.cmd_search_devices.emit()
        
    def on_scan_completed(self, found_devices):
        self.rescan_btn.setEnabled(True)

        poll_devices = [dev for dev in found_devices if dev["type"] == 1]
        
        if not poll_devices:
            self.status_label.setText("검색된 장비가 없습니다. 배선 및 전원을 확인해 주세요.")
            return
            
        self.status_label.setText(f"총 {len(poll_devices)}개의 장비가 검색되었습니다. 연결할 장비를 선택하세요.")
        
        for dev in poll_devices:
            mac_id = dev["mac_id"]
            dev_type = dev["type"]
            in_len = dev["in_len"]
            out_len = dev["out_len"]
            
            # 리스트 아이템 생성 및 MAC ID 데이터 심기
            list_text = f"MAC ID: {mac_id} (Type: {dev_type}, In: {in_len}B, Out: {out_len}B)"
            item = QListWidgetItem(list_text)
            item.setData(Qt.UserRole, (mac_id, in_len, out_len))
            self.device_list.addItem(item)

    def on_selection_changed(self):
        # 아이템 클릭 시 '연결' 버튼 활성화
        if self.device_list.selectedItems():
            self.connect_btn.setEnabled(True)
        else:
            self.connect_btn.setEnabled(False)
            
    def on_connect_clicked(self):
        selected = self.device_list.selectedItems()
        if selected:
            # 선택된 아이템의 MAC ID 가져오기
            self.selected_device_info = selected[0].data(Qt.UserRole)
            self.accept() # 다이얼로그 성공적으로 닫기
            
    def on_worker_log(self, level, msg):
        # 스캔 실패 등의 에러가 발생한 경우 UI에 표시
        if level == ("ERROR" or "WARNING"):
            self.status_label.setText(f"<font color='red'>오류 발생: {msg}</font>")
            self.rescan_btn.setEnabled(True)

    def closeEvent(self, event):
        # 다이얼로그를 강제로 닫을 때 스캔 중지 (시그널 호출)
        self.cmd_stop_search.emit()
        
        # Worker 시그널 연결 해제 (다이얼로그가 닫힌 후 남아있는 시그널 방지)
        self.worker.device_search_complete_signal.disconnect()
        self.worker.log_msg_signal.disconnect()
        
        super().closeEvent(event)
