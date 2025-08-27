import time
import threading
from sensim.hardware.uart_device import VirtualUARTDevice

def main():
    # 1. 初始化虚拟UART温度传感器
    temp_uart = VirtualUARTDevice(
        device_name="Temp-Sensor-UART",
        baudrate=115200,
        parity="N",
        sensor_id="uart-temp-001",
        data_type="temperature"
    )

    # 2. 初始化虚拟UART湿度传感器
    hum_uart = VirtualUARTDevice(
        device_name="Hum-Sensor-UART",
        baudrate=9600,  # 不同波特率
        parity="E",     # 偶校验
        sensor_id="uart-hum-001",
        data_type="humidity"
    )

    try:
        # 3. 连接设备
        temp_uart.connect()
        hum_uart.connect()

        # 4. 启动数据发送（用线程实现多设备并发发送）
        # 温度传感器发送线程（间隔0.1秒）
        temp_thread = threading.Thread(
            target=temp_uart.start_sending,
            args=(0.1,),
            daemon=True  # 主线程退出时子线程自动退出
        )
        # 湿度传感器发送线程（间隔0.2秒）
        hum_thread = threading.Thread(
            target=hum_uart.start_sending,
            args=(0.2,),
            daemon=True
        )

        temp_thread.start()
        hum_thread.start()

        # 5. 运行10秒后停止
        print("虚拟UART设备开始发送数据（按Ctrl+C停止或等待10秒）...")
        time.sleep(10)

        # 6. 停止发送并断开连接
        temp_uart.stop_sending()
        hum_uart.stop_sending()
        time.sleep(1)  # 等待发送线程结束

        # 7. 打印设备最终状态
        print("\n=== 设备最终状态 ===")
        temp_status = temp_uart.get_device_status()
        hum_status = hum_uart.get_device_status()

        print(f"温度UART设备：连接状态={temp_status['is_connected']}，发送状态={temp_status['is_sending']}")
        print(f"湿度UART设备：连接状态={hum_status['is_connected']}，发送状态={hum_status['is_sending']}")

    except KeyboardInterrupt:
        print("\n接收到手动停止指令")
    finally:
        # 确保断开所有设备连接
        temp_uart.disconnect()
        hum_uart.disconnect()

if __name__ == "__main__":
    main()