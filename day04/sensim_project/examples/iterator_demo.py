import time
from sensim.embedded.data_iterator import SensorDataIterator

# 1. 有限数据迭代测试
print("=== 有限数据迭代测试（100条，每批20条）===")
temp_iterator = SensorDataIterator(
    sensor_id="temp-001",
    data_type="temperature",
    total_count=100,
    batch_size=20
)
for batch in temp_iterator:
    print(f"批次{batch['batch_info']['batch_index']}: 第1条数据值 = {batch['data'][0]['value']}°C")

# 2. 无限数据迭代测试（按Ctrl+C停止）
print("\n=== 无限数据迭代测试（按Ctrl+C停止）===")
humidity_iterator = SensorDataIterator(
    sensor_id="hum-001",
    data_type="humidity",
    total_count=None,  # 无限迭代
    batch_size=5
)
try:
    for batch in humidity_iterator:
        print(f"湿度批次{batch['batch_info']['batch_index']}: 平均湿度 = {sum(d['value'] for d in batch['data'])/len(batch['data']):.1f}%", flush=True)
        time.sleep(1)  # 模拟实时采集间隔
except KeyboardInterrupt:
    humidity_iterator.stop()
    print("迭代测试已手动停止")