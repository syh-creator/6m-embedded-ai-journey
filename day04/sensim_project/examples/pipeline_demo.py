from sensim.pipeline.sensor_pipeline import SensorDataPipeline

# 1. 初始化温度传感器流水线（SQLite存储+资源监控）
print("=== 初始化温度传感器数据处理流水线 ===")
temp_pipeline = SensorDataPipeline(
    sensor_id="temp-pipeline-001",
    data_type="temperature",
    storage_type="sqlite",  # 仅使用SQLite存储
    db_path="data/temp_pipeline.db",
    resource_monitor_interval=5  # 每5秒监控一次资源
)

# 2. 初始化湿度传感器流水线（双存储+无资源监控）
print("\n=== 初始化湿度传感器数据处理流水线 ===")
hum_pipeline = SensorDataPipeline(
    sensor_id="hum-pipeline-001",
    data_type="humidity",
    storage_type="both",  # 同时使用CSV和SQLite存储
    csv_path="data/hum_pipeline.csv",
    db_path="data/hum_pipeline.db",
    resource_monitor_interval=0  # 关闭资源监控
)

try:
    # 3. 启动流水线（温度运行30秒，湿度运行20秒）
    print("\n=== 启动温度传感器流水线（运行30秒） ===")
    temp_pipeline.start(run_duration=30)

    print("\n=== 启动湿度传感器流水线（运行20秒） ===")
    hum_pipeline.start(run_duration=20)

    # 4. 输出流水线最终状态
    print("\n=== 流水线运行完成，状态汇总 ===")
    temp_status = temp_pipeline.get_pipeline_status()
    hum_status = hum_pipeline.get_pipeline_status()

    print(f"温度流水线 - 运行状态: {'运行中' if temp_status['running'] else '已停止'}, 存储数据量: {temp_status['stored_data_count']}条")
    print(f"湿度流水线 - 运行状态: {'运行中' if hum_status['running'] else '已停止'}, 存储数据量: {hum_status['stored_data_count']}条")
except Exception as e:
    print(f"流水线运行失败: {str(e)}")
    # 确保异常时停止流水线
    temp_pipeline.stop()
    hum_pipeline.stop()