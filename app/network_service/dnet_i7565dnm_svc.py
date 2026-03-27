import os
import ctypes
import queue
from enum import Enum, auto
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from app.file_helper.file_helper import get_i7565dnm_dll_path
from app.ui.components.composit.console_widget import MsgType

# I7565DNM API 에러 코드
I7565DNM_NO_ERROR = 0
DNMXS_NOW_SCANNING = 1055
DNMXS_DEVICE_EXIST = 1057         # 추가
DNMXS_POLL_ALREADY_EXIST = 1105   # 추가

# --- 추가되어야 할 Explicit Message 응답 상태 코드 ---
DNMXS_SLAVE_NO_RESP = 1150         # 타임아웃 (응답 없음)
DNMXS_WAIT_FOR_SLAVE_RESP = 1151   # 슬레이브 응답 대기 중
DNMXS_SLAVE_RESP_ERROR = 1152      # 슬레이브 측에서 에러 응답 보냄
# -----------------------------------------------------

# =========================================================================
# 🚦 워커 상태 정의 (State Machine)
# =========================================================================
class DnetI7565DNMSvc(QObject):
    _instance = None
    _initialized = False

    # 인스턴스 생성 제어 (싱글톤)
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DnetI7565DNMSvc, cls).__new__(cls, *args, **kwargs)
        return cls._instance    
    # =========================================================================
    # 📡 SIGNALS
    # =========================================================================
    sig_add_log                  = Signal(MsgType, str)
    sig_connect_network_finished = Signal(bool)
    sig_connect_slave_finished   = Signal(bool)
    sig_scan_slave_finished      = Signal(list)

    poll_rx_signal               = Signal(int, int, bytes)        # (mac_id, con_type, raw_bytes)
    explicit_rx_signal           = Signal(int, int, int, int, bytes, bool)         # (service_code, class_id, instance_id, attribute_id, data, is_ok)

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
            
        self.dll = None
        self.current_port = 0
        self.target_mac_id = None

        self.is_active_module = False
        self.is_add_device = False
        self.is_add_io = False
        self.is_start_device = False
        
        self.explicit_queue = queue.Queue()
        self.current_explicit_req = None  # (service_code, class, inst, attr, payload)
        self._current_explicit_req_buffer = None  # C API 메모리 참조 유지 변수

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._read_poll_in_data)
        
        self.explicit_timer = QTimer(self)
        self.explicit_timer.timeout.connect(self._process_explicit_messages)
        
        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._check_search_status)

        self._initialize()
       
    # =========================================================================
    # 🎯 SLOTS: 초기화 및 마스터 모듈 제어
    # =========================================================================
    def _initialize(self):
        self._setup_argtypes()

    @Slot(int)
    def connect_module(self, port: int):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetI7565DNMSvc] 마스터 모듈 연결")
        print("[DnetI7565DNMSvc] 마스터 모듈 연결")

        if not self._check_dll():
            self.sig_connect_network_finished.emit(False)
            return

        self.clear_all_resources()

        res = self.dll.I7565DNM_ActiveModule(port)
        if res == I7565DNM_NO_ERROR:
            self.current_port = port
            self.is_active_module = True
            self.sig_connect_network_finished.emit(True)
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"[DnetI7565DNMSvc] 포트 연결 실패 (코드: {res})")
            self.sig_connect_network_finished.emit(False)

    @Slot()
    def disconnect_module(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetI7565DNMSvc] 마스터 모듈 연결 해제")
        print("[DnetI7565DNMSvc] 마스터 모듈 연결 해제")

        if not self._check_dll():
            return

        self.clear_all_resources()


    # =========================================================================
    # 🎯 SLOTS: 네트워크 스캔 제어
    # =========================================================================
    @Slot()
    def search_devices(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetI7565DNMSvc] 스캔 시작")
        print("[DnetI7565DNMSvc] 스캔 시작")

        self.clear_resources_without_module()

        if not self._check_dll() or not self._check_module():
            self.sig_scan_slave_finished.emit([])
            return

        res = self.dll.I7565DNM_SearchAllDevices(self.current_port)
        if res == I7565DNM_NO_ERROR or res == DNMXS_NOW_SCANNING:
            self.search_timer.start(500)
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"네트워크 스캔 시작 실패 (코드: {res})")
            self.sig_scan_slave_finished.emit([])

    @Slot()
    def stop_search(self):
        self.sig_add_log.emit(MsgType.INFO, "[DnetI7565DNMSvc] 스캔 중지")

        self.clear_resources_without_module()

        if not self._check_dll():
            return

    # =========================================================================
    # 🎯 SLOTS: 슬레이브 연결 관리
    # =========================================================================
    @Slot(int, int, int)
    def connect_slave(self, mac_id: int, in_len: int, out_len: int):
        self.clear_resources_without_module()

        if not self._check_dll() or not self._check_module():
            self.sig_connect_slave_finished.emit(False)
            return

        res_add = self.dll.I7565DNM_AddDevice(self.current_port, mac_id, 2500)
        if res_add != I7565DNM_NO_ERROR and res_add != DNMXS_DEVICE_EXIST: 
            self.sig_add_log.emit(MsgType.ERROR, f"[DnetI7565DNMSvc] AddDevice 실패 (코드: {res_add})")
            self.sig_connect_slave_finished.emit(False)
            return

        self.is_add_device = True

        res_io = self.dll.I7565DNM_AddIOConnection(self.current_port, mac_id, 1, in_len, out_len, 2500)
        if res_io != I7565DNM_NO_ERROR and res_io != DNMXS_POLL_ALREADY_EXIST: 
            self.clear_resources_without_module()
            self.sig_add_log.emit(MsgType.ERROR, f"[DnetI7565DNMSvc] AddIOConnection 실패 (코드: {res_io})")
            self.sig_connect_slave_finished.emit(False)
            return

        self.is_add_io = True

        res_start = self.dll.I7565DNM_StartDevice(self.current_port, mac_id)
        if res_start != I7565DNM_NO_ERROR:
            self.clear_resources_without_module()
            self.sig_add_log.emit(MsgType.ERROR, f"[DnetI7565DNMSvc] StartDevice 실패 (코드: {res_start})")
            self.sig_connect_slave_finished.emit(False)
            return

        self.is_start_device = True

        self.sig_add_log.emit(MsgType.INFO, f"[DnetI7565DNMSvc] 슬레이브 연결 성공 (MAC ID: {mac_id})")
        self.sig_connect_slave_finished.emit(True)

        self.target_mac_id = mac_id
        self.explicit_timer.start(100)



    # =========================================================================
    # 🎯 SLOTS: 폴링 및 송수신 (State를 변경하지 않는 Action들)
    # =========================================================================
    @Slot(int)
    def start_polling(self, interval_ms: int):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetI7565DNMSvc] Polling 시작 (Interval: {interval_ms}ms)")

        if not self._check_dll() or not self._check_module() or not self._check_slave():
            return

        self.poll_timer.start(interval_ms)

    @Slot()
    def stop_polling(self):
        self.sig_add_log.emit(MsgType.INFO, "[DnetI7565DNMSvc] Polling 중지")

        self.poll_timer.stop()


    @Slot(bytes)
    def write_poll_out_data(self, data: bytes):
        if not self._check_dll() or not self._check_module() or not self._check_slave():
            return

        data_len = len(data)
        data_buffer = (ctypes.c_uint8 * data_len)(*data)

        res = self.dll.I7565DNM_WriteOutputData(
            self.current_port, self.target_mac_id, 1, data_len, data_buffer
        )

        if res == I7565DNM_NO_ERROR:
            self.sig_add_log.emit(MsgType.TX, f"{data.hex(' ').upper()}")
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"[Poll Out] 버퍼 갱신 실패 (코드: {res})")

    @Slot(int, int, int, int, bytes)
    def req_explicit(self, service_code: int, class_id: int, instance_id: int, attribute_id: int, data: bytes | None):
        if not self._check_dll() or not self._check_module() or not self._check_slave():
            return
            
        if not data:
            data = b""

        # Attribute ID가 0이 아니면, CIP 스펙에 맞게 Payload의 첫 바이트로 삽입
        if attribute_id != 0:
            data = bytes([attribute_id]) + data
            
        # [수정] 바로 전송하지 않고 큐에 요청 등록
        self.explicit_queue.put((service_code, class_id, instance_id, attribute_id, data))


    # =========================================================================
    # 🔄 INTERNAL: 타이머 콜백
    # =========================================================================
    def _read_poll_in_data(self):
        io_len = ctypes.c_uint16(0)
        io_data_buffer = (ctypes.c_uint8 * 256)()

        res = self.dll.I7565DNM_ReadInputData(
            self.current_port, self.target_mac_id, 1, ctypes.byref(io_len), io_data_buffer
        )
        if res == I7565DNM_NO_ERROR and io_len.value > 0:
            self.sig_add_log.emit(MsgType.RX, f"{bytes(io_data_buffer[:io_len.value]).hex(' ').upper()}")
            self.poll_rx_signal.emit(self.target_mac_id, 1, bytes(io_data_buffer[:io_len.value]))
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"[Poll In] 데이터 읽기 실패 (코드: {res}) port: {self.current_port}, mac_id: {self.target_mac_id}")

    def _process_explicit_messages(self):
        # ---------------------------------------------------------
        # [상태 1] 현재 진행 중인 요청이 없을 때: 큐에서 새로 꺼내어 전송
        # ---------------------------------------------------------
        if self.current_explicit_req is None:
            try:
                req = self.explicit_queue.get_nowait()  # 💡 블로킹 없이 가져오기 시도
            except queue.Empty:
                return  # 보낼 메시지가 없음
                
            # 큐에서 하나 꺼내기
            service_code, class_id, instance_id, attribute_id, data = req
            
            data_len = len(data)
            if data_len > 0:
                data_buffer = (ctypes.c_uint8 * data_len)(*data)
            else:
                data_buffer = ctypes.POINTER(ctypes.c_uint8)()
            
            # 메모리가 함수 종료 후 정리되지 않도록 참조 유지
            self._current_explicit_req_buffer = data_buffer

            # 1. 8-bit Class/Instance 지원 API (일반적인 슬레이브용)
            res = self.dll.I7565DNM_SendExplicitMSG(
                self.current_port, self.target_mac_id, service_code, class_id, instance_id, data_len, data_buffer
            )

            if res == I7565DNM_NO_ERROR:
                self.current_explicit_req = req  # 전송 성공 시에만 현재 요청으로 등록
                data_hex = f" [Payload: {data.hex(' ').upper()}]" if data_len > 0 else ""
                self.sig_add_log.emit(MsgType.TX, f"[Explicit] Svc 0x{service_code} Cls 0x{class_id} Inst 0x{instance_id} Attr 0x{attribute_id} 전송{data_hex}")
            else:
                self.sig_add_log.emit(MsgType.ERROR, f"[Explicit] 전송 실패 (코드: {res}) Svc 0x{service_code} Cls 0x{class_id} Inst 0x{instance_id} Attr 0x{attribute_id} 전송{data_hex}")
                # 에러 시그널을 UI로 보내 실패 처리
                self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, b"", False)
            
            return  # 이번 틱(Tick)은 전송을 수행했으므로 응답 확인은 다음 틱으로 넘김

        # ---------------------------------------------------------
        # [상태 2] 현재 진행 중인 요청이 있을 때: 응답 또는 타임아웃 확인
        # ---------------------------------------------------------
        res_is_ok = self.dll.I7565DNM_IsExplicitMSGRespOK(self.current_port, self.target_mac_id)
        
        if res_is_ok == DNMXS_WAIT_FOR_SLAVE_RESP:
            return  # 아직 응답 대기 중
            
        # 응답 완료, 타임아웃 또는 에러 발생 시 현재 요청 정보 꺼내기
        service_code, class_id, instance_id, attribute_id, data = self.current_explicit_req
        self.current_explicit_req = None  # 큐의 다음 요청이 처리될 수 있도록 상태 비우기
        self._current_explicit_req_buffer = None  # 포인터 생존 제약 해제
        
        if res_is_ok == I7565DNM_NO_ERROR:
            exp_len = ctypes.c_uint16(0)
            exp_data_buffer = (ctypes.c_uint8 * 256)()
            res_exp_val = self.dll.I7565DNM_GetExplicitMSGRespValue(
                self.current_port, self.target_mac_id, ctypes.byref(exp_len), exp_data_buffer
            )
            if res_exp_val == I7565DNM_NO_ERROR:
                rx_bytes = bytes(exp_data_buffer[:exp_len.value])
                # [핵심] 어느 요청에 대한 응답인지 class, instance, attribute 값을 함께 전달
                self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, rx_bytes, True)
                if exp_len.value > 0:
                    self.sig_add_log.emit(MsgType.RX, f"[Explicit] 정상 수신: {rx_bytes.hex(' ').upper()}")
                else:
                    self.sig_add_log.emit(MsgType.RX, f"[Explicit] 정상 수신 (데이터 없음)")
            else:
                self.sig_add_log.emit(MsgType.ERROR, f"[Explicit] 데이터 읽기 실패 (코드: {res_exp_val})")
                self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, b"", False)

        elif res_is_ok == DNMXS_SLAVE_NO_RESP:
            self.sig_add_log.emit(MsgType.ERROR, f"[Explicit] 타임아웃 (Class:{class_id} Inst:{instance_id})")
            self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, b"", False)
            
        elif res_is_ok == DNMXS_SLAVE_RESP_ERROR:
            exp_len = ctypes.c_uint16(0)
            exp_data_buffer = (ctypes.c_uint8 * 256)()
            res_exp_val = self.dll.I7565DNM_GetExplicitMSGRespValue(
                self.current_port, self.target_mac_id, ctypes.byref(exp_len), exp_data_buffer
            )
            
            error_details = ""
            if res_exp_val == I7565DNM_NO_ERROR and exp_len.value > 0:
                # 슬레이브가 보낸 에러 바이트 (예: [0x02, 0x00] -> Resource Unavailable)
                error_bytes = bytes(exp_data_buffer[:exp_len.value])
                error_details = f" (상세 에러 Hex: {error_bytes.hex(' ').upper()})"

            self.sig_add_log.emit(MsgType.ERROR, f"[Explicit] 슬레이브 거부{error_details} - Cls:{class_id} Inst:{instance_id}")
            self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, b"", False)
            
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"[Explicit] 알 수 없는 에러 (코드: {res_is_ok})")
            self.explicit_rx_signal.emit(service_code, class_id, instance_id, attribute_id, b"", False)

    def _check_search_status(self):
        res = self.dll.I7565DNM_IsSearchOK(self.current_port)

        self.sig_add_log.emit(MsgType.INFO, f"스캔 진행 중 {res}")

        if res == DNMXS_NOW_SCANNING:
            return

        self.search_timer.stop()
            
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
                self.sig_add_log.emit(MsgType.INFO, f"스캔 완료: {total_devices.value}개 장비 발견")
                self.sig_scan_slave_finished.emit(found_devices)
            else:
                self.sig_add_log.emit(MsgType.ERROR, f"스캔 결과 로딩 실패 (코드: {res_get})")
        else:
            self.sig_add_log.emit(MsgType.ERROR, f"네트워크 스캔 오류 (코드: {res})")

    def _setup_argtypes(self) -> bool:
        if self.dll: return True
        try:
            self.dll = ctypes.WinDLL(get_i7565dnm_dll_path())
            self.dll.I7565DNM_ActiveModule.argtypes = [ctypes.c_uint8]
            self.dll.I7565DNM_ActiveModule.restype = ctypes.c_uint32
            self.dll.I7565DNM_CloseModule.argtypes = [ctypes.c_uint8]
            self.dll.I7565DNM_CloseModule.restype = ctypes.c_uint32
            self.dll.I7565DNM_ReadInputData.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint8)]
            self.dll.I7565DNM_ReadInputData.restype = ctypes.c_uint32
            self.dll.I7565DNM_WriteOutputData.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16, ctypes.POINTER(ctypes.c_uint8)]
            self.dll.I7565DNM_WriteOutputData.restype = ctypes.c_uint32
            
            # 원래의 8-bit 함수 매핑 (Class, Inst가 8-bit)
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
            self.dll.I7565DNM_AddDevice.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16]
            self.dll.I7565DNM_AddDevice.restype = ctypes.c_uint32
            self.dll.I7565DNM_AddIOConnection.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16]
            self.dll.I7565DNM_AddIOConnection.restype = ctypes.c_uint32
            self.dll.I7565DNM_StartDevice.argtypes = [ctypes.c_uint8, ctypes.c_uint8]
            self.dll.I7565DNM_StartDevice.restype = ctypes.c_uint32
            self.dll.I7565DNM_StopDevice.argtypes = [ctypes.c_uint8, ctypes.c_uint8]
            self.dll.I7565DNM_StopDevice.restype = ctypes.c_uint32
            self.dll.I7565DNM_RemoveDevice.argtypes = [ctypes.c_uint8, ctypes.c_uint8]
            self.dll.I7565DNM_RemoveDevice.restype = ctypes.c_uint32
            self.dll.I7565DNM_RemoveIOConnection.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]
            self.dll.I7565DNM_RemoveIOConnection.restype = ctypes.c_uint32
            #self.sig_add_log.emit(MsgType.INFO, "DLL 로드 성공")
        except Exception as e:
            #self.sig_add_log.emit(MsgType.ERROR, f"DLL 로드 실패: {e}")
            self.dll = None
            return False
        return True

    def _check_dll(self) -> bool:
        if not self.dll:
            self.sig_add_log.emit(MsgType.ERROR, "[DnetI7565DNMSvc] DLL이 로드되지 않았습니다.")
            return False
        return True
    
    def _check_module(self) -> bool:
        if self.current_port == 0:
            self.sig_add_log.emit(MsgType.ERROR, "[DnetI7565DNMSvc] 마스터 모듈이 연결되지 않았습니다.")
            return False
        return True

    def _check_slave(self) -> bool:
        if self.target_mac_id is None:
            self.sig_add_log.emit(MsgType.ERROR, "[DnetI7565DNMSvc] 슬레이브가 지정되지 않았습니다.")
            return False
        return True 

    def clear_resources_without_module(self):
        print("[DnetI7565DNMSvc] clear_resources_without_module")
        self.poll_timer.stop()
        self.explicit_timer.stop()
        self.search_timer.stop()
        
        if self.dll and self.target_mac_id is not None and self.current_port != 0:
            if self.is_start_device:
                self.dll.I7565DNM_StopDevice(self.current_port, self.target_mac_id)
                self.is_start_device = False
            if self.is_add_io:
                self.dll.I7565DNM_RemoveIOConnection(self.current_port, self.target_mac_id, 1)
                self.is_add_io = False
            if self.is_add_device:
                self.dll.I7565DNM_RemoveDevice(self.current_port, self.target_mac_id)
                self.is_add_device = False

        self.current_explicit_req = None
        self.explicit_queue = queue.Queue()
        self.target_mac_id = None
        self.sig_add_log.emit(MsgType.INFO, "[DnetI7565DNMSvc] 리소스 초기화")

    def clear_all_resources(self):
        print("[DnetI7565DNMSvc] clear_all_resources")
        self.clear_resources_without_module()
        if self.dll and self.current_port != 0:
            if self.is_active_module:
                self.dll.I7565DNM_CloseModule(self.current_port)
                self.is_active_module = False
        self.current_port = 0
        
        self.sig_add_log.emit(MsgType.INFO, "[DnetI7565DNMSvc] 모든 리소스 초기화")        