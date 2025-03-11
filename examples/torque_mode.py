import sys
import can
import time
from arg_parser import parse_args

from CyberGearDriver import CyberGearMotor, RunMode, CyberMotorMessage

bus: can.Bus
motor: CyberGearMotor
notifier: can.Notifier


def connect(
    motor_id: int, interface: str, channel: str, bitrate: int, verbose: bool
) -> CyberGearMotor:
    global bus, motor, notifier

    # Connect to the bus
    bus = can.interface.Bus(
        interface=interface,
        channel=channel,
        bitrate=bitrate,
    )

    # Create function to pass the CyberGear messages to the CAN bus
    def send_message(message: CyberMotorMessage):
        bus.send(
            can.Message(
                arbitration_id=message.arbitration_id,
                data=message.data,
                is_extended_id=message.is_extended_id,
            )
        )

    # Create the motor controller
    motor = CyberGearMotor(motor_id, verbose=verbose, send_message=send_message)

    # Send the CyberGear driver messages received from the CAN bus
    notifier = can.Notifier(bus, [motor.message_received])

    return motor


def main() -> None:
    global bus, motor, notifier

    # Parse command line arguments
    args = parse_args(sys.argv[1:], description="Test the CyberGear in position mode")

    # Create the motor controller
    motor = connect(
        motor_id=args.motor_id,
        verbose=args.verbose,
        interface=args.interface,
        channel=args.channel,
        bitrate=args.bitrate,
    )

    # Init motor
    motor.enable()
    motor.mode(RunMode.TORQUE)

    # Apply 0.5A of torque to the motor
    print("0.5A")
    motor.set_parameter("iq_ref", 0.5)

    while True:
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if motor:
            motor.stop()
        if bus:
            bus.shutdown()
