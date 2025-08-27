from typing import List
import pytest
import numpy as np
from sensim.analysis import filter_outliers,analyze_sensor_data
@pytest.fixture
def sample_data() -> List[float]:
    np.random.seed(42)
    normal_data = np.random.normal(loc=25,scale=5,size=100).tolist()
    outliers = [5,10,50,60]
    return normal_data + outliers
def test_zscore_filter(sample_data):
    filtered = filter_outliers(sample_data,method = 'zscore',threshold = 3)\
    
    assert isinstance(filtered,list)
    assert len(filtered)<len(sample_data)
    for v in (5,10,50,60):
        assert v not in filtered
    assert len(filtered)>=95
def test_iqr_filter(sample_data):
    filtered = filter_outliers(sample_data,method='iqr',threshold = 1.5)

    assert len(filtered)<len(sample_data)
    z_filtered = filter_outliers(sample_data,method='zscore',threshold=3)
    assert len(filtered)<=len(z_filtered)

    for v in (5,10,50,60):
        assert v not in filtered
def test_analyze_data_trend():
    data = [10+i*0.5 for i in range(20)]
    analysis = analyze_sensor_data(data)

    assert analysis['sample_count'] == 20
    assert analysis['mean'] == pytest.approx(14.75)  # 验证均值计算
    assert analysis['trend'] == "上升"  # 验证趋势判断
    assert analysis['trend_strength'] > 0.4  # 验证趋势强度
    assert analysis['peak_count'] == 0  # 无峰值数据
def test_empty_data_handling():
    """测试空数据处理逻辑"""
    # 测试空数据过滤
    filtered = filter_outliers([])
    assert filtered == []

    # 测试空数据分析
    analysis = analyze_sensor_data([])
    assert analysis == {}

def test_invalid_method_error():
    """测试无效算法的异常处理"""
    with pytest.raises(ValueError) as excinfo:
        filter_outliers([1, 2, 3], method='invalid_method')
    # 验证异常信息正确
    assert "不支持的异常检测方法" in str(excinfo.value)