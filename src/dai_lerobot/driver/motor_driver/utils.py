"""
电机总线通信的工具函数
"""

import os
import platform
import select
import sys
from functools import wraps

""" 当设备未连接或链接时抛出的异常. """


class DeviceNotConnectedError(ConnectionError):
    """当设备未连接时抛出的异常."""

    def __init__(self, message="设备未连接. 请先调用 `.connect()` 方法."):
        self.message = message
        super().__init__(self.message)


class DeviceAlreadyConnectedError(ConnectionError):
    """当设备已连接时抛出的异常."""

    def __init__(
        self,
        message="设备已连接. 请不要重复调用 `.connect()` 方法.",
    ):
        self.message = message
        super().__init__(self.message)


def check_if_not_connected(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"{self.__class__.__name__} 未连接. 请先调用 `.connect()` 方法."
            )
        return func(self, *args, **kwargs)

    return wrapper


def check_if_already_connected(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_connected:
            raise DeviceAlreadyConnectedError(
                f"{self.__class__.__name__} 已连接. 请不要重复调用 `.connect()` 方法."
            )
        return func(self, *args, **kwargs)

    return wrapper


def get_ctrl_table(model_ctrl_table: dict[str, dict], model: str) -> dict[str, tuple[int, int]]:
    ctrl_table = model_ctrl_table.get(model)
    if ctrl_table is None:
        raise KeyError(f"Control table for {model=} not found.")
    return ctrl_table


def get_address(model_ctrl_table: dict[str, dict], model: str, data_name: str) -> tuple[int, int]:
    ctrl_table = get_ctrl_table(model_ctrl_table, model)
    addr_bytes = ctrl_table.get(data_name)
    if addr_bytes is None:
        raise KeyError(f"Address for '{data_name}' not found in {model} control table.")
    return addr_bytes


def assert_same_address(model_ctrl_table: dict[str, dict], motor_models: list[str], data_name: str) -> None:
    all_addr = []
    all_bytes = []
    for model in motor_models:
        addr, bytes = get_address(model_ctrl_table, model, data_name)
        all_addr.append(addr)
        all_bytes.append(bytes)

    if len(set(all_addr)) != 1:
        raise NotImplementedError(
            f"At least two motor models use a different address for `data_name`='{data_name}'"
            f"({list(zip(motor_models, all_addr, strict=False))})."
        )

    if len(set(all_bytes)) != 1:
        raise NotImplementedError(
            f"At least two motor models use a different bytes representation for `data_name`='{data_name}'"
            f"({list(zip(motor_models, all_bytes, strict=False))})."
        )


def enter_pressed() -> bool:
    return select.select([sys.stdin], [], [], 0)[0] and sys.stdin.readline().strip() == ""


def move_cursor_up(lines):
    """移动光标向上指定行数."""
    print(f"\033[{lines}A", end="")


""" 有符号数编码和解码 """
def encode_sign_magnitude(value: int, sign_bit_index: int):
    """
    https://en.wikipedia.org/wiki/Signed_number_representations#Sign%E2%80%93magnitude
    """
    max_magnitude = (1 << sign_bit_index) - 1
    magnitude = abs(value)
    if magnitude > max_magnitude:
        raise ValueError(f"Magnitude {magnitude} exceeds {max_magnitude} (max for {sign_bit_index=})")

    direction_bit = 1 if value < 0 else 0
    return (direction_bit << sign_bit_index) | magnitude


def decode_sign_magnitude(encoded_value: int, sign_bit_index: int):
    """
    https://en.wikipedia.org/wiki/Signed_number_representations#Sign%E2%80%93magnitude
    """
    direction_bit = (encoded_value >> sign_bit_index) & 1
    magnitude_mask = (1 << sign_bit_index) - 1
    magnitude = encoded_value & magnitude_mask
    return -magnitude if direction_bit else magnitude


def encode_twos_complement(value: int, n_bytes: int):
    """
    https://en.wikipedia.org/wiki/Signed_number_representations#Two%27s_complement
    """

    bit_width = n_bytes * 8
    min_val = -(1 << (bit_width - 1))
    max_val = (1 << (bit_width - 1)) - 1

    if not (min_val <= value <= max_val):
        raise ValueError(
            f"Value {value} out of range for {n_bytes}-byte two's complement: [{min_val}, {max_val}]"
        )

    if value >= 0:
        return value

    return (1 << bit_width) + value


def decode_twos_complement(value: int, n_bytes: int) -> int:
    """
    https://en.wikipedia.org/wiki/Signed_number_representations#Two%27s_complement
    """
    bits = n_bytes * 8
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        value -= 1 << bits
    return value
