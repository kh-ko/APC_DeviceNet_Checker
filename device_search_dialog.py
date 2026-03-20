import re
import ctypes
from PySide6.QtWidgets import (QApplication, QDialog, QListWidget, QPushButton, 
                               QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from i7565dnm_helper import i7565dnm_helper
from log_manager.console_widget import ConsoleWidget, MsgType

class DeviceSearchDialog(QDialog):
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.mainWin = parent
        self.i7565dnm_helper = i7565dnm_helper()
        self.console: ConsoleWidget = self.mainWin.log_widget

        self.setWindowTitle(f"COM{port} Slave 장치 검색")
        self.resize(400, 400)

        # 1. UI 구성
        self.status_label = QLabel("장치 스캔 준비 중...", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 시각적인 애니메이션을 위한 Progress Bar 추가
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0) # (0, 0)으로 설정하면 무한 로딩 애니메이션 실행
        self.progress_bar.setTextVisible(False)
        
        self.device_list = QListWidget(self)
        self.device_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.device_list.itemSelectionChanged.connect(self._on_item_selected)
        
        self.btn_ok = QPushButton("선택", self)
        self.btn_ok.setEnabled(False) # 처음에는 비활성화 (결과가 나와야 활성화)
        self.btn_ok.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("취소", self)
        self.btn_cancel.clicked.connect(self.cancel_scan)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar) # 레이아웃에 Progress Bar 추가
        main_layout.addWidget(self.device_list)
        main_layout.addLayout(btn_layout)

        # 2. 타이머 설정 (비동기 상태 체크)
        self.timeout_cnt = 0
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_scan_status)

        # 3. 다이얼로그가 뜨고 나서 스캔 시작 (100ms 딜레이)
        QTimer.singleShot(100, self._start_scan)
        
    def _start_scan(self):
        self.status_label.setText("네트워크를 스캔 중입니다. 잠시만 기다려주세요...")
        
        # 스캔 시작
        res = self.i7565dnm_helper.dnm_lib.I7565DNM_SearchAllDevices(self.port)
        self.console.add_message(MsgType.INFO, f"SearchAllDevices() 시작 - 반환값: {res}")

        if res != 0 and res != 1055: # 1055(진행중)는 정상
            self._stop_progress_bar(success=False)
            self.console.add_message(MsgType.ERROR, f"스캔 시작 실패 (에러 코드: {res})")
            self.status_label.setText(f"스캔 실패 (에러 코드: {res})")
            return
            
        # 스캔 상태 체크 타이머 가동 (100ms 마다 동작)
        self.timeout_cnt = 0
        self.check_timer.start(100)

    def _check_scan_status(self):
        self.timeout_cnt += 1
        
        # 타임아웃 처리 (예: 20초 = 200회)
        if self.timeout_cnt >= 200:
            self.check_timer.stop()
            self._stop_progress_bar(success=False)
            self.status_label.setText("장치 검색 시간 초과!")
            self.console.add_message(MsgType.WARNING, "장치 검색 시간 초과! (네트워크 상태를 확인하세요)")
            return

        # 스캔 상태 확인
        status = self.i7565dnm_helper.dnm_lib.I7565DNM_IsSearchOK(self.port)
        
        if status == 0: # 스캔 완료
            self.check_timer.stop()
            self._stop_progress_bar(success=True)
            self.status_label.setText("스캔 완료! 연결할 장치를 선택하세요.")
            self._load_scanned_devices()
            
        elif status == 1055: # 스캔 진행 중
            # 점(.) 애니메이션은 유지
            dots = "." * ((self.timeout_cnt % 4) + 1)
            self.status_label.setText(f"장치를 스캔 중입니다{dots}")
            
        else: # 기타 에러 발생 시
            self.check_timer.stop()
            self._stop_progress_bar(success=False)
            self.status_label.setText(f"스캔 에러 발생 (코드: {status})")
            self.console.add_message(MsgType.ERROR, f"스캔 중 에러 발생! (코드: {status})")

    def _stop_progress_bar(self, success):
        """스캔이 종료되었을 때 Progress Bar의 애니메이션을 멈추고 상태를 업데이트합니다."""
        self.progress_bar.setRange(0, 100) # (0, 100)으로 변경하여 무한 로딩 해제
        if success:
            self.progress_bar.setValue(100) # 성공 시 100%로 가득 채움
        else:
            self.progress_bar.setValue(0)   # 실패 시 0%로 초기화
            self.progress_bar.hide()        # 실패/오류 시에는 숨김 처리 가능

    def _load_scanned_devices(self):
        total_devices = ctypes.c_uint16(0)
        mac_ids = (ctypes.c_uint8 * 64)()
        dev_types = (ctypes.c_uint8 * 64)()
        input_lens = (ctypes.c_uint16 * 64)()
        output_lens = (ctypes.c_uint16 * 64)()
        
        res = self.i7565dnm_helper.dnm_lib.I7565DNM_GetSearchedDevices(
            self.port, ctypes.byref(total_devices), mac_ids, dev_types, input_lens, output_lens
        )
        
        if res == 0:
            count = total_devices.value
            if count == 0:
                self.console.add_message(MsgType.WARNING, "=> 스캔 완료! 연결된 Slave 장치가 없습니다.")
                self.status_label.setText("검색된 장치가 없습니다.")
            else:
                self.console.add_message(MsgType.INFO, f"=> 스캔 완료! 총 {count}개의 Slave 장치가 응답했습니다.")
                
                # 리스트 위젯에 아이템 추가
                for i in range(count):
                    item_text = f"MAC ID: {mac_ids[i]:02d} | Type: 0x{dev_types[i]:02X} | In: {input_lens[i]} byte | Out: {output_lens[i]} byte"
                    self.device_list.addItem(item_text)
                    self.console.add_message(MsgType.INFO, f"  [{i+1}] {item_text}")
        else:
            self.console.add_message(MsgType.ERROR, f"검색 결과 가져오기 실패 (코드: {res})")
            self.status_label.setText("결과 가져오기 실패")

    def _on_item_selected(self):
        # 리스트에서 항목을 선택했을 때만 '선택' 버튼 활성화
        self.btn_ok.setEnabled(bool(self.device_list.selectedItems()))

    def get_selected_mac_id(self):
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            return None
        
        text = selected_items[0].text()
        match = re.search(r"MAC ID:\s*(\d+)", text)
        if match:
            return int(match.group(1))
        return None

    def cancel_scan(self):
        """취소 버튼을 눌렀을 때 스캔 타이머를 즉시 멈추고 다이얼로그를 닫습니다."""
        if self.check_timer.isActive():
            self.check_timer.stop()
            self._stop_progress_bar(success=False)
            self.console.add_message(MsgType.WARNING, "사용자에 의해 장치 스캔이 취소되었습니다.")
        
        self.reject() # 창을 닫고 dialog.exec()가 False를 반환하도록 함

    def closeEvent(self, event):
        # 다이얼로그의 X 버튼 등을 눌러 창을 닫을 때, 타이머가 돌고 있다면 스캔 중지 처리
        if self.check_timer.isActive():
            self.check_timer.stop()
            self._stop_progress_bar(success=False)
            self.console.add_message(MsgType.WARNING, "창 닫기로 인해 장치 스캔이 취소되었습니다.")
            
        super().closeEvent(event)