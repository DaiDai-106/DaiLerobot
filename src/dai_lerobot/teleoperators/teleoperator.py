import abc
import builtins
from pathlib import Path
from typing import Any
import draccus

from dai_lerobot.processors import RobotAction
from dai_lerobot.driver.motor_driver.motors_bus import MotorCalibration
from .config import TeleoperatorConfig


class Teleoperator(abc.ABC):
    """
    对于全部摇操硬件的通用抽象接口, 本类为与物理遥操作设备交互提供统一接口。子类必须实现所有抽象方法和属性后才能正常使用。
    Attributes:
        config_class (RobotConfig): The expected configuration class for this teleoperator.
        name (str): The unique name used to identify this teleoperator type.
    """

    # Set these in ALL subclasses
    config_class: builtins.type[TeleoperatorConfig]
    name: str

    def __init__(self, config: TeleoperatorConfig):
        self.id = config.id
        self.calibration_dir = config.calibration_dir

        if self.calibration_dir is not None:
            self.calibration_dir.mkdir(parents=True, exist_ok=True)
            self.calibration_fpath = self.calibration_dir / f"{self.id}.json"
            self.calibration: dict[str, MotorCalibration] = {}
            if self.calibration_fpath.is_file():
                self._load_calibration()

    def __str__(self) -> str:
        return f"{self.id} {self.__class__.__name__}"

    def __enter__(self):
        """
        Context manager entry. 自动连接到遥操作设备
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Context manager exit. 自动断开与遥操作设备的连接
        """
        self.disconnect()

    def __del__(self) -> None:
        """
        析构函数安全网. 在对象被垃圾回收时尝试断开连接
        """
        try:
            if self.is_connected:
                self.disconnect()
        except Exception:  # nosec B110
            pass

    @property
    @abc.abstractmethod
    def action_features(self) -> dict:
        """
        用于描述遥操作设备产生的动作的结构和类型的字典。其结构（键）应该与: get_action` 返回的结构匹配。字典的值应该是值的类型，例如单个关节的目标位置/速度的 `float`。
        无论遥操作设备是否连接，都应该能够调用这个属性。
        主要就是告诉一下用户目前的数据结构是啥样的，存的就是一个元信息
        """
        pass

    @property
    @abc.abstractmethod
    def feedback_features(self) -> dict:
        """
        用于描述遥操作设备期望的反馈动作的结构和类型的字典, 主要就是告诉一下用户目前的数据结构是啥样的，存的就是一个元信息
        """
        pass

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """
        是否与遥操作设备连接。
        """
        pass

    @abc.abstractmethod
    def connect(self, calibrate: bool = True) -> None:
        """
        建立与遥操作设备的通信。

        Args:
            calibrate (bool): 如果为 True, 在连接后自动校准遥操作设备（如果未校准或需要校准）（这取决于硬件）。
        """
        pass

    @property
    @abc.abstractmethod
    def is_calibrated(self) -> bool:
        """是否与遥操作设备校准。如果不可用，应该始终为 `True`"""
        pass

    @abc.abstractmethod
    def calibrate(self) -> None:
        """
        对于部分需要校准的遥操作设备，进行校准。
        """
        pass

    def _load_calibration(self, fpath: Path | None = None) -> None:
        """
        从指定文件中加载校准数据
        """
        fpath = self.calibration_fpath if fpath is None else fpath
        with open(fpath) as f, draccus.config_type("json"):
            self.calibration = draccus.load(dict[str, MotorCalibration], f)

    def _save_calibration(self, fpath: Path | None = None) -> None:
        """
        保存校准后的标定数据
        """
        fpath = self.calibration_fpath if fpath is None else fpath
        with open(fpath, "w") as f, draccus.config_type("json"):
            draccus.dump(self.calibration, f, indent=4)

    @abc.abstractmethod
    def configure(self) -> None:
        """
        应用任何一次性的或运行时的配置到遥操作设备。这可能包括设置电机参数、控制模式或初始状态。
        """
        pass

    @abc.abstractmethod
    def get_action(self) -> RobotAction:
        """
        从遥操作设备中获取当前动作。

        Returns:
            RobotAction: 一个扁平的字典，表示遥操作设备的当前动作。
        """
        pass

    @abc.abstractmethod
    def send_feedback(self, feedback: dict[str, Any]) -> None:
        """
        发送一个反馈动作命令到遥操作设备。
        Args:
            feedback (dict[str, Any]): 表示期望的反馈的字典。其结构应该与 :pymeth:`feedback_features` 匹配。

        Returns:
            dict[str, Any]: 实际发送给电机的动作，可能被剪裁或修改，例如由于速度安全限制。
        """
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """断开与遥操作设备的连接并执行必要的清理。"""
        pass
