import time
import logging
from sensim.hardware.uart_device import VirtualUARTDevice
from sensim.hardware.uart_receiver import UARTReceiver
from sensim.pipeline.sensor_pipeline import SensorDataPipeline
from sensim.utils.producer_consumer import ProducerConsumerManager

# 日志
logger = logging.getLogger("producer_consumer_demo")

# 全局变量：用于共享UART设备和接收器（简化演示）
uart_devices = {}
uart_receiver = None
pipeline = None


def uart_frame_generator(device_name: str) -> dict:
    """
    UART帧生成函数（生产者数据来源）
    模拟UART设备生成数据帧
    """
    global uart_devices
    if device_name not in uart_devices:
        raise ValueError(f"UART设备 {device_name} 未初始化")

    device = uart_devices[device_name]
    # 从设备生成器获取数据并生成UART帧
    data = next(device.data_generator)
    frame = device._generate_uart_frame(data)
    return {
        "device_name": device_name,
        "frame": frame,
        "timestamp": time.time()
    }


def uart_frame_processor(frame_info: dict) -> bool:
    """
    UART帧处理函数（消费者数据处理）
    解析UART帧并对接流水线存储
    """
    global uart_receiver, pipeline
    try:
        # 1. 解析UART帧
        frame = frame_info["frame"]
        parsed_data = uart_receiver._parse_uart_frame(frame)
        if not parsed_data:
            logger.warning(f"帧解析失败，跳过处理：{frame}")
            return False

        # 2. 对接数据处理流水线
        if pipeline:
            pipeline._process_single_data(parsed_data)

        return True  # 处理成功
    except Exception as e:
        logger.error(f"帧处理异常：{str(e)}", exc_info=True)
        return False  # 处理失败


def main():
    global uart_devices, uart_receiver, pipeline
    # 1. 初始化基础组件（UART设备、接收器、流水线）
    print("=== 初始化基础组件 ===")
    # 初始化2个UART设备（温度+湿度）
    uart_devices["temp-device"] = VirtualUARTDevice(
        device_name="Temp-Sensor-UART",
        baudrate=115200,
        parity="N",
        sensor_id="uart-temp-002",
        data_type="temperature"
    )
    uart_devices["hum-device"] = VirtualUARTDevice(
        device_name="Hum-Sensor-UART",
        baudrate=9600,
        parity="E",
        sensor_id="uart-hum-002",
        data_type="humidity"
    )
    # 初始化UART接收器（适配温度设备参数，湿度设备后续可扩展多接收器）
    uart_receiver = UARTReceiver(
        receiver_name="Main-UART-Receiver",
        baudrate=115200,
        parity="N"
    )
    # 初始化数据处理流水线（SQLite存储）
    pipeline = SensorDataPipeline(
        sensor_id="pc-pipeline-001",
        data_type="temperature",  # 后续可扩展多类型支持
        storage_type="sqlite",
        db_path="day05/data/pc_pipeline.db",
        resource_monitor_interval=5
    )
    # 连接所有UART设备
    for device in uart_devices.values():
        device.connect()

    # 2. 初始化生产者-消费者管理器
    print("\n=== 初始化生产者-消费者管理器 ===")
    pc_manager = ProducerConsumerManager(queue_maxsize=50)  # 队列容量50，防止内存溢出

    # 添加生产者（每个UART设备对应一个生产者）
    pc_manager.add_producer(
        name="temp-producer",
        data_generator=lambda: uart_frame_generator("temp-device"),
        produce_interval=0.1  # 温度设备发送间隔0.1秒
    )
    pc_manager.add_producer(
        name="hum-producer",
        data_generator=lambda: uart_frame_generator("hum-device"),
        produce_interval=0.2  # 湿度设备发送间隔0.2秒
    )

    # 添加消费者（2个消费者并发处理，批量大小3）
    pc_manager.add_consumer(
        name="consumer-1",
        data_processor=uart_frame_processor,
        consume_interval=0.05,
        batch_size=3
    )
    pc_manager.add_consumer(
        name="consumer-2",
        data_processor=uart_frame_processor,
        consume_interval=0.05,
        batch_size=3
    )

    try:
        # 3. 启动管理器和流水线
        print("\n=== 启动所有组件 ===")
        pipeline.start()  # 启动流水线
        pc_manager.start()  # 启动生产者-消费者

        # 4. 运行20秒，观察多线程并发处理
        print("\n多设备并发处理已启动（运行20秒，按Ctrl+C停止）...")
        for i in range(20):
            time.sleep(1)
            # 每5秒打印一次整体统计
            if (i + 1) % 5 == 0:
                stats = pc_manager.get_overall_stats()
                print(f"\n运行{i+1}秒 - 统计信息：")
                print(f" 生产者：总生成{stats['producers']['total_produced']}条，丢弃{stats['producers']['total_dropped']}条")
                print(f" 消费者：总消费{stats['consumers']['total_consumed']}条，成功{stats['consumers']['total_success']}条")
                print(f" 队列：当前{stats['queue']['current_queue_size']}条，容量{stats['queue']['max_queue_size']}条")

        # 5. 停止流程（等待队列数据处理完成）
        print("\n=== 停止所有组件（等待数据处理完成） ===")
        pc_manager.stop(wait=True)
        pipeline.stop()

        # 6. 输出最终统计
        print("\n=== 最终统计汇总 ===")
        final_stats = pc_manager.get_overall_stats()
        pipeline_stats = pipeline.get_pipeline_status()
        print("1. 生产者-消费者统计：")
        print(f" - 总生成数据：{final_stats['producers']['total_produced']}条")
        print(f" - 总丢弃数据：{final_stats['producers']['total_dropped']}条")
        print(f" - 总消费数据：{final_stats['consumers']['total_consumed']}条")
        print(f" - 处理成功：{final_stats['consumers']['total_success']}条")
        print(f" - 处理失败：{final_stats['consumers']['total_failed']}条")
        print("\n2. 流水线存储统计：")
        print(f" - 存储数据总数：{pipeline_stats['stored_data_count']}条")
        print(f" - 资源监控：CPU最高占用率（需查看日志）")
    except KeyboardInterrupt:
        print("\n接收到手动停止指令")
        pc_manager.stop(wait=True)
        pipeline.stop()
    finally:
        # 确保UART设备断开连接
        for device in uart_devices.values():
            device.disconnect()
        print("\n所有组件已清理完成")


if __name__ == "__main__":
    main()