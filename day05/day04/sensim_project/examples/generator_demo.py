import time
from sensim.embedded.data_generator import sensor_data_generator, batch_data_generator

# 1. 实时异常值检测演示
print("=== 实时传感器数据生成（含异常值检测）===")
temp_gen = sensor_data_generator(
    sensor_id="temp-002",
    data_type="temperature",
    total_count=30,  # 生成30条数据
    filter_method="zscore"
)
for data in temp_gen:
    status = "异常" if data["is_outlier"] else "正常"
    print(f"第{data['sequence']}条: {data['raw_value']}°C ({status})")
    time.sleep(0.1)

# 2. 批次数据生成演示
print("\n=== 批次数据生成演示 ===")
humidity_gen = sensor_data_generator(
    sensor_id="hum-002",
    data_type="humidity",
    total_count=25,
    filter_method=None  # 不过滤
)

# 包装为批次生成器（每批5条）
batch_gen = batch_data_generator(humidity_gen, batch_size=5)
for batch in batch_gen:
    avg_hum = sum(d["raw_value"] for d in batch["data"]) / len(batch["data"])
    print(f"批次{batch['batch_index']}（{batch['batch_size']}条）: 平均湿度 = {avg_hum:.1f}%")

# 3. 无限生成器演示（按Ctrl+C停止）
print("\n=== 无限数据生成（按Ctrl+C停止）===")
pressure_gen = sensor_data_generator(
    sensor_id="press-001",
    data_type="pressure",
    total_count=None,
    filter_method="iqr"
)
try:
    for data in pressure_gen:
        print(f"气压: {data['raw_value']} hPa (序列: {data['sequence']})", end="\r", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    pressure_gen.close()  # 关闭生成器，触发资源清理
    print("\n已手动停止")