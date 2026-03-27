import struct
from decimal import Decimal

def format_sigfigs_no_e(val, sigfigs=6):
    # 1. g 포맷으로 '유효숫자 적용' 및 '불필요한 0 제거'를 먼저 수행
    g_str = f"{val:.{sigfigs}g}"
    
    # 2. Decimal을 이용해 과학적 표기법(e)을 일반 소수점 형태(f)로 강제 변환
    # (g_str에서 이미 필요한 반올림과 0 제거가 끝났으므로 모양만 바꿔줍니다)
    result = format(Decimal(g_str), 'f')
    
    return result

def format_sigfigs_width_hex(type:str, buffer:bytes, sigfigs=6):
    hex_str : str = "0x" + buffer.hex(' ').upper()
    parsed_str : str = ""
    val = 0

    if type == "uint8":
        val = struct.unpack('<B', buffer)[0]
        parsed_str = str(val)
    elif type == "int8":
        val = struct.unpack('<b', buffer)[0]
        parsed_str = str(val)
    elif type == "uint16":
        val = struct.unpack('<H', buffer)[0]
        parsed_str = str(val)
    elif type == "int16":
        val = struct.unpack('<h', buffer)[0]
        parsed_str = str(val)
    elif type == "uint32":
        val = struct.unpack('<I', buffer)[0]
        parsed_str = str(val)
    elif type == "int32":
        val = struct.unpack('<i', buffer)[0]
        parsed_str = str(val)
    elif type == "float":
        val = struct.unpack('<f', buffer)[0]
        parsed_str = format_sigfigs_no_e(val, sigfigs)
    
    return val, f"{hex_str} ({parsed_str})"