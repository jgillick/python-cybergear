from typing import Literal
from enum import Enum

DEFAULT_HOST_CAN_ID = 0
PAUSE_AFTER_SEND = 0.01

P_MIN = -12.5
P_MAX = 12.5
V_MIN = -30.0
V_MAX = 30.0
KP_MIN = 0.0
KP_MAX = 500.0
KD_MIN = 0.0
KD_MAX = 5.0
T_MIN = -12.0
T_MAX = 12.0
IQ_MIN = -27.0
IQ_MAX = 27.0

READ_ONLY = "r"
READ_WRITE = "rw"


class DataType(Enum):
    UINT8 = 0x00
    UINT16 = 0x02
    INT16 = 0x03
    UINT32 = 0x04
    INT32 = 0x05
    FLOAT = 0x06
    STRING = 0x0A


class RunMode(Enum):
    OPERATION_CONTROL = 0
    POSITION = 1
    VELOCITY = 2
    TORQUE = 3


class Command(Enum):
    GET_DEVICE_ID = 0
    POSITION = 1
    STATE = 2
    ENABLE = 3
    STOP = 4
    SET_ZERO = 6
    CHANGE_CAN_ID = 7
    WRITE_CONFIG = 8
    READ_CONFIG = 9
    READ_PARAM = 17
    WRITE_PARAM = 18
    FAULT = 21
