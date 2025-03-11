# Python CyberGear Motor Driver

A python driver for the [CyberGear motor](https://openelab.io/blogs/learn/what-is-xiaomi-cybergear-micromotor).

[CyberGear user manual](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-3.-debugger-usage-instructions-download-link-below)

## Getting started

Install the package from pip:

```bash
pip install CyberGearDriver
```

## CAN Interface

Since there are so many CAN interfaces available, this library doesn't have a built-in CAN driver but provides a simple method to connect it to your CAN library of choice.

For example, using a Serial CAN USB adapter with `python-can` would look something like this:

```python
import can
from CyberGearDriver import CyberGearMotor, RunMode, CyberMotorMessage

# Connect to the bus with python-can
# @see https://python-can.readthedocs.io/en/stable/installation.html
bus = can.interface.Bus(
    interface='slcan',
    channel='/dev/cu.usbmodem101',
    bitrate=1000000,
)

# Create function to pass the messages from CyberGear to the CAN bus
def send_message(message: CyberMotorMessage):
    bus.send(
        can.Message(
            arbitration_id=message.arbitration_id,
            data=message.data,
            is_extended_id=message.is_extended_id,
        )
    )

# Create the motor controller
motor = CyberGearMotor(motor_id=127, send_message=send_message)

# Send the CyberGear driver messages received from the CAN bus
notifier = can.Notifier(bus, [motor.message_received])
```

## Moving the motor

The motor has 4 different drive modes:

1. Operation control mode (sometimes call MIT control mode)
2. Position mode
3. Velocity mode
4. Torque mode (or current mode)

### Operation Control Mode

This is sometimes called MIT mode and combines position, speed, and torque to move the motor in a single function:

```python
motor.enable()
motor.mode(RunMode.OPERATION_CONTROL)

# Move the motor to position 6 (in radians from the zero position)
motor.control(position=6, velocity=0, torque=0, kp=0.1, kd=0.1)
```

[Full example](./examples/operation_control_mode.py)

### Position control mode

In this mode the motor will move to the `loc_ref` parameter value (see [section 4.1.12](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-4.-driver-communication-protocol-and-usage-instructions) for a list of parameters).

```python
motor.enable()
motor.mode(RunMode.POSITION)

# Limit the top speed
motor.set_parameter("limit_spd", 10)

# Move to position 8 rad
motor.set_parameter("loc_ref", 8)
```

[Full example](./examples/position_mode.py)

### Velocity mode

This mode continuously spins the motor at a particular speed, controlled by the `spd_ref`, `spd_kp`, `spd_ki`, and `limit_cur` parameter values. (see [section 4.1.12](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-4.-driver-communication-protocol-and-usage-instructions) for a full list of parameters).

```python
motor.enable()
motor.mode(RunMode.VELOCITY)

# Turn at 5 rad/s
motor.set_parameter("spd_ref", 5)
```

[Full example](./examples/velocity_mode.py)

### Torque mode (i.e. Current Mode)

This controls how much current is applied to the motor with the `iq_ref`, `cur_kp`, `cur_ki`, and `cur_filt_gain` parameter values. (see [section 4.1.12](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-4.-driver-communication-protocol-and-usage-instructions) for a full list of parameters).

```python
motor.enable()
motor.mode(RunMode.TORQUE)

# Apply 0.5A of maximum torque to the motor
motor.set_parameter("iq_ref", 0.5)
```

[Full example](./examples/torque_mode.py)

## Get the motor state

There's a single command to request the position, torque, velocity, and temperature of the motor. The controller will listen for the response and automatically add it to the state dict.

```python
motor.request_motor_state()
time.sleep(1)
print(motor.state.get("position"))
```

You can also use an event listener to be notified when the state value has been retrieved

```python
def state_updated():
    print(f"{motor.state}")

motor.on("state_changed", state_updated)
motor.request_motor_state()
```

## Reading and writing motor config and parameters

The motor has two lists of values that you can read and write to. Config values are saved between power cycles and parameter values control motor activity and are reset on power down.

NOTE: CyberGear calls both of these sets of values "parameters". However, in the driver we differentiate them as "config" and "parameters" because they are read and saved slightly differently. There are also some value names that exist in both lists.

To see the full tables of values, goto the [motor docs](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-4.-driver-communication-protocol-and-usage-instructions)

- Config values: section 3.3.3 (CyberGear also calls them parameters)
- Parameter values: section 4.1.12

### Read a config value

To read a value, you have to request it from the motor and wait for it to come back. Then you can read it from the config dict.

```python
motor.request_config("MechOffset")
time.sleep(1)
print(motor.config.get("MechOffset"))
```

You can also use an event listener to be notified when config value is retrieved

```python
def config_value_received(name: str, value: str):
    print(f"{name}: {value}")

motor.on("config_received", config_value_received)
motor.request_config("MechOffset")
```

### Set config values

Not all config values can be written to (refer to the table in [the docs](https://wiki.openelab.io/motors/cybergear-micromotor-instruction-manual#id-4.-driver-communication-protocol-and-usage-instructions)).

Be careful when setting config values. Many are core to how the motor works and you could break your motor if you don't know what you're doing.

```python
motor.set_config("overTempTime", 20001)
```

### Read parameter values

To read a parameter, you have to request it from the motor and wait for it to come back. Then you can read it from the parameters dict.

```python
motor.request_parameter("loc_ref")
time.sleep(1)
print(motor.params.get("loc_ref"))
```

You can also use an event listener to be notified when param values are retrieved

```python
def param_value_received(name: str, value: str):
    print(f"{name}: {value}")

motor.on("param_received", param_value_received)
motor.request_parameter("loc_ref")
```

### Set parameter values

```python
motor.set_parameter("loc_ref", 5)
```

## Motor errors

It's important to know when there is a motor fault. Here's how to request the current fault state of the motor:

```python
motor.request_motor_fault_status()

time.sleep(1)

# All the faults might be defined, but only the ones set to True are actively faulting
active_faults = [motor.fault for fault, is_active in faults.items() if is_active]
print("Active motor faults:", motor.faults)
```

You can also use an event listeners to be notified when faults happen or are cleared.

```python
def has_fault():
    active_faults = [motor.fault for fault, is_active in faults.items() if is_active]
    print("Active motor faults:", motor.faults)

def faults_clear():
    print("No more faults")

# Define event listeners
motor.on("has_fault", has_fault)
motor.on("fault_cleared", has_fault)

# Check regularly
motor.request_motor_fault_status()
```

## Other useful things

### Change the CAN bus ID

If you have multiple motors, you'll need to change their CAN bus IDs so they can all be on the same bus.

```python
motor.change_motor_id(5)
```

### Set zero position

Set the current motor position as the zero position. NOTE: this position is lost on power down.

```python
motor.set_zero_position()
```
