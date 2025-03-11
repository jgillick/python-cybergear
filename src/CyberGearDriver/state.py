from typing import Literal

from CyberGearDriver.constants import P_MIN, P_MAX, V_MIN, V_MAX, T_MIN, T_MAX

StateValues = (
    ("position", (P_MIN, P_MAX)),
    ("velocity", (V_MIN, V_MAX)),
    ("torque", (T_MIN, T_MIN)),
    ("temperature", None),
)

state_names = [name for name, _ in StateValues]

StateName = Literal["position", "velocity", "torque", "temperature"]
