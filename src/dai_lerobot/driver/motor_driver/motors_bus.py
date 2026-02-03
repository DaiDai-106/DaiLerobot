"""
电机的总线接口, 依然借鉴了Lerobot中的实现, 主要的目的是帮助本人理解驱动器与电机的交互
"""

import abc
import logging
from dataclasses import dataclass
from enum import Enum
from pprint import pformat

import serial
from tqdm import tqdm

from .protocol import GroupSyncRead, GroupSyncWrite, PacketHandler, PortHandler
from .utils import check_if_already_connected, check_if_not_connected

logger = logging.getLogger(__name__)


class MotorNormMode(str, Enum):
    RANGE_0_100 = "range_0_100"
    RANGE_M100_100 = "range_m100_100"
    DEGREES = "degrees"


""" 电机校准数据类 """
@dataclass
class MotorCalibration:
    id: int
    drive_mode: int
    homing_offset: int
    range_min: int
    range_max: int

""" 电机数据类 """
@dataclass
class Motor:
    id: int  # 电机的索引
    model: str  # 电机的型号
    norm_mode: MotorNormMode  # 电机的归一化模式


"""
电机的总线通信抽象类, 主要职责:
管理串口连接生命周期（连接、断开、超时设置）
提供单电机和同步多电机的寄存器读写能力
处理电机校准数据的存储与转换
支持扭矩控制与电机配置
管理不同型号电机的控制表差异
"""
class MotorsBus(abc.ABC):
    apply_drive_mode: bool  # 是否应用驱动模式
    available_baudrates: list[int]  # 可用的波特率
    default_baudrate: int  # 默认的波特率
    default_timeout: int  # 默认的超时时间
    model_baudrate_table: dict[str, dict]  # 模型与波特率的关系
    model_ctrl_table: dict[
        str, dict
    ]  # 这是最重要的部分，是寓意话的控制参数与硬件寄存器中的地址的映射关系
    model_encoding_table: dict[str, dict]  # 模型与编码方式的关系
    model_number_table: dict[
        str, int
    ]  # 实际的电机模型在寄存器中的编号和电机模型名称的映射关系
    model_resolution_table: dict[str, int]  # 模型与分辨率的关系
    normalized_data: list[str]  # 归一化数据

    def __init__(
        self,
        port: str,
        motors: dict[str, Motor],
        calibration: dict[str, MotorCalibration] | None = None,
    ):
        self.port = port
        self.motors = motors
        self.calibration = calibration if calibration else {}

        self.port_handler: PortHandler
        self.packet_handler: PacketHandler
        self.sync_reader: GroupSyncRead
        self.sync_writer: GroupSyncWrite
        self._comm_success: int
        self._no_error: int

        self._id_to_model_dict = {m.id: m.model for m in self.motors.values()}
        self._id_to_name_dict = {m.id: motor for motor, m in self.motors.items()}
        self._model_nb_to_model_dict = {v: k for k, v in self.model_number_table.items()}

        self._validate_motors()

    def __len__(self):
        return len(self.motors)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(\n"
            f"    Port: '{self.port}',\n"
            f"    Motors: \n{pformat(self.motors, indent=8, sort_dicts=False)},\n"
            ")',\n"
        )

    
    # --------------------------- public 方法 --------------------------------
    # --------------------------- 1. 连接管理 --------------------------------
    @property
    def is_connected(self) -> bool:
        """bool: 如果底层串口是打开的, 则返回 `True`."""
        return self.port_handler.is_open


    """ 连接电机 """
    @check_if_already_connected
    def connect(self, handshake: bool = True) -> None:
        """打开串口并初始化通信.

        Args:
            handshake (bool, optional): 对每个预期的电机执行 ping 操作，并执行特定于实现的额外完整性检查。默认为 `True`.

        Raises:
            DeviceAlreadyConnectedError: 串口已经打开.
            ConnectionError: 底层SDK打开串口或握手验证失败.
        """

        self._connect(handshake)
        self.set_timeout()

    @check_if_not_connected
    def disconnect(self, disable_torque: bool = True) -> None:
        """关闭串口 (可选地先禁用扭矩).

        Args:
            disable_torque (bool, optional): 如果 `True` (默认) 则在关闭串口前禁用每个电机的扭矩. 这可以防止电机在断开连接后继续施加阻力扭矩而损坏电机. (但是如果希望是抱闸的话, 可以设置为 `False`)
        """

        if disable_torque:
            self.port_handler.clearPort()
            self.port_handler.is_using = False
            self.disable_torque(num_retry=5)

        self.port_handler.closePort()

    # --------------------------- 2. 端口扫描与电机配置 --------------------------------
    @classmethod
    def scan_port(cls, port: str, *args, **kwargs) -> dict[int, list[int]]:
        """探测 *port* 在每个支持的波特率下, 列出响应的ID. 会通过强制遍历波特率的方式找到对应串口支持的波特率, 并返回每个波特率下响应的ID.

        Args:
            port (str): 要扫描的串口/USB端口 (例如 ``"/dev/ttyUSB0"``).
            *args, **kwargs: 传递给子类构造函数的参数.

        Returns:
            dict[int, list[int]]: 映射 *波特率 → 电机ID列表*
        """
        bus = cls(port, {}, *args, **kwargs)
        bus._connect(handshake=False)
        baudrate_ids = {}

        # 用进度条的方式遍历每个支持的波特率
        for baudrate in tqdm(bus.available_baudrates, desc="Scanning port"):  
            bus.set_baudrate(baudrate)
            ids_models = bus.broadcast_ping()
            if ids_models:
                tqdm.write(f"Motors found for {baudrate=}: {pformat(ids_models, indent=4)}")
                baudrate_ids[baudrate] = list(ids_models)

        bus.port_handler.closePort()
        return baudrate_ids

    




    # --------------------------- 3.波特率与超时 --------------------------------
    def set_baudrate(self, baudrate: int) -> None:
            """设置新的串口波特率.

            Args:
                baudrate (int): 新的波特率 (单位: 比特/秒).

            Raises:
                RuntimeError: 底层SDK无法应用改变.
            """
            present_bus_baudrate = self.port_handler.getBaudRate()
            if present_bus_baudrate != baudrate:
                logger.info(f"设置串口波特率到 {baudrate}. 之前是 {present_bus_baudrate}.")
                self.port_handler.setBaudRate(baudrate)
                if self.port_handler.getBaudRate() != baudrate:
                    raise RuntimeError("无法写入串口波特率.")


    # --------------------------- private 方法 --------------------------------
    def _connect(self, handshake: bool = True) -> None:
        try:
            if not self.port_handler.openPort():
                raise OSError(f"打开串口 '{self.port}' 失败.")
            elif handshake:
                self._handshake()
        except (FileNotFoundError, OSError, serial.SerialException) as e:
            raise ConnectionError(
                f"\n无法连接到端口 '{self.port}'. 请确保使用正确的端口. 并确保串口权限正确."
            ) from e


    @abc.abstractmethod
    def _handshake(self) -> None:
        """ 握手验证, 不同的电机实现方法应该重载 """
        pass
    

    # --------------------------- 4. 验证电机数据 --------------------------------
    """ 验证电机数据 """
    def _validate_motors(self):
        pass 

