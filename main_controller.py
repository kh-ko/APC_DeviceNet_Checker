import re
import time
import ctypes
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from log_manager.console_widget import ConsoleWidget, MsgType
from i7565dnm_helper import i7565dnm_helper
from device_search_dialog import DeviceSearchDialog
import serial.tools.list_ports

# 실행 시점에는 임포트하지 않고, 타입 검사 시에만 임포트하여 순환 참조 방지
if TYPE_CHECKING:
    from dnet_checker import MyWindow

class MainController:
    def __init__(self, view: 'MyWindow'):
        self.view = view
        self.connected_port  = None

        self.console: ConsoleWidget = view.log_widget

        self.i7565dnm_helper = i7565dnm_helper()
        self.__load_dll()
    
    def __load_dll(self):
        result = self.i7565dnm_helper.load_dll()
        self.console.add_message(MsgType.INFO, result)

    def __check_i7565(self):
        if not self.i7565dnm_helper.dnm_lib: 
            self.console.add_message(MsgType.ERROR, "i7565DNM DLL을 로드하지 못했습니다.")
            return False
        if self.connected_port is None: 
            self.console.add_message(MsgType.ERROR, "i7565DNM과 연결된 포트가 없습니다.")
            return False
        return True
    
    def connect_device(self):
        self.console.add_message(MsgType.INFO, "i7565DNM과 연결합니다.")
        if not self.i7565dnm_helper.dnm_lib: 
            self.console.add_message(MsgType.ERROR, "i7565DNM DLL을 로드하지 못했습니다.")
            return

        selected_text = self.view.comport_combo.currentText()
        numbers = re.findall(r'\d+', selected_text.split(" ")[0]) if selected_text else None
        
        if not numbers:
            self.console.add_message(MsgType.ERROR, "포트 번호를 인식할 수 없습니다.")
            return
            
        PORT_NUMBER = int(numbers[0])
        self.console.add_message(MsgType.INFO, f"COM{PORT_NUMBER} 모듈 활성화 시도 중...")
        
        result = self.i7565dnm_helper.dnm_lib.I7565DNM_ActiveModule(PORT_NUMBER)
        if result == 0:
            self.console.add_message(MsgType.INFO, f"COM{PORT_NUMBER} 모듈 연결됨")
            self.connected_port = PORT_NUMBER
        else:
            self.console.add_message(MsgType.ERROR, f"COM{PORT_NUMBER} 모듈 연결 실패 (코드: {result})")
    
    def disconnect_device(self):
        self.console.add_message(MsgType.INFO, "i7565DNM과 연결을 끊습니다.")
        if self.__check_i7565() == False:
            return
            
        result = self.i7565dnm_helper.dnm_lib.I7565DNM_CloseModule(self.connected_port)

        if result == 0:
            self.console.add_message(MsgType.INFO, f"COM{self.connected_port} 모듈 연결 해제됨")
            self.connected_port = None
        else:
            self.console.add_message(MsgType.ERROR, f"COM{self.connected_port} 모듈 연결 해제 실패 (코드: {result})")
    
    def search_devices(self):
        self.console.add_message(MsgType.INFO, "i7565DNM을 이용하여 slave 장치를 검색합니다.")
        if self.__check_i7565() == False:
            return
        
        dialog = DeviceSearchDialog(self.connected_port, self.view)
        dialog.exec()


    
    def refresh_ports(self):
        self.console.add_message(MsgType.INFO, "포트 목록을 새로고침합니다.")
        self.view.comport_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            self.view.comport_combo.addItem("포트 없음")
            return

        for port in ports:
            self.view.comport_combo.addItem(f"{port.device} - {port.description}")
    