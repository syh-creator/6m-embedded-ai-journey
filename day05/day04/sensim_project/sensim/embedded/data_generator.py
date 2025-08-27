import time
import random
from typing import Generator, Dict, Any, Optional, List
from sensim.analysis import filter_outliers  # 复用Day3的异常值过滤功能


def sensor_data_generator(
    sensor_id: str,
    data_type: str = "temperature",
    total_count: Optional[int] = None,
    noise_level: float = 0.1,
    filter_method: Optional[str] = "zscore"
) -> Generator[Dict[str, Any], None, None]:
    """
    传感器数据生成器：实时生成单条传感器数据，支持实时异常值过滤

    :param sensor_id: 传感器ID
    :param data_type: 数据类型
    :param total_count: 总数据量（None表示无限生成）
    :param noise_level: 噪声强度
    :param filter_method: 异常值过滤方法（None表示不过滤）
    :yield: 单条传感器数据字典
    """
    # 基础值配置
    base_map = {
        "temperature": 25.0,
        "humidity": 60.0,
        "pressure": 1013.25
    }
    base_value = base_map.get(data_type, 0.0)#0.0为默认值
    generated = 0
    # 缓存最近10条数据用于异常值检测（滑动窗口）
    recent_data: List[float] = []

    try:
        while total_count is None or generated < total_count:
            timestamp = time.time()
            # 数据漂移 + 噪声
            drift = 0.001 * generated
            noise = random.gauss(0, noise_level)
            raw_value = base_value + drift + noise
            current_value = round(raw_value, 2)

            # 实时异常值过滤（滑动窗口）
            recent_data.append(current_value)
            if len(recent_data) > 10:  # 保持窗口大小为10
                recent_data.pop(0)#删除索引为0的值

            is_outlier = False
            if filter_method and len(recent_data) >= 5:  # 数据量足够时才过滤
                filtered = filter_outliers(recent_data, method=filter_method, threshold=2)
                if current_value not in filtered:
                    is_outlier = True

            # 生成数据
            yield {
                "sensor_id": sensor_id,
                "timestamp": round(timestamp, 2),
                "data_type": data_type,
                "raw_value": current_value,
                "is_outlier": is_outlier,
                "sequence": generated + 1
            }

            generated += 1
            time.sleep(0.1)  # 模拟传感器采样间隔（100ms/次）

    except GeneratorExit:
        # 生成器关闭时的资源清理（如传感器断电指令）
        print(f"\n生成器关闭：传感器 {sensor_id} 已停止采集，共生成{generated}条数据")


def batch_data_generator(
    generator: Generator[Dict[str, Any], None, None],
    batch_size: int = 10
) -> Generator[Dict[str, Any], None, None]:
    """
    批次数据生成器：将单条数据生成器包装为批次生成器

    :param generator: 单条数据生成器
    :param batch_size: 批次大小
    :yield: 批次数据字典
    """
    batch: List[Dict[str, Any]] = []
    batch_index = 1
    for data in generator:
        batch.append(data)
        if len(batch) >= batch_size:
            yield {
                "batch_index": batch_index,
                "batch_size": len(batch),
                "data": batch
            }
            batch = []
            batch_index += 1
    # 处理最后一批不足batch_size的数据
    if batch:
        yield {
            "batch_index": batch_index,
            "batch_size": len(batch),
            "data": batch
        }