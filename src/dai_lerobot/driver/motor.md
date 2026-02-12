# MotorsBus 抽象类文档

## 1. 类概述

`MotorsBus` 是一个抽象基类（ABC），用于高效地读写通过串口菊花链连接的多个电机。该类封装了与电机总线通信的通用逻辑，目前有两个具体实现：`DynamixelMotorsBus` 和 `FeetechMotorsBus`。

### 核心职责
- 管理串口连接生命周期（连接、断开、超时设置）
- 提供单电机和同步多电机的寄存器读写能力
- 处理电机校准数据的存储与转换
- 支持扭矩控制与电机配置
- 管理不同型号电机的控制表差异

---

## 2. 类属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `apply_drive_mode` | `bool` | 是否应用驱动模式（影响方向反转） |
| `available_baudrates` | `list[int]` | 支持的波特率列表 |
| `default_baudrate` | `int` | 默认波特率 |
| `default_timeout` | `int` | 默认超时时间（毫秒） |
| `model_baudrate_table` | `dict[str, dict]` | 型号→波特率配置表 |
| `model_ctrl_table` | `dict[str, dict]` | 型号→控制表（寄存器地址映射） |
| `model_encoding_table` | `dict[str, dict]` | 型号→编码表 |
| `model_number_table` | `dict[str, int]` | 型号→型号编号映射 |
| `model_resolution_table` | `dict[str, int]` | 型号→分辨率（编码器位数） |
| `normalized_data` | `list[str]` | 需要归一化处理的数据字段列表 |

---

## 3. 接口方法详解

### 3.1 初始化与表示

| 方法 | 功能说明 |
|------|----------|
| `__init__(port, motors, calibration=None)` | 初始化总线实例，配置端口、电机字典和校准数据 |
| `__len__()` | 返回连接的电机数量 |
| `__repr__()` | 返回格式化的实例信息（端口、电机列表） |

### 3.2 连接管理

| 方法 | 功能说明 |
|------|----------|
| `connect(handshake=True)` | 打开串口并初始化通信，可选执行握手验证 |
| `_connect(handshake=True)` | 内部连接实现，处理端口打开和异常转换 |
| `_handshake()` | **抽象方法** - 执行实现特定的握手和完整性检查 |
| `disconnect(disable_torque=True)` | 关闭串口，可选先禁用扭矩防止电机损坏 |
| `is_connected` (property) | 返回底层串口是否打开 |

### 3.3 端口扫描与电机配置

| 方法 | 功能说明 |
|------|----------|
| `scan_port(port, *args, **kwargs)` | 扫描指定端口的所有支持波特率，返回波特率→电机ID列表的映射 |
| `setup_motor(motor, initial_baudrate=None, initial_id=None)` | 为单个电机配置正确的ID和波特率（自动扫描或指定初始值） |
| `_find_single_motor(motor, initial_baudrate)` | **抽象方法** - 查找单个电机的当前波特率和ID |
| `configure_motors()` | **抽象方法** - 向所有电机写入实现特定的推荐配置（如返回延迟、加速度限制等） |

### 3.4 波特率与超时

| 方法 | 功能说明 |
|------|----------|
| `set_timeout(timeout_ms=None)` | 设置SDK包超时时间（毫秒），默认使用`default_timeout` |
| `get_baudrate()` | 获取当前配置的波特率 |
| `set_baudrate(baudrate)` | 设置新的UART波特率，验证设置是否成功 |

### 3.5 扭矩控制

| 方法 | 功能说明 |
|------|----------|
| `disable_torque(motors=None, num_retry=0)` | **抽象方法** - 禁用选定电机的扭矩（支持EPROM写入） |
| `_disable_torque(motor, model, num_retry=0)` | **抽象方法** - 内部单电机扭矩禁用 |
| `enable_torque(motors=None, num_retry=0)` | **抽象方法** - 启用选定电机的扭矩 |
| `torque_disabled(motors=None)` | 上下文管理器，确保扭矩在代码块执行后重新启用 |

### 3.6 校准管理

| 方法 | 功能说明 |
|------|----------|
| `is_calibrated` (property) | **抽象方法** - 检查缓存的校准是否与电机匹配 |
| `read_calibration()` | **抽象方法** - 从电机读取校准参数，返回`{电机名: MotorCalibration}` |
| `write_calibration(calibration_dict, cache=True)` | **抽象方法** - 向电机写入校准参数，可选缓存到实例 |
| `reset_calibration(motors=None)` | 重置选定电机到校准出厂状态（归零位偏移，恢复全范围限位） |
| `set_half_turn_homings(motors=None)` | 将各电机当前位置设为中点（半圈），计算并写入归位偏移 |
| `_get_half_turn_homings(positions)` | **抽象方法** - 计算半圈归位偏移值 |
| `record_ranges_of_motion(motors=None, display_values=True)` | 交互式记录电机运动范围（手动移动关节，实时显示位置，按Enter结束） |

### 3.7 数据读写（单电机）

| 方法 | 功能说明 |
|------|----------|
| `read(data_name, motor, *, normalize=True, num_retry=0)` | 读取单个电机寄存器，可选归一化 |
| `_read(address, length, motor_id, *, num_retry=0, raise_on_error=True, err_msg="")` | 底层读取实现，处理1/2/4字节读取和重试逻辑 |
| `write(data_name, motor, value, *, normalize=True, num_retry=0)` | 写入单个电机寄存器，带状态响应（可靠但较慢） |
| `_write(addr, length, motor_id, value, *, num_retry=0, raise_on_error=True, err_msg="")` | 底层写入实现，处理数据序列化和错误处理 |

### 3.8 同步数据读写（多电机）

| 方法 | 功能说明 |
|------|----------|
| `sync_read(data_name, motors=None, *, normalize=True, num_retry=0)` | 同时读取多个电机的同一寄存器，返回`{电机名: 值}` |
| `_sync_read(addr, length, motor_ids, *, num_retry=0, raise_on_error=True, err_msg="")` | 底层同步读取实现，使用`GroupSyncRead` |
| `_setup_sync_reader(motor_ids, addr, length)` | 配置同步读取器参数（地址、长度、电机ID列表） |
| `sync_write(data_name, values, *, normalize=True, num_retry=0)` | 同时写入多个电机的同一寄存器（无状态响应，快速但可能丢包） |
| `_sync_write(addr, length, ids_values, num_retry=0, raise_on_error=True, err_msg="")` | 底层同步写入实现，使用`GroupSyncWrite` |
| `_setup_sync_writer(ids_values, addr, length)` | 配置同步写入器参数 |

### 3.9 数据转换与编码

| 方法 | 功能说明 |
|------|----------|
| `_normalize(ids_values)` | 将原始编码器值归一化到用户友好范围（-100~100、0~100或角度） |
| `_unnormalize(ids_values)` | 将归一化值转换回原始编码器值 |
| `_encode_sign(data_name, ids_values)` | **抽象方法** - 处理有符号数据的编码 |
| `_decode_sign(data_name, ids_values)` | **抽象方法** - 处理有符号数据的解码 |
| `_serialize_data(value, length)` | 将无符号整数序列化为字节列表（支持1/2/4字节，大/小端由子类决定） |
| `_split_into_byte_chunks(value, length)` | **抽象方法** - 将整数分割为字节块（实现特定的字节序） |

### 3.10 通信诊断

| 方法 | 功能说明 |
|------|----------|
| `ping(motor, num_retry=0, raise_on_error=False)` | Ping单个电机，返回型号编号或None |
| `broadcast_ping(num_retry=0, raise_on_error=False)` | **抽象方法** - 广播Ping所有ID，返回`{id: 型号编号}`映射 |
| `_is_comm_success(comm)` | 检查通信返回值是否表示成功 |
| `_is_error(error)` | 检查错误码是否非零 |
| `_assert_motors_exist()` | 验证所有配置的电机是否存在且型号匹配 |

### 3.11 辅助方法

| 方法 | 功能说明 |
|------|----------|
| `_model_nb_to_model(motor_nb)` | 型号编号转换为型号字符串 |
| `_id_to_model(motor_id)` | 电机ID转换为型号字符串 |
| `_id_to_name(motor_id)` | 电机ID转换为配置名称 |
| `_get_motor_id(motor)` | 获取电机ID（支持名称或ID输入） |
| `_get_motor_model(motor)` | 获取电机型号（支持名称或ID输入） |
| `_get_motors_list(motors)` | 标准化电机列表输入（None→全部，str→单元素列表） |
| `_get_ids_values_dict(values)` | 标准化值输入（单值→所有ID，dict→转换键为ID） |

### 3.12 缓存属性

| 属性 | 功能说明 |
|------|----------|
| `_has_different_ctrl_tables` | 检查总线上是否存在不同型号的电机（控制表不同） |
| `models` | 返回所有电机的型号列表 |
| `ids` | 返回所有电机的ID列表 |

---

## 4. 使用流程示例

```python
# 1. 实例化总线
bus = FeetechMotorsBus(
    port="/dev/tty.usbmodem575E0031751",
    motors={"joint_1": (1, "sts3215"), "joint_2": (2, "sts3215")}
)

# 2. 连接并验证
bus.connect()

# 3. 读取位置（归一化值）
position = bus.read("Present_Position", "joint_1")

# 4. 同步读取多个电机
positions = bus.sync_read("Present_Position", ["joint_1", "joint_2"])

# 5. 同步写入目标位置（快速，无响应确认）
bus.sync_write("Goal_Position", {"joint_1": 50.0, "joint_2": -30.0})

# 6. 断开连接（自动禁用扭矩）
bus.disconnect()
```

---

## 5. 设计特点

1. **双重API设计**：提供带响应确认的`read/write`（可靠）和无响应的`sync_read/sync_write`（高性能）
2. **自动归一化**：支持将原始编码器值自动转换为-100~100、0~100或角度单位
3. **多型号兼容**：通过控制表抽象支持同一总线上混合不同型号电机
4. **校准管理**：内置归一化/反归一化逻辑，支持范围校准和方向反转
5. **健壮性**：内置重试机制、详细的错误信息和通信状态检查
