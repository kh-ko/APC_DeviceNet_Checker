import ctypes
import os
import sys
import re
import time  # 대기 시간 제어용 추가
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QToolBar, QWidget, 
                               QVBoxLayout, QLabel, QStatusBar, QComboBox, QDialog, QMessageBox, QSplitter, QTabWidget)
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtCore import Qt
import qdarktheme

from log_manager.console_widget import MsgType, ConsoleWidget
from device_select_dialog import DeviceSelectDialog
from protocol_model import DeviceConfig
from main_controller import MainController

class DNetMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APC DeviceNet Checker")
        self.resize(1000, 800)
        
        self.connected_port = None

        self._init_ui()
        self._init_toolbar()
        self._load_dll()
        self._load_protocol_model()

        self.mainController = MainController(self)


    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 1. 메인 화면 상하 분할 스플리터
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(main_splitter)
        
        # 2. 상단: 탭 위젯 (Poll 데이터 및 Explicit 등)
        self.tab_widget = QTabWidget()
        main_splitter.addWidget(self.tab_widget)
        
        # 3. 하단: 내장형 로그 콘솔 위젯
        self.console_widget = ConsoleWidget(self)
        main_splitter.addWidget(self.console_widget)
        
        # 스플리터 비율 설정 (상단 60%, 하단 40% 비율)
        main_splitter.setSizes([480, 320])

        # 상태바 및 상태 라벨 설정
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        
        self.status_label = QLabel("준비")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Malgun Gothic", 10))
        self.statusBar.addPermanentWidget(self.status_label)

    def _init_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.port_combo = QComboBox(self)
        self.port_combo.setMinimumWidth(100)
        self.refresh_ports()
        self.toolbar.addWidget(self.port_combo)

        self.refresh_action = QAction("새로고침", self)
        self.refresh_action.triggered.connect(self.mainController.refresh_ports)
        self.toolbar.addAction(self.refresh_action)
        self.toolbar.addSeparator()

        self.connect_action = QAction("연결", self)
        self.connect_action.triggered.connect(self.mainController.connect_device)
        self.toolbar.addAction(self.connect_action)

        self.disconnect_action = QAction("연결끊기", self)
        self.disconnect_action.triggered.connect(self.mainController.disconnect_device)
        self.disconnect_action.setEnabled(False)
        self.toolbar.addAction(self.disconnect_action)
        self.toolbar.addSeparator()

        # 장치 검색 액션 추가
        self.search_action = QAction("장치 검색", self)
        self.search_action.triggered.connect(self.mainController.search_devices)
        self.search_action.setEnabled(False) # 연결 전에는 비활성화
        self.toolbar.addAction(self.search_action)
        self.toolbar.addSeparator()

        self.log_action = QAction("로그보기", self)
        self.log_action.triggered.connect(self.show_log)
        self.toolbar.addAction(self.log_action)

    def _load_dll(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(current_dir, "x64", "I7565DNM.dll")
        
        try:
            self.dnm_lib = ctypes.WinDLL(dll_path)
            self.log_manager.log("DLL 로드 성공!", MsgType.INFO)
            
            # 기존 함수들
            self.dnm_lib.I7565DNM_ActiveModule.argtypes = [ctypes.c_uint8]
            self.dnm_lib.I7565DNM_ActiveModule.restype = ctypes.c_uint32
            self.dnm_lib.I7565DNM_CloseModule.argtypes = [ctypes.c_uint8]
            self.dnm_lib.I7565DNM_CloseModule.restype = ctypes.c_uint32

            # [장치 검색 관련 함수 정의]
            # 1. 전체 스캔 시작
            self.dnm_lib.I7565DNM_SearchAllDevices.argtypes = [ctypes.c_uint8]
            self.dnm_lib.I7565DNM_SearchAllDevices.restype = ctypes.c_uint32
            
            # 2. 스캔 완료 여부 체크
            self.dnm_lib.I7565DNM_IsSearchOK.argtypes = [ctypes.c_uint8]
            self.dnm_lib.I7565DNM_IsSearchOK.restype = ctypes.c_uint32
            
            # 3. 검색된 데이터 가져오기 (포인터 배열 형태)
            self.dnm_lib.I7565DNM_GetSearchedDevices.argtypes = [
                ctypes.c_uint8,                       # Port Number
                ctypes.POINTER(ctypes.c_uint16),      # TotalDevices (출력)
                ctypes.POINTER(ctypes.c_uint8),       # DesMACID Array (출력)
                ctypes.POINTER(ctypes.c_uint8),       # Type Array (출력)
                ctypes.POINTER(ctypes.c_uint16),      # DeviceInputLen Array (출력)
                ctypes.POINTER(ctypes.c_uint16)       # DeviceOutputLen Array (출력)
            ]
            self.dnm_lib.I7565DNM_GetSearchedDevices.restype = ctypes.c_uint32
            
        except OSError as e:
            self.log_manager.log(f"DLL 로드 실패: {e}", MsgType.ERROR)
            self.status_label.setText("DLL 로드 실패")
            self.dnm_lib = None

    def _load_protocol_model(self):
        try:
            self.config = DeviceConfig.from_json_file('device_configs.json')
            self.log_manager.log("프로토콜 모델 로드 성공!", MsgType.INFO)
        except Exception as e:
            self.log_manager.log(f"프로토콜 모델 로드 실패: {e}", MsgType.ERROR)
            self.config = None

    def connect_device(self):
        if not self.dnm_lib: return
        selected_text = self.port_combo.currentText()
        numbers = re.findall(r'\d+', selected_text.split(" ")[0]) if selected_text else None
        
        if not numbers:
            self.log_manager.log("포트 번호를 인식할 수 없습니다.", MsgType.ERROR)
            return
            
        PORT_NUMBER = int(numbers[0])
        self.log_manager.log(f"COM{PORT_NUMBER} 모듈 활성화 시도 중...", MsgType.INFO)
        
        result = self.dnm_lib.I7565DNM_ActiveModule(PORT_NUMBER)
        if result == 0:
            self.log_manager.log("=> [성공] 모듈 연결됨", MsgType.INFO)
            self.status_label.setText(f"COM{PORT_NUMBER} 연결됨")
            self.connected_port = PORT_NUMBER
            
            # 버튼 상태 전환
            self.connect_action.setEnabled(False)
            self.disconnect_action.setEnabled(True)
            self.search_action.setEnabled(True)  # 장치 검색 활성화
            self.port_combo.setEnabled(False)
        else:
            self.log_manager.log(f"=> [실패] 연결 에러 (코드: {result})", MsgType.ERROR)

    def disconnect_device(self):
        if not self.dnm_lib or self.connected_port is None: return
        result = self.dnm_lib.I7565DNM_CloseModule(self.connected_port)

        if result == 0:
            self.log_manager.log("=> [성공] 연결 해제됨", MsgType.INFO)
            self.status_label.setText("연결 해제됨")
            self.connected_port = None
            
            # 버튼 상태 복구
            self.connect_action.setEnabled(True)
            self.disconnect_action.setEnabled(False)
            self.search_action.setEnabled(False)  # 장치 검색 비활성화
            self.port_combo.setEnabled(True)
        else:
            self.log_manager.log(f"=> [실패] 해제 에러 (코드: {result})", MsgType.ERROR)

    def search_devices(self):
        if not self.dnm_lib or self.connected_port is None: return

        port = self.connected_port
        self.log_manager.log("--- DeviceNet 네트워크 스캔을 시작합니다 ---", MsgType.INFO)
        self.statusBar().showMessage("네트워크 스캔 중...")
        
        # 1. 스캔 시작
        res = self.dnm_lib.I7565DNM_SearchAllDevices(port)
        if res != 0 and res != 1055: # 1055(진행중)는 에러로 간주하지 않고 통과시킴
            self.log_manager.log(f"스캔 시작 실패 (에러 코드: {res})", MsgType.ERROR)
            self.statusBar().showMessage("스캔 실패")
            return
            
        timeout_cnt = 0
        search_finished = False
        
        # 2. 스캔 완료 대기 (수정 전 코드로 완벽 복구!)
        while timeout_cnt < 100:
            status = self.dnm_lib.I7565DNM_IsSearchOK(port)
            
            if status == 0:
                search_finished = True
                break
            
            # 중간에 어떤 코드가 나오든 무시하고 0이 뜰 때까지 대기
            QApplication.processEvents()
            time.sleep(0.1)
            timeout_cnt += 1
            
        if not search_finished:
            self.log_manager.log("장치 검색 시간 초과! (네트워크 상태를 확인하세요)", MsgType.WARNING)
            self.statusBar().showMessage("스캔 시간 초과")
            return
            
        # 3. 검색 결과 가져오기 (팝업 기능은 그대로 유지)
        total_devices = ctypes.c_uint16(0)
        mac_ids = (ctypes.c_uint8 * 64)()
        dev_types = (ctypes.c_uint8 * 64)()
        input_lens = (ctypes.c_uint16 * 64)()
        output_lens = (ctypes.c_uint16 * 64)()
        
        res = self.dnm_lib.I7565DNM_GetSearchedDevices(
            port, ctypes.byref(total_devices), mac_ids, dev_types, input_lens, output_lens
        )
        
        if res == 0:
            count = total_devices.value
            if count == 0:
                self.log_manager.log("=> 스캔 완료! 연결된 Slave 장치가 없습니다.", MsgType.WARNING)
                self.statusBar().showMessage("스캔 완료 (0개 장치)")
                QMessageBox.information(self, "검색 결과", "검색된 장치가 없습니다.")
            else:
                self.log_manager.log(f"=> 스캔 완료! 총 {count}개의 Slave 장치가 응답했습니다.", MsgType.INFO)
                self.statusBar().showMessage(f"스캔 완료 ({count}개 장치 발견됨)")
                
                # 팝업에 전달할 리스트 생성
                devices_list = []
                for i in range(count):
                    dev_info = {
                        'mac': mac_ids[i],
                        'type': dev_types[i],
                        'in_len': input_lens[i],
                        'out_len': output_lens[i]
                    }
                    devices_list.append(dev_info)
                    self.log_manager.log(f"  [{i+1}] MAC ID: {dev_info['mac']:02d} | Type: 0x{dev_info['type']:02X}", MsgType.INFO)
                
                # 팝업 띄우기
                dialog = DeviceSelectDialog(devices_list, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_mac = dialog.get_selected_mac()
                    if selected_mac is not None:
                        self.selected_slave_mac = selected_mac
                        self.log_manager.log(f"사용자가 MAC ID {self.selected_slave_mac:02d} 장치를 선택했습니다.", MsgType.INFO)
                        self.statusBar().showMessage(f"현재 통신 대상: MAC ID {self.selected_slave_mac:02d}")
                else:
                    self.log_manager.log("장치 선택이 취소되었습니다.", MsgType.WARNING)
        else:
            self.log_manager.log(f"검색 결과 가져오기 실패 (코드: {res})", MsgType.ERROR)
            self.statusBar().showMessage("결과 로드 실패")

    def show_log(self):
        self.log_manager.show_log_window()

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            self.port_combo.addItem("포트 없음")
            return

        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    
    window = DNetMainWindow()
    window.show()
    
    sys.exit(app.exec())