import pytest
import time
from sensim.pipeline.sensor_pipeline import SensorDataPipeline

def test_pipeline_restart():
    """测试流水线停止后重启，数据是否连续存储"""
    # 初始化流水线（运行10秒后停止）
    pipeline = SensorDataPipeline(
        sensor_id="test-pipeline-001",
        data_type="temperature",
        storage_type="sqlite",
        db_path="data/test_pipeline.db",
        resource_monitor_interval=0
    )

    # 第一次运行10秒
    pipeline.start(run_duration=10)
    first_count = pipeline.get_pipeline_status()["stored_data_count"]
    pipeline.stop()

    # 等待2秒后重启
    time.sleep(2)
    pipeline.start(run_duration=5)
    second_count = pipeline.get_pipeline_status()["stored_data_count"]
    pipeline.stop()

    # 验证数据连续存储（第二次运行应新增数据）
    assert second_count > first_count
    assert second_count - first_count > 0  # 确保有新数据插入