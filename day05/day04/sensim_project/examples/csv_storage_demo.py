from sensim.storage.csv_storage import CSVStorage
from sensim.embedded.data_generator import sensor_data_generator

# 1. 批次写入测试
print("=== CSV批次写入测试 ===")
csv_storage = CSVStorage(
    file_path="data/sensor_data.csv",  # 存储到data子目录
    headers=["sensor_id", "timestamp", "data_type", "raw_value", "is_outlier", "sequence"]
)

# 生成20条数据并批次写入
data_gen = sensor_data_generator(
    sensor_id="temp-003",
    total_count=20,
    filter_method="zscore"
)
data_list = [data for data in data_gen]
csv_storage.batch_write(data_list, mode="w")
print(f"批次写入完成，数据总行数: {csv_storage.get_data_count()}")

# 2. 追加写入测试
print("\n=== CSV追加写入测试 ===")
append_gen = sensor_data_generator(
    sensor_id="temp-003",
    total_count=5,
    filter_method="zscore"
)
for data in append_gen:
    csv_storage.append_data(data)
    print(f"追加第{data['sequence']}条数据")
print(f"追加完成，数据总行数: {csv_storage.get_data_count()}")