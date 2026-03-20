import ctypes
import os
import sys
import re

class i7565dnm_helper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(i7565dnm_helper, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.dnm_lib = None

    def load_dll(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(current_dir, "x64", "I7565DNM.dll")
        
        try:
            self.dnm_lib = ctypes.WinDLL(dll_path)
            
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

            return "DLL 로드 성공"
            
        except OSError as e:
            return "DLL 로드 실패";

    def search_slave(self):
        pass