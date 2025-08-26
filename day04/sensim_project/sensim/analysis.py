import numpy as np
from scipy import stats
from .logging_utils import logger
from typing import List, Dict, Union

def filter_outliers(
    data: List[float], 
    method: str = 'zscore', 
    threshold: Union[float, int] = 3
) -> List[float]:
    if not data:
        logger.warning("输入数据为空列表，返回空结果")
        return []
        
    data_np = np.array(data, dtype=np.float64)
    
    if method == 'zscore':
        # 迭代式 Z-score
        filtered_data = data_np.copy()
        for _ in range(5):  # 迭代次数可调
            if filtered_data.size <= 1:
                break
            z_scores = np.abs(stats.zscore(filtered_data))  # ddof=0 默认即可
            # 处理可能出现的 nan（例如全常数或单元素的情况）
            if np.isnan(z_scores).all():
                break
            mask = z_scores < threshold
            if np.all(mask):
                break
            filtered_data = filtered_data[mask]
        result = filtered_data.tolist()
        logger.info(
            f"异常值过滤完成[zscore] - 原始数据: {len(data)}条, "
            f"过滤后: {len(result)}条, 移除异常值: {len(data) - len(result)}条, 阈值: {threshold}"
        )
        return result

    elif method == 'iqr':
        # IQR方法
        q1, q3 = np.percentile(data_np, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        mask = (data_np >= lower_bound) & (data_np <= upper_bound)
        result = data_np[mask].tolist()
        logger.info(
            f"异常值过滤完成[iqr] - 原始数据: {len(data)}条, "
            f"过滤后: {len(result)}条, 移除异常值: {len(data) - len(result)}条, 阈值: {threshold}"
        )
        return result

    else:
        raise ValueError(f"不支持的异常检测方法: {method}，支持的方法为 'zscore' 和 'iqr'")


def analyze_sensor_data(data: List[float]) -> Dict[str, Union[float, int, str]]:
    if not data:
        logger.warning("输入数据为空，无法进行分析")
        return {}
        
    data_np = np.array(data, dtype=np.float64)
    diffs = np.diff(data_np)
    trend_mean = np.mean(diffs) if len(diffs) > 0 else 0
    
    if trend_mean > 0.1:
        trend = "上升"
    elif trend_mean < -0.1:
        trend = "下降"
    else:
        trend = "平稳"
    
    mean_val = np.mean(data_np)
    std_val = np.std(data_np)
    peak_threshold = mean_val + 2 * std_val
    peak_count = int(np.sum(data_np > peak_threshold))
    
    return {
        "sample_count": len(data_np),
        "mean": round(float(mean_val), 2),
        "variance": round(float(np.var(data_np)), 2),
        "max_value": round(float(np.max(data_np)), 2),
        "min_value": round(float(np.min(data_np)), 2),
        "peak_count": peak_count,
        "trend": trend,
        "trend_strength": round(abs(trend_mean), 4)
    }