import time
import random
import logging
from typing import Dict, Optional, List
from queue import Queue, Empty, Full
from sensim.embedded.data_generator import sensor_data_generator

# 配置日志：设为DEBUG以便观察发送帧日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - UART Device - %(levelname)s - %(message)s'
)
logger = logging.getLogger('uart_device')

class VirtualUARTDevice:
    """
    虚拟UART设备：模拟传感器通过UART接口发送数据
    支持配置UART参数、生成符合协议的数据帧、模拟数据发送
    """
    def __init__(
        self,
        device_name: str = "Sensor-UART-001",
        baudrate: int = 115200,
        data_bits: int = 8,
        parity: str = "N",  # N(无校验)/O(奇校验)/E(偶校验)
        stop_bits: int = 1,
        sensor_id: str = "uart-sensor-001",
        data_type: str = "temperature"
    ):
        """
        初始化虚拟UART设备
        
        :param device_name: 设备名称（用于标识）
        :param baudrate: 波特率（bps）
        :param data_bits: 数据位（5-8）
        :param parity: 校验位
        :param stop_bits: 停止位（1/1.5/2）
        :param sensor_id: 关联的传感器ID
        :param data_type: 发送的数据类型
        """
        # 校验UART参数合法性
        self._validate_uart_params(baudrate, data_bits, parity, stop_bits)
        
        self.device_name = device_name
        self.baudrate = baudrate
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.sensor_id = sensor_id
        self.data_type = data_type
        
        # 初始化数据生成器（复用Day04的传感器数据生成器）
        self.data_generator = sensor_data_generator(
            sensor_id=sensor_id,
            data_type=data_type,
            total_count=None,  # 无限生成
            filter_method="zscore",
            noise_level=0.2
        )
        
        # 设备状态
        self.is_connected = False  # UART连接状态
        self.is_sending = False    # 数据发送状态

        # 发送缓冲（线程安全队列），供接收器读取已发送的帧，避免多线程竞争generator
        self.tx_buffer: Queue[str] = Queue(maxsize=1000)

    def _validate_uart_params(self, baudrate: int, data_bits: int, parity: str, stop_bits: int) -> None:
        """校验UART参数合法性"""
        valid_baudrates = [2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]
        if baudrate not in valid_baudrates:
            raise ValueError(f"不支持的波特率 {baudrate}，支持的波特率：{valid_baudrates}")
        
        if data_bits not in [5, 6, 7, 8]:
            raise ValueError(f"数据位必须为5-8，实际为 {data_bits}")
        
        if parity not in ["N", "O", "E"]:
            raise ValueError(f"校验位必须为N/O/E，实际为 {parity}")
        
        if stop_bits not in [1, 1.5, 2]:
            raise ValueError(f"停止位必须为1/1.5/2，实际为 {stop_bits}")

    def _generate_uart_frame(self, data: Dict) -> str:
        """
        生成UART数据帧（字符串格式模拟二进制帧）
        帧格式：<起始位><数据段><校验位><停止位>
        数据段格式：sensor_id,data_type,raw_value,is_outlier,sequence,timestamp
        """
        # 1. 构建数据段（CSV格式，便于解析）
        data_segment = ",".join([
            str(data["sensor_id"]),
            str(data["data_type"]),
            f"{data['raw_value']:.2f}",
            "1" if data["is_outlier"] else "0",
            str(data["sequence"]),
            f"{data['timestamp']:.2f}"
        ])
        
        # 注意：data_bits 指每个字符的位宽（如8位），不限制整个帧的负载长度。
        # 因此不对 data_segment 长度进行截断，否则接收端无法解析CSV字段。

        # 2. 计算校验位（仅演示逻辑，实际为二进制校验）
        parity_bit = "0"
        if self.parity != "N":
            # 统计数据段中'1'的个数（模拟二进制位）
            one_count = bin(int.from_bytes(data_segment.encode(), 'utf-8')).count('1')
            if self.parity == "O":
                parity_bit = "1" if one_count % 2 == 0 else "0"  # 奇校验：1的个数为奇数
            elif self.parity == "E":
                parity_bit = "1" if one_count % 2 == 1 else "0"  # 偶校验：1的个数为偶数
        
        # 3. 组装完整帧
        frame = (
            f"S"  # 起始位标识（模拟0电平）
            f"{data_segment}"  # 数据位
            f"{parity_bit}"    # 校验位
            f"{'P' * int(self.stop_bits)}"  # 停止位标识（模拟1电平，1.5位简化为1位）
        )
        return frame

    def connect(self) -> bool:
        """模拟UART设备连接"""
        if self.is_connected:
            logger.warning(f"设备 {self.device_name} 已处于连接状态")
            return True
        
        # 模拟连接过程（如硬件初始化、参数协商）
        logger.info(f"正在连接设备 {self.device_name}（波特率：{self.baudrate}，8{self.parity}{self.stop_bits}）...")
        time.sleep(0.5)  # 模拟连接延迟
        
        self.is_connected = True
        logger.info(f"设备 {self.device_name} 连接成功")
        return True

    def disconnect(self) -> bool:
        """模拟UART设备断开连接"""
        if not self.is_connected:
            logger.warning(f"设备 {self.device_name} 已处于断开状态")
            return True
        
        # 停止数据发送
        if self.is_sending:
            self.stop_sending()
        
        logger.info(f"正在断开设备 {self.device_name} 连接...")
        time.sleep(0.3)  # 模拟断开延迟
        
        self.is_connected = False
        logger.info(f"设备 {self.device_name} 断开成功")
        return True

    def start_sending(self, interval: float = 0.1) -> None:
        """
        开始通过UART发送数据
        
        :param interval: 发送间隔（秒），模拟传感器采样周期
        """
        if not self.is_connected:
            raise RuntimeError(f"设备 {self.device_name} 未连接，无法发送数据")
        
        if self.is_sending:
            logger.warning(f"设备 {self.device_name} 已在发送数据")
            return
        
        self.is_sending = True
        logger.info(f"设备 {self.device_name} 开始发送数据（间隔：{interval}秒）")
        
        try:
            while self.is_sending and self.is_connected:
                # 从生成器获取传感器数据
                data = next(self.data_generator)
                # 生成UART数据帧
                frame = self._generate_uart_frame(data)
                # 将帧写入发送缓冲，供接收器读取
                try:
                    self.tx_buffer.put(frame, timeout=0.1)
                except Full:
                    # 若缓冲满，丢弃最旧一帧再放入（避免阻塞）
                    try:
                        _ = self.tx_buffer.get_nowait()
                        self.tx_buffer.put_nowait(frame)
                    except Exception:
                        pass

                # 模拟数据发送（打印帧信息）
                logger.debug(f"发送帧：{frame}（长度：{len(frame)}字符）")
                # 按间隔等待下一次发送
                time.sleep(interval)
        except StopIteration:
            logger.info(f"设备 {self.device_name} 数据生成完成，停止发送")
            self.is_sending = False
        except Exception as e:
            logger.error(f"发送数据异常：{str(e)}")
            self.is_sending = False

    def stop_sending(self) -> None:
        """停止UART数据发送"""
        if not self.is_sending:
            return
        
        self.is_sending = False
        logger.info(f"设备 {self.device_name} 已停止发送数据")

    def get_device_status(self) -> Dict:
        """获取UART设备状态"""
        return {
            "device_name": self.device_name,
            "is_connected": self.is_connected,
            "is_sending": self.is_sending,
            "uart_params": {
                "baudrate": self.baudrate,
                "data_bits": self.data_bits,
                "parity": self.parity,
                "stop_bits": self.stop_bits
            },
            "sensor_info": {
                "sensor_id": self.sensor_id,
                "data_type": self.data_type
            }
        }

    def read_frame(self, timeout: Optional[float] = None) -> Optional[str]:
        """从发送缓冲区读取一帧（供接收器调用）"""
        try:
            return self.tx_buffer.get(timeout=timeout)
        except Empty:
            return None