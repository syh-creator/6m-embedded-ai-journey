import time
import logging
import threading
from queue import Empty
from typing import Dict, Optional, Callable, List
from sensim.pipeline.sensor_pipeline import SensorDataPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - UART Receiver - %(levelname)s - %(message)s'
)
logger = logging.getLogger('uart_receiver')

class UARTReceiver:
    """
    UART接收器：模拟嵌入式主机接收UART数据帧，解析后对接数据处理流水线
    支持帧校验、数据解析、错误处理
    """
    def __init__(
        self,
        receiver_name: str = "UART-Receiver-001",
        baudrate: int = 115200,
        parity: str = "N",
        pipeline: Optional[SensorDataPipeline] = None
    ):
        """
        初始化UART接收器
        
        :param receiver_name: 接收器名称
        :param baudrate: 波特率（需与发送设备一致）
        :param parity: 校验位（需与发送设备一致）
        :param pipeline: 对接的数据处理流水线（可选，None则仅解析不存储）
        """
        self.receiver_name = receiver_name
        self.baudrate = baudrate
        self.parity = parity
        self.pipeline = pipeline
        
        # 接收器状态
        self.is_listening = False  # 是否正在监听UART数据
        self.receive_buffer = []   # 接收缓冲区（存储未解析的帧）
        self.stats = {             # 接收统计
            "total_frames": 0,
            "valid_frames": 0,
            "error_frames": 0,
            "parity_error_frames": 0
        }

    def _parse_uart_frame(self, frame: str) -> Optional[Dict]:
        """
        解析UART数据帧
        
        :param frame: 接收到的UART帧（格式：S<数据段><校验位>P...P）
        :return: 解析后的传感器数据字典，失败则返回None
        """
        self.stats["total_frames"] += 1
        
        # 1. 帧格式校验（必须以S开头，以P结尾，可有多个P表示多个停止位）
        if not frame.startswith("S") or not frame.endswith("P"):
            logger.error(f"帧格式错误（非S开头/P结尾）：{frame}")
            self.stats["error_frames"] += 1
            return None
        
        # 2. 移除起始位并剥离所有停止位P
        payload = frame[1:]          # 去掉起始位S
        payload = payload.rstrip("P")  # 去掉所有停止位P
        if len(payload) < 2:  # 至少包含1位数据+1位校验位
            logger.error(f"帧内容过短：{frame}")
            self.stats["error_frames"] += 1
            return None
        
        # 拆分数据段和校验位（校验位占1位）
        data_segment = payload[:-1]
        received_parity = payload[-1]

        # 3. 校验位验证（仅演示逻辑）
        if self.parity != "N":
            # 计算数据段的校验位（与发送端逻辑一致）
            one_count = bin(int.from_bytes(data_segment.encode(), 'utf-8')).count('1')
            expected_parity = "0"
            if self.parity == "O":
                expected_parity = "1" if one_count % 2 == 0 else "0"
            elif self.parity == "E":
                expected_parity = "1" if one_count % 2 == 1 else "0"
            
            if received_parity != expected_parity:
                logger.error(f"校验位错误：接收={received_parity}，期望={expected_parity}，帧：{frame}")
                self.stats["parity_error_frames"] += 1
                self.stats["error_frames"] += 1
                return None

        # 4. 解析数据段（CSV格式：sensor_id,data_type,raw_value,is_outlier,sequence,timestamp）
        try:
            fields = data_segment.split(",")
            if len(fields) != 6:
                raise ValueError(f"数据段字段数错误（需6个，实际{len(fields)}个）")
            
            # 转换字段类型
            parsed_data = {
                "sensor_id": fields[0],
                "data_type": fields[1],
                "raw_value": float(fields[2]),
                "is_outlier": bool(int(fields[3])),
                "sequence": int(fields[4]),
                "timestamp": float(fields[5])
            }
            
            self.stats["valid_frames"] += 1
            logger.debug(f"帧解析成功：{parsed_data}")
            return parsed_data
        
        except Exception as e:
            logger.error(f"数据段解析失败：{str(e)}，帧：{frame}")
            self.stats["error_frames"] += 1
            return None

    def _listen_loop(self, uart_device: "VirtualUARTDevice", interval: float = 0.05) -> None:
        """
        监听UART设备发送的帧（模拟硬件接收中断）
        
        :param uart_device: 关联的虚拟UART设备（用于获取发送的帧）
        :param interval: 监听间隔（秒）
        """
        # 校验波特率和校验位是否匹配
        if uart_device.baudrate != self.baudrate:
            raise RuntimeError(f"波特率不匹配：接收器{self.baudrate}，设备{uart_device.baudrate}")
        if uart_device.parity != self.parity:
            raise RuntimeError(f"校验位不匹配：接收器{self.parity}，设备{uart_device.parity}")
        
        logger.info(f"开始监听UART设备 {uart_device.device_name}（间隔：{interval}秒）")
        
        while self.is_listening and uart_device.is_connected:
            # 从设备的发送缓冲读取帧（避免与发送线程竞争数据生成器）
            try:
                frame = uart_device.read_frame(timeout=interval * 2)
                if frame is None:
                    continue

                # 解析帧并处理
                parsed_data = self._parse_uart_frame(frame)
                if parsed_data and self.pipeline:
                    # 对接数据处理流水线（调用流水线的单数据处理方法）
                    self.pipeline._process_single_data(parsed_data)
                
            except Exception as e:
                logger.error(f"监听循环异常：{str(e)}")
                time.sleep(1)  # 异常后延迟重试
        
        self.is_listening = False
        logger.info(f"停止监听UART设备 {uart_device.device_name}")

    def start_listening(self, uart_device: "VirtualUARTDevice", interval: float = 0.05) -> None:
        """
        启动UART监听（异步线程）
        
        :param uart_device: 要监听的虚拟UART设备
        :param interval: 监听间隔
        """
        if self.is_listening:
            logger.warning(f"接收器 {self.receiver_name} 已在监听")
            return
        
        if not uart_device.is_connected:
            raise RuntimeError(f"UART设备 {uart_device.device_name} 未连接，无法监听")
        
        if not uart_device.is_sending:
            raise RuntimeError(f"UART设备 {uart_device.device_name} 未发送数据，无法监听")
        
        self.is_listening = True
        # 启动监听线程（避免阻塞主线程）
        listen_thread = threading.Thread(
            target=self._listen_loop,
            args=(uart_device, interval),
            daemon=True
        )
        listen_thread.start()
        logger.info(f"接收器 {self.receiver_name} 监听线程已启动")

    def stop_listening(self) -> None:
        """停止UART监听"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        logger.info(f"接收器 {self.receiver_name} 已停止监听")

    def get_receive_stats(self) -> Dict:
        """获取接收统计信息"""
        # 计算帧有效率
        valid_rate = (self.stats["valid_frames"] / self.stats["total_frames"] * 100) if self.stats["total_frames"] > 0 else 0
        return {
            **self.stats,
            "valid_rate": round(valid_rate, 2)  # 有效帧率（%）
        }

    def reset_stats(self) -> None:
        """重置接收统计信息"""
        self.stats = {
            "total_frames": 0,
            "valid_frames": 0,
            "error_frames": 0,
            "parity_error_frames": 0
        }
        logger.info(f"接收器 {self.receiver_name} 统计信息已重置")