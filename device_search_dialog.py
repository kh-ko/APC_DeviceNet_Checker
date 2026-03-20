import time
import ctypes
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt
from i7565dnm_helper import i7565dnm_helper
from log_manager.console_widget import ConsoleWidget, MsgType

class DeviceSearchDialog(QDialog):
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.mainWin = parent
        self.i7565dnm_helper = i7565dnm_helper()
        self.console : ConsoleWidget = self.mainWin.log_widget

        self.setWindowTitle(f"COM{port} Slave 장치 검색")
        self.resize(350, 300)

        self.__search_devices()
        
    def __search_devices(self):
        # 1. 스캔 시작
        res = self.i7565dnm_helper.dnm_lib.I7565DNM_SearchAllDevices(self.port)
        self.console.add_message(MsgType.INFO, f"SearchAllDevices() - {res}")

        if res != 0 and res != 1055: # 1055(진행중)는 에러로 간주하지 않고 통과시킴
            self.console.add_message(MsgType.ERROR, f"스캔 시작 실패 (에러 코드: {res})")
            return
            
        timeout_cnt = 0
        search_finished = False
        
        # 2. 스캔 완료 대기
        while timeout_cnt < 100:
            status = self.i7565dnm_helper.dnm_lib.I7565DNM_IsSearchOK(self.port)
            
            if status == 0:
                search_finished = True
                break
            
            QApplication.processEvents()
            time.sleep(0.1)
            timeout_cnt += 1
            
        if not search_finished:
            self.console.add_message(MsgType.WARNING, "장치 검색 시간 초과! (네트워크 상태를 확인하세요)")
            return
            
        # 3. 검색 결과 가져오기
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
                QMessageBox.information(self, "검색 결과", "검색된 장치가 없습니다.")
            else:
                self.console.add_message(MsgType.INFO, f"=> 스캔 완료! 총 {count}개의 Slave 장치가 응답했습니다.")
                
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
                    self.console.add_message(MsgType.INFO, f"  [{i+1}] MAC ID: {dev_info['mac']:02d} | Type: 0x{dev_info['type']:02X}")
        else:
            self.console.add_message(MsgType.ERROR, f"검색 결과 가져오기 실패 (코드: {res})")
        