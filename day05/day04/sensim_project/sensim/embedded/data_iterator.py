import time
import random
from typing import Dict, Union, Any, List, Optional
import logging

logger = logging.getLogger('sensor_iterator')


class SensorDataIterator:
    """
    传感器数据迭代器：按批次生成/读取传感器数据
    适用于嵌入式设备实时数据处理，支持批量迭代
    """
    def __init__(
        self,
        sensor_id: str,
        data_type: str = "temperature",
        total_count: Optional[int] = 100,
        batch_size: int = 10,
        noise_level: float = 0.1
    ):
        """
        初始化迭代器
        :param sensor_id: 传感器ID（用于多设备区分）
        :param data_type: 数据类型（temperature/humidity/pressure）
        :param total_count: 总数据量（None表示无限迭代）
        :param batch_size: 每次迭代返回的数据批次大小
        :param noise_level: 数据噪声强度（模拟硬件误差）
        """
        self.sensor_id = sensor_id
        self.data_type = data_type
        self.total_count = total_count
        self.batch_size = batch_size
        self.noise_level = noise_level

        # 数据基础值（按类型预设）
        self.base_value = self._get_base_value()
        # 已生成数据计数
        self.generated = 0
        # 迭代器状态标记
        self._stopped = False

    def _get_base_value(self) -> float:
        """根据数据类型获取基础值（模拟真实传感器基准）"""
        base_map = {
            "temperature": 25.0,  # 常温基准
            "humidity": 60.0,     # 常规湿度基准
            "pressure": 1013.25   # 标准大气压
        }
        return base_map.get(self.data_type, 0.0)

    def __iter__(self) -> "SensorDataIterator":
        """返回迭代器对象自身"""
        return self

    def __next__(self) -> Dict[str, Any]:
        """生成并返回下一批数据，触发StopIteration结束迭代"""
        # 检查是否已停止或达到总数据量
        if self._stopped or (self.total_count is not None and self.generated >= self.total_count):
            raise StopIteration

        # 计算当前批次实际数据量（最后一批可能不足batch_size）
        if self.total_count is not None:
            remaining = self.total_count - self.generated
        else:
            remaining = self.batch_size
        current_batch_size = min(self.batch_size, remaining)

        # 生成批次数据
        batch_data: List[Dict[str, Union[str, float, int]]] = []
        for _ in range(current_batch_size):
            timestamp = time.time()
            # 模拟数据漂移（随时间轻微变化）
            drift = 0.001 * self.generated
            # 模拟噪声（正态分布）
            noise = random.gauss(0, self.noise_level)
            value = round(self.base_value + drift + noise, 2)

            batch_data.append({
                "sensor_id": self.sensor_id,
                "timestamp": round(timestamp, 2),
                "data_type": self.data_type,
                "value": value,
                "batch_index": self.generated // self.batch_size + 1
            })
            self.generated += 1

        if batch_data:
            logger.info(f"生成第{batch_data[0]['batch_index']}批数据，共{len(batch_data)}条")

        total_batches: Union[int, str] = "unlimited"
        if self.total_count is not None:
            total_batches = (self.total_count + self.batch_size - 1) // self.batch_size

        return {
            "batch_info": {
                "batch_index": batch_data[0]['batch_index'] if batch_data else 0,
                "total_batches": total_batches,
                "data_count": len(batch_data)
            },
            "data": batch_data
        }

    def stop(self) -> None:
        """手动停止迭代器（嵌入式设备断电/休眠前调用）"""
        self._stopped = True
        logger.info(f"传感器 {self.sensor_id} 迭代器已停止，共生成{self.generated}条数据")