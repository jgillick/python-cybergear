import time
import struct
import traceback
from numbers import Real
from typing import Callable

from CyberGearDriver.can import CyberMotorMessage
from CyberGearDriver.utils import (
    float_to_uint,
    uint_to_float,
    extract_type,
    encode_to_bytes,
)
from CyberGearDriver.event_emitter import EventEmitter
from CyberGearDriver.parameters import (
    ConfigName,
    ParameterName,
    get_parameter_by_name,
    get_parameter_by_addr,
    get_config_by_addr,
    get_config_by_name,
)
from CyberGearDriver.constants import (
    Command,
    RunMode,
    DataType,
    DEFAULT_HOST_CAN_ID,
    KD_MAX,
    KD_MIN,
    KP_MAX,
    KP_MIN,
    P_MAX,
    P_MIN,
    T_MAX,
    T_MIN,
    V_MAX,
    V_MIN,
    PAUSE_AFTER_SEND,
)


class CyberGearMotor(EventEmitter):
    """CyberGear motor controller"""

    # The motor ID on the CAN bus
    motor_id: int

    # The host ID on the CAN bus
    host_id: int

    # Motor state
    state: dict

    # Motor configuration parameters that are retained after power down (ID: 0x0000 - 0x302F)
    config: dict

    # Motor parameters stored in RAM (ID: 0x7005 - 0x7020)
    params: dict

    # Collection of possible fault messages and their True/False
    faults: dict

    # Whether to output verbose logging
    verbose: bool

    def __init__(
        self,
        motor_id: int,
        send_message: Callable[[CyberMotorMessage], None],
        host_id: int = DEFAULT_HOST_CAN_ID,
        verbose: bool = False,
    ) -> None:
        self.motor_id = motor_id
        self.host_id = host_id
        self.send_message = send_message
        self.verbose = verbose

        self.params = {}
        self.config = {}
        self.state = {}
        self.faults = {}

        super().__init__()

    def enable(self):
        """Enable the motor for commands. This needs to be called before any other commands."""
        self._send(Command.ENABLE)

    def stop(self):
        """Disable the motor."""
        self._send(Command.STOP, extended_data=self.host_id)

    def mode(self, mode: RunMode):
        """Set the motor run mode"""
        self.set_parameter("run_mode", mode.value)

    def set_zero_position(self):
        """Set the current motor position as the zero position"""
        data = bytearray(8)
        data[0] = 1
        self._send(Command.SET_ZERO, data=data)

    def request_motor_state(self):
        """Request the current motor state"""
        self._send(Command.STATE)

    def request_motor_fault_status(self):
        """Request any active faults from the motor"""
        self._send(Command.FAULT)

    def control(
        self, position: float, velocity: float, torque: float, kp: float, kd: float
    ):
        """
        Operation control mode, or also called MIT mode.
        Sets the position, velocity, torque, kp, and kd values.
        """
        data = bytearray(8)

        # Convert values
        position_value = float_to_uint(position, P_MIN, P_MAX, 16)
        velocity_value = float_to_uint(velocity, V_MIN, V_MAX, 16)
        kp_value = float_to_uint(kp, KP_MIN, KP_MAX, 16)
        kd_value = float_to_uint(kd, KD_MIN, KD_MAX, 16)

        # Pack the data as big-endian 16-bit values ('>H')
        data = struct.pack(">HHHH", position_value, velocity_value, kp_value, kd_value)

        # Torque data
        torque_value = float_to_uint(torque, T_MIN, T_MAX, 16)

        # Send
        self._send(Command.POSITION, data=data, extended_data=torque_value)

    def set_parameter(self, param_name: ParameterName, value: Real):
        """Send a parameter value to the motor"""
        try:
            param = get_parameter_by_name(param_name)
        except:
            self._log(f"ERROR: Could not find parameter by name: '{param_name}'")
            return
        (addr, _name, data_type, range, permission) = param
        if permission != "rw":
            self._log(f"ERROR: Cannot write to parameter '{param_name}'")
            return

        # Create message data
        data = bytearray(4)
        data[0] = addr & 0x00FF
        data[1] = addr >> 8
        data[2] = 0x00
        data[3] = 0x00

        # Encode types
        encoded_value = encode_to_bytes(value, data_type, range)
        data.extend(encoded_value)

        self._send(Command.WRITE_PARAM, data=data)

    def set_config(self, name: ConfigName, value: Real):
        """Send a config value to the motor"""
        try:
            config = get_config_by_name(name)
        except:
            self._log(f"ERROR: Could not find config config by name: '{name}'")
            return
        (addr, _name, data_type, range, permission) = config
        if permission != "rw":
            self._log(f"ERROR: Cannot write to config value '{name}'")
            return

        # Create message data
        data = bytearray(4)
        data[0] = addr & 0x00FF
        data[1] = addr >> 8
        data[2] = data_type.value
        data[3] = 0x00

        # Encode types
        encoded_value = encode_to_bytes(value, data_type, range)
        data.extend(encoded_value)

        self._send(Command.WRITE_PARAM, data=data)

    def request_parameter(self, param_name: ParameterName):
        """Send a request to receive a motor parameter"""
        try:
            param = get_parameter_by_name(param_name)
        except:
            self._log(f"ERROR: Could not find parameter by name: '{param_name}'")
            return
        addr = param[0]

        # Copy the parameter value (as bytes) into the first 2 bytes of data
        data = bytearray(8)
        data[0:2] = addr.to_bytes(2, byteorder="little")

        # Send
        self._log(f"Send: {Command.READ_PARAM.name} - {param_name}")
        self._send(Command.READ_PARAM, data=data, log=False)

    def request_config(self, name: ConfigName):
        """Send a request to receive a motor config parameter value"""
        try:
            config = get_config_by_name(name)
        except:
            self._log(f"ERROR: Could not find a config parameter by name: '{name}'")
            return
        addr = config[0]

        # Copy the parameter value (as bytes) into the first 2 bytes of data
        data = bytearray(8)
        data[0:2] = addr.to_bytes(2, byteorder="little")

        # Send
        self._log(f"Send: {Command.READ_CONFIG.name} - {name}")
        self._send(Command.READ_CONFIG, data=data, log=True)

    def change_motor_id(self, new_motor_id: int):
        """Change the motor's ID on the CAN bus."""
        # Encode ID
        arbitration_id = 0
        arbitration_id |= self.motor_id & 0xFF  # Bits 7~0
        arbitration_id |= (self.host_id & 0xFF) << 8  # Bits 15~8
        arbitration_id |= (new_motor_id & 0xFF) << 16  # Bits 23~16
        arbitration_id |= (Command.CHANGE_CAN_ID.value & 0x1F) << 24  # Bits 28~24

        # Create message
        data = bytearray(8)
        data[0] = 1
        msg = CyberMotorMessage(
            arbitration_id=arbitration_id,
            data=data,
        )

        self.send_message(msg)
        self._log(f"Send: {Command.CHANGE_CAN_ID.name}")
        self.motor_id = new_motor_id
        time.sleep(PAUSE_AFTER_SEND)

    def message_received(self, msg: CyberMotorMessage):
        """Process a received message on the CAN bus."""

        # Parse values out of arbitration ID
        destination_id = msg.arbitration_id & 0xFF
        from_id = (msg.arbitration_id >> 8) & 0xFF

        command_num = (msg.arbitration_id >> 24) & 0x1F
        command = Command(command_num)

        extended_data = (msg.arbitration_id >> 8) & 0xFFFF
        ext_data_bytes = extended_data.to_bytes(16, "little")

        self._log(f"Received: {msg}")
        self._log(f" > {command.name} from: {from_id}, to: {destination_id}")

        # Filter out messages not from our motor
        if destination_id != self.host_id:
            return
        if from_id != self.motor_id:
            return

        if command == Command.STATE:
            self._process_received_state(msg.data, ext_data_bytes)
        elif command == Command.READ_CONFIG:
            self._processed_received_config(msg.data)
        elif command == Command.READ_PARAM:
            self._processed_received_param(msg.data)
        elif command == Command.FAULT:
            self._process_fault_data(msg.data)

    def _send(
        self,
        command: Command,
        data: bytearray = bytearray(8),
        extended_data: int = 0,
        log: bool = True,
    ):
        """Send a message to the motor."""

        # Encode ID
        id = command.value << 24 | extended_data << 8 | self.motor_id

        # Create message
        msg = CyberMotorMessage(
            arbitration_id=id,
            data=data,
        )

        # Send
        self.send_message(msg)
        if log:
            self._log(f"Send: {command.name}")
        time.sleep(PAUSE_AFTER_SEND)

    def _log(self, message: str):
        """If verbose is True, output some logging"""
        if self.verbose:
            print(message)

    def _update_faults(self, errors: dict):
        """Add/remote faults from the fault dict"""
        had_errors = len([v for v in errors.values() if v])
        for key, val in errors.items():
            self.faults[key] = val
        has_errors = len([v for v in errors.values() if v])

        if has_errors:
            self.emit("has_fault")
        elif had_errors:
            self.emit("fault_cleared")

    def _process_received_state(self, data: bytearray, ext_data: bytearray):
        """Convert the motor feedback response into the current motor state"""
        pos_data = data[1] | data[0] << 8
        vel_data = data[3] | data[2] << 8
        torque_data = data[5] | data[4] << 8

        raw_temp = data[7] | data[6] << 8
        motor_id = int.from_bytes(ext_data[0:7], byteorder="little")

        self.state["temperature"] = raw_temp / 10 if raw_temp else 0
        self.state["position"] = uint_to_float(pos_data, P_MIN, P_MAX)
        self.state["velocity"] = uint_to_float(vel_data, V_MIN, V_MAX)
        self.state["torque"] = uint_to_float(torque_data, T_MIN, T_MAX)

        # mode_status = int.from_bytes(ext_data[14:15], byteorder="little")
        # self.state["mode_status"] = ModeStatus(mode_status)

        # Errors and warnings
        faults = self.faults.copy()
        faults["Encoder not calibrated"] = bool(ext_data[13])
        faults["Hall encoder failure"] = bool(ext_data[12])
        faults["Magnetic encoder failure"] = bool(ext_data[11])
        faults["Over temperature"] = bool(ext_data[10])
        faults["Over current"] = bool(ext_data[9])
        faults["Under voltage"] = bool(ext_data[8])
        self._update_faults(faults)

        self.emit("state_changed")

        # Log state
        self._log(f" > Motor ID: {motor_id}")
        self._log(f" > Position: {self.state['position']}")
        self._log(f" > Velocity: {self.state['velocity']}")
        self._log(f" > Torque: {self.state['torque']}")

        # Log errors
        for err in self.faults:
            self._log(f" ! {err}")

    def _processed_received_param(self, data: bytearray):
        """A requested motor prarameter has been received"""
        log_name = ""
        try:
            # Get the property config by address
            addr = data[1] << 8 | data[0]
            log_name = hex(addr)
            try:
                parameter = get_parameter_by_addr(addr)
            except:
                self._log(f"ERROR: Unknown parameter address: '{hex(addr)}'")
                return
            (_addr, name, data_type, range, _permission) = parameter
            log_name = name

            # Read the value
            value = extract_type(data[4:], data_type)

            self._log(f" > {name} = {value}")
            self.params[name] = value
            self.emit("param_received", name, value)
        except Exception as e:
            traceback.print_exc()
            self._log(f"ERROR: Could not process parameter value ({log_name}): {e}")

    def _processed_received_config(self, data: bytearray):
        """A requested motor config param has been received"""
        log_name = ""
        try:
            # Get the property config by address
            addr = data[1] << 8 | data[0]
            log_name = hex(addr)
            try:
                parameter = get_config_by_addr(addr)
            except:
                self._log(f"ERROR: Unknown config address: '{hex(addr)}'")
                return
            (_addr, name, *rest) = parameter
            log_name = name

            # Get the type bit
            type_bit = data[2]
            data_type = DataType(type_bit)

            # Read the value
            value = extract_type(data[4:], data_type)

            self._log(f" > {name} = {value}")
            self.config[name] = value
            self.emit("config_received", name, value)
        except Exception as e:
            traceback.print_exc()
            self._log(f"ERROR: Could not process parameter value ({log_name}): {e}")

    def _process_fault_data(self, data: bytearray):
        """Process the fault feedback message"""
        # Extract fault value (bytes 0-3)
        fault_value = int.from_bytes(data[0:4], byteorder="little")

        # Extract individual fault bits
        faults = self.faults.copy()
        faults["Phase A over current"] = bool(fault_value & (1 << 16))
        faults["Phase B over current"] = bool(fault_value & (1 << 4))
        faults["Phase C over current"] = bool(fault_value & (1 << 5))
        faults["Overload"] = (fault_value >> 8) & 0xFF  # Bits 15-8
        faults["Encoder not calibrated"] = bool(fault_value & (1 << 7))
        faults["Over voltage"] = bool(fault_value & (1 << 3))
        faults["Under voltage"] = bool(fault_value & (1 << 2))
        faults["Driver chip"] = bool(fault_value & (1 << 1))
        faults["Over temperature"] = bool(fault_value & (1 << 0))
        self._update_faults(faults)

        # Log faults
        for err in self.faults:
            self._log(f" ! {err}")
