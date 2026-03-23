import ctypes
from enum import Enum, auto
from PySide6.QtCore import QObject, Signal, Slot, QTimer

# I7565DNM API 에러 코드
I7565DNM_NO_ERROR = 0
DNMXS_NOW_SCANNING = 1055

# =========================================================================
# 🚦 워커 상태 정의 (State Machine)
# =========================================================================
class WorkerState(Enum):
    DISCONNECTED = auto()  # 포트 닫힘 (초기 상태)
    READY = auto()         # 마스터 포트 열림 (슬레이브 미지정)
    SCANNING = auto()      # 네트워크 스캔 중 (모든 통신 차단)
    ONLINE = auto()        # 타겟 슬레이브 지정됨 (Explicit 통신 가능, 폴링 대기)
    POLLING = auto()       # 타겟 슬레이브와 I/O 폴링 진행 중


class DnetWorker(QObject):
    # =========================================================================
    # 📡 SIGNALS
    # =========================================================================
    log_msg_signal = Signal(str, str)
    state_changed_signal = Signal(str)              # UI에 현재 상태명 전달
    
    poll_rx_signal = Signal(int, int, bytes)        # (mac_id, con_type, raw_bytes)
    explicit_rx_signal = Signal(int, bytes)         # (mac_id, raw_bytes)
    device_search_complete_signal = Signal(list)    # found_devices 리스트

    def __init__(self, dll_path: str = "./x64/I7565DNM.dll"):
        super().__init__()
        self.dll_path = dll_path
        self.dll = None
        self.current_port = 1
        
        self.target_mac_id = None
        self.poll_interval = 100
        
        # FSM 상태 초기화
        self.state = WorkerState.DISCONNECTED
        self.pre_scan_state = WorkerState.READY
        
        # 타이머 초기화 (시작/정지는 오직 _transition_to 에서만 제어됨)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._read_poll_in_data)
        
        self.explicit_timer = QTimer(self)
        self.explicit_timer.timeout.connect(self._check_explicit_response)
        
        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._check_search_status)


    # =========================================================================
    # 🚦 FSM 엔진: 상태 전이 및 타이머 제어 (Centralized State Transition)
    # =========================================================================
    def _transition_to(self, new_state: WorkerState):
        """
        상태 전이를 수행하고, 상태에 맞는 [Exit] 및 [Entry] 액션을 처리합니다.
        """
        self.log_msg_signal.emit("INFO", f"상태 변경: {self.state.name} -> {new_state.name}")

        if self.state == new_state:
            return

        old_state = self.state
        self.state = new_state

        # -------------------------------------------------------------
        # [EXIT Actions] 이전 상태를 빠져나갈 때의 정리 작업
        # -------------------------------------------------------------
        if old_state == WorkerState.POLLING and new_state != WorkerState.POLLING:
            self.poll_timer.stop()
            
        if old_state == WorkerState.SCANNING and new_state != WorkerState.SCANNING:
            self.search_timer.stop()
            
        # 슬레이브와의 연결을 벗어날 때 (ONLINE/POLLING -> READY/DISCONNECTED)
        if old_state in (WorkerState.ONLINE, WorkerState.POLLING) and new_state not in (WorkerState.ONLINE, WorkerState.POLLING):
            self.explicit_timer.stop()

        # -------------------------------------------------------------
        # [ENTRY Actions] 새로운 상태로 진입할 때의 시작 작업
        # -------------------------------------------------------------
        if new_state == WorkerState.DISCONNECTED:
            self.target_mac_id = None
            
        elif new_state == WorkerState.READY:
            self.target_mac_id = None

        elif new_state == WorkerState.SCANNING:
            self.search_timer.start(500)

        elif new_state == WorkerState.ONLINE:
            if not self.explicit_timer.isActive():
                self.explicit_timer.start(20)

        elif new_state == WorkerState.POLLING:
            if not self.explicit_timer.isActive():
                self.explicit_timer.start(20)
            self.poll_timer.start(self.poll_interval)

        # 로그 및 상태 변경 알림
        self.log_msg_signal.emit("INFO", f"[상태 변경] {old_state.name} -> {new_state.name}")
        self.state_changed_signal.emit(self.state.name)


    # =========================================================================
    # 🎯 SLOTS: 초기화 및 마스터 모듈 제어
    # =========================================================================
    @Slot()
    def initialize(self):
        try:
            self.dll = ctypes.WinDLL(self.dll_path)
            self._setup_argtypes()
            self.log_msg_signal.emit("INFO", "I7565DNM DLL 로드 성공")
        except Exception as e:
            self.log_msg_signal.emit("ERROR", f"DLL 로드 실패: {e}")

    @Slot(int)
    def connect_module(self, port: int):
        if self.state != WorkerState.DISCONNECTED or not self.dll:
            self.log_msg_signal.emit("WARNING", "현재 상태에서는 마스터를 연결할 수 없습니다.")
            return

        res = self.dll.I7565DNM_ActiveModule(port)
        if res == I7565DNM_NO_ERROR:
            self.current_port = port
            self._transition_to(WorkerState.READY)
        else:
            self.log_msg_signal.emit("ERROR", f"포트 연결 실패 (코드: {res})")

    @Slot()
    def disconnect_module(self):
        if self.state == WorkerState.DISCONNECTED or not self.dll:
            return

        self._transition_to(WorkerState.DISCONNECTED)
        self.dll.I7565DNM_CloseModule(self.current_port)


    # =========================================================================
    # 🎯 SLOTS: 슬레이브 연결 관리
    # =========================================================================
    @Slot(int)
    def connect_slave(self, mac_id: int):
        if self.state != WorkerState.READY:
            self.log_msg_signal.emit("WARNING", f"현재 상태({self.state.name})에서는 슬레이브를 지정할 수 없습니다. (READY 상태 필요)")
            return

        self.target_mac_id = mac_id
        self._transition_to(WorkerState.ONLINE)

    @Slot()
    def disconnect_slave(self):
        if self.state not in (WorkerState.ONLINE, WorkerState.POLLING):
            self.log_msg_signal.emit("WARNING", f"현재 상태({self.state.name})에서는 해제할 슬레이브가 없습니다.")
            return
            
        self._transition_to(WorkerState.READY)


    # =========================================================================
    # 🎯 SLOTS: 네트워크 스캔 제어
    # =========================================================================
    @Slot()
    def search_devices(self):
        self.log_msg_signal.emit("INFO", f"스캔 시작")

        if self.state in (WorkerState.DISCONNECTED, WorkerState.SCANNING) or not self.dll:
            self.log_msg_signal.emit("WARNING", f"현재 상태({self.state.name})에서는 스캔을 시작할 수 없습니다.")
            return

        self.pre_scan_state = self.state 
        self._transition_to(WorkerState.SCANNING)

        res = self.dll.I7565DNM_SearchAllDevices(self.current_port)
        if res == I7565DNM_NO_ERROR or res == DNMXS_NOW_SCANNING:
            self.log_msg_signal.emit("INFO", "네트워크 스캔 시작...")
        else:
            self.log_msg_signal.emit("ERROR", f"네트워크 스캔 시작 실패 (코드: {res})")
            self._transition_to(self.pre_scan_state) # 실패 시 즉시 롤백

    @Slot()
    def stop_search(self):
        if self.state != WorkerState.SCANNING:
            return
            
        self.log_msg_signal.emit("INFO", "스캔 강제 중지. 이전 상태로 복구합니다.")
        self._transition_to(self.pre_scan_state)


    # =========================================================================
    # 🎯 SLOTS: 폴링 및 송수신 (State를 변경하지 않는 Action들)
    # =========================================================================
    @Slot(int)
    def start_polling(self, interval_ms: int):
        if self.state != WorkerState.ONLINE:
            self.log_msg_signal.emit("WARNING", f"현재 상태({self.state.name})에서는 폴링을 시작할 수 없습니다.")
            return

        self.poll_interval = interval_ms
        self._transition_to(WorkerState.POLLING)

    @Slot()
    def stop_polling(self):
        if self.state != WorkerState.POLLING:
            return
            
        self._transition_to(WorkerState.ONLINE)

    @Slot(bytes)
    def write_poll_out_data(self, data: bytes):
        if self.state not in (WorkerState.ONLINE, WorkerState.POLLING):
            self.log_msg_signal.emit("WARNING", "통신 가능한 슬레이브가 없습니다.")
            return

        data_len = len(data)
        data_buffer = (ctypes.c_uint8 * data_len)(*data)

        res = self.dll.I7565DNM_WriteOutputData(
            self.current_port, self.target_mac_id, 1, data_len, data_buffer
        )

        if res == I7565DNM_NO_ERROR:
            self.log_msg_signal.emit("TX", f"[Poll Out] 버퍼 갱신 성공 ({data.hex().upper()})")
        else:
            self.log_msg_signal.emit("ERROR", f"[Poll Out] 버퍼 갱신 실패 (코드: {res})")

    @Slot(int, int, int, bytes)
    def send_explicit_msg(self, service_id: int, class_id: int, instance_id: int, data: bytes):
        if self.state not in (WorkerState.ONLINE, WorkerState.POLLING):
            self.log_msg_signal.emit("WARNING", "통신 가능한 슬레이브가 없습니다.")
            return
            
        data_len = len(data)
        data_buffer = (ctypes.c_uint8 * data_len)(*data)
        
        res = self.dll.I7565DNM_SendExplicitMSG(
            self.current_port, self.target_mac_id, service_id, class_id, instance_id, data_len, data_buffer
        )
        
        if res == I7565DNM_NO_ERROR:
            self.log_msg_signal.emit("TX", f"[Explicit] 요청 전송 완료")
        else:
            self.log_msg_signal.emit("ERROR", f"[Explicit] 요청 전송 실패 (코드: {res})")


    # =========================================================================
    # 🔄 INTERNAL: 타이머 콜백
    # =========================================================================
    def _read_poll_in_data(self):
        if self.state != WorkerState.POLLING or not self.dll:
            return

        io_len = ctypes.c_uint16(0)
        io_data_buffer = (ctypes.c_uint8 * 256)()
        res = self.dll.I7565DNM_ReadInputData(
            self.current_port, self.target_mac_id, 1, ctypes.byref(io_len), io_data_buffer
        )
        if res == I7565DNM_NO_ERROR and io_len.value > 0:
            self.poll_rx_signal.emit(self.target_mac_id, 1, bytes(io_data_buffer[:io_len.value]))

    def _check_explicit_response(self):
        if self.state not in (WorkerState.ONLINE, WorkerState.POLLING) or not self.dll:
            return

        res_is_ok = self.dll.I7565DNM_IsExplicitMSGRespOK(self.current_port, self.target_mac_id)
        if res_is_ok == I7565DNM_NO_ERROR:
            exp_len = ctypes.c_uint16(0)
            exp_data_buffer = (ctypes.c_uint8 * 256)()
            res_exp_val = self.dll.I7565DNM_GetExplicitMSGRespValue(
                self.current_port, self.target_mac_id, ctypes.byref(exp_len), exp_data_buffer
            )
            if res_exp_val == I7565DNM_NO_ERROR and exp_len.value > 0:
                self.explicit_rx_signal.emit(self.target_mac_id, bytes(exp_data_buffer[:exp_len.value]))

    def _check_search_status(self):
        if self.state != WorkerState.SCANNING or not self.dll:
            self.log_msg_signal.emit("INFO", f"스캔 진행 오류")
            return

        res = self.dll.I7565DNM_IsSearchOK(self.current_port)

        self.log_msg_signal.emit("INFO", f"스캔 진행 중 {res}")

        if res == DNMXS_NOW_SCANNING:
            return
            
        if res == I7565DNM_NO_ERROR:
            total_devices = ctypes.c_uint16(0)
            mac_ids = (ctypes.c_uint8 * 64)()
            types = (ctypes.c_uint8 * 64)()
            in_lens = (ctypes.c_uint16 * 64)()
            out_lens = (ctypes.c_uint16 * 64)()
            
            res_get = self.dll.I7565DNM_GetSearchedDevices(
                self.current_port, ctypes.byref(total_devices), mac_ids, types, in_lens, out_lens
            )
            
            if res_get == I7565DNM_NO_ERROR:
                found_devices = [{"mac_id": mac_ids[i], "type": types[i], 
                                  "in_len": in_lens[i], "out_len": out_lens[i]} 
                                 for i in range(total_devices.value)]
                self.log_msg_signal.emit("INFO", f"스캔 완료: {total_devices.value}개 장비 발견")
                self.device_search_complete_signal.emit(found_devices)
            else:
                self.log_msg_signal.emit("ERROR", f"스캔 결과 로딩 실패 (코드: {res_get})")
        else:
            self.log_msg_signal.emit("ERROR", f"네트워크 스캔 오류 (코드: {res})")
            
        # 스캔이 정상/비정상 종료되면 즉시 이전 상태로 FSM 복귀
        self._transition_to(self.pre_scan_state)

    def _setup_argtypes(self):
        if not self.dll: return
        self.dll.I7565DNM_ActiveModule.argtypes = [ctypes.c_uint8]
        self.dll.I7565DNM_ActiveModule.restype = ctypes.c_uint32
        self.dll.I7565DNM_CloseModule.argtypes = [ctypes.c_uint8]
        self.dll.I7565DNM_CloseModule.restype = ctypes.c_uint32
        self.dll.I7565DNM_ReadInputData.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint8)]
        self.dll.I7565DNM_ReadInputData.restype = ctypes.c_uint32
        self.dll.I7565DNM_WriteOutputData.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16, ctypes.POINTER(ctypes.c_uint8)]
        self.dll.I7565DNM_WriteOutputData.restype = ctypes.c_uint32
        self.dll.I7565DNM_SendExplicitMSG.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16, ctypes.POINTER(ctypes.c_uint8)]
        self.dll.I7565DNM_SendExplicitMSG.restype = ctypes.c_uint32
        self.dll.I7565DNM_IsExplicitMSGRespOK.argtypes = [ctypes.c_uint8, ctypes.c_uint8]
        self.dll.I7565DNM_IsExplicitMSGRespOK.restype = ctypes.c_uint32
        self.dll.I7565DNM_GetExplicitMSGRespValue.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint8)]
        self.dll.I7565DNM_GetExplicitMSGRespValue.restype = ctypes.c_uint32
        self.dll.I7565DNM_SearchAllDevices.argtypes = [ctypes.c_uint8]
        self.dll.I7565DNM_SearchAllDevices.restype = ctypes.c_uint32
        self.dll.I7565DNM_IsSearchOK.argtypes = [ctypes.c_uint8]
        self.dll.I7565DNM_IsSearchOK.restype = ctypes.c_uint32
        self.dll.I7565DNM_GetSearchedDevices.argtypes = [ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint16)]
        self.dll.I7565DNM_GetSearchedDevices.restype = ctypes.c_uint32