import sys
import errno
import argparse
import can
from typing import List


DEFAULT_CAN_BITRATE = 1000000


def parse_args(
    args: List[str], description: str = "Connect to the CyberGear driver via CAN bus"
) -> argparse.Namespace:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description=description,
    )

    parser.add_argument(
        "-m",
        "--motor-id",
        type=int,
        help="The ID of the motor on the CAN bus",
        default=127,
    )

    parser.add_argument(
        "-c",
        "--channel",
        help=r"Most backend interfaces require some sort of channel. For "
        r"example with the serial interface the channel might be"
        r'"/dev/ttyACM0". With the socketcan interface valid '
        r'channel examples include: "can0", "vcan0".'
        r"(more info: https://python-can.readthedocs.io/en/stable/interfaces.html)",
    )

    parser.add_argument(
        "-i",
        "--interface",
        dest="interface",
        help="""Specify the Python CAN interface to use (for example 'slcan'). See: https://python-can.readthedocs.io/en/stable/interfaces.html""",
        choices=sorted(can.VALID_INTERFACES),
    )

    parser.add_argument(
        "-b",
        "--bitrate",
        dest="bitrate",
        help="""CAN bus communication bitrate""",
        default=DEFAULT_CAN_BITRATE,
        type=int,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        help="""Verbose output""",
        action=argparse.BooleanOptionalAction,
    )

    if not args:
        parser.print_help(sys.stderr)
        raise SystemExit(errno.EINVAL)
    parsed_args, unknown_args = parser.parse_known_args(args)

    return parsed_args
