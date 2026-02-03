"""
电机总线通信的工具函数
"""

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
