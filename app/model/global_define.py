from enum import Enum

class NetworkType(str, Enum):
    DNET = 'Device Net'
    RS232 = 'RS232'
    RS485 = 'RS485'
    ETHERNET = 'EtherNet'