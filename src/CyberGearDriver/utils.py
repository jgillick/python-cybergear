import struct
from numbers import Real
from typing import Tuple
from CyberGearDriver.constants import DataType


def float_to_uint(value: float, range_min: float, range_max: float, bits: int) -> int:
    """
    Converts a floating-point number into an unsigned integer with a specified bit depth while respecting a given range.

    For example: If you call float_to_uint(0.5, 0.0, 1.0, 8):
      - You're converting 0.5 in the range [0.0, 1.0] to an 8-bit integer
      - It would return 127, which is halfway between 0 and 255
    """
    span = range_max - range_min
    offset = range_min
    if value > range_max:
        value = range_max
    elif value < range_min:
        value = range_min
    return int((value - offset) * ((1 << bits) - 1) / span)


def uint_to_float(value: int, value_min: float, value_max: float) -> float:
    """
    This is the opposite of float_to_uint. It takes an unsigned integer received from the CAN bus and
    converts it back into a floating point number
    """
    int_max = 0xFFFF
    span = value_max - value_min
    return value / int_max * span + value_min


def extract_type(data: bytearray, to_type: DataType) -> Real:
    """
    Extract a data type encoded into a byte array
    """
    if to_type == DataType.UINT8:
        return data[0]
    elif to_type == DataType.INT16:
        return struct.unpack("<h", data[0:2])[0]
    elif to_type == DataType.UINT16:
        return struct.unpack("<H", data[0:2])[0]
    elif to_type == DataType.INT32:
        return struct.unpack("<i", data[0:4])[0]
    elif to_type == DataType.UINT32:
        return struct.unpack("<I", data[0:4])[0]
    elif to_type == DataType.FLOAT:
        return struct.unpack("<f", data[0:4])[0]
    return 0


def encode_to_bytes(
    value: Real,
    from_type: DataType,
    range: Tuple[Real, Real] = None,
) -> bytearray:
    # Clamp value to range
    if range is not None:
        (min, max) = range
        if value > max:
            value = max
        elif value < min:
            value = min

    # Encode types
    data = bytearray(4)
    if from_type == DataType.UINT8:
        data[0] = value
    elif from_type == DataType.INT16:
        data[0:2] = struct.pack("<h", value)
    elif from_type == DataType.UINT16:
        data = bytearray(2)
        data[0:2] = struct.pack("<H", value)
    elif from_type == DataType.INT32:
        data = bytearray(2)
        data[0:4] = struct.pack("<i", value)
    elif from_type == DataType.UINT32:
        data[0:4] = struct.pack("<I", value)
    elif from_type == DataType.FLOAT:
        data[0:4] = struct.pack("<f", float(value))
    return data
