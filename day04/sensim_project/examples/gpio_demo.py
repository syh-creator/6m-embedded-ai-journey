# 文件路径：examples/gpio_demo.py
import time
import random
from sensim.embedded.gpio import GPIOController, GPIODirection, GPIOEdge

# 中断回调函数
def motion_detected(pin: int):
    """运动传感器触发时的处理函数"""
    print(f"\n检测到运动！引脚 {pin} 触发中断")
    # 点亮 LED
    gpio.output(LED_PIN, 1)
    time.sleep(2)  # 保持 2 秒
    # 熄灭 LED
    gpio.output(LED_PIN, 0)


# 初始化 GPIO 控制器
gpio = GPIOController()

# 定义引脚
MOTION_SENSOR_PIN = 17  # 运动传感器连接引脚
LED_PIN = 18            # LED 连接引脚

try:
    # 配置引脚
    gpio.setup(MOTION_SENSOR_PIN, GPIODirection.INPUT)
    gpio.setup(LED_PIN, GPIODirection.OUTPUT)

    # 配置中断检测
    gpio.add_event_detect(
        MOTION_SENSOR_PIN,
        GPIOEdge.RISING,
        motion_detected
    )

    print("GPIO 演示程序启动，按 Ctrl+C 退出...")
    print("模拟运动传感器数据中...")

    # 模拟传感器数据变化
    while True:
        # 10% 概率检测到运动（高电平）
        if random.random() < 0.1:
            gpio._simulate_input_change(MOTION_SENSOR_PIN, 1)
            time.sleep(0.5)  # 保持高电平
            gpio._simulate_input_change(MOTION_SENSOR_PIN, 0)
        time.sleep(1)

except KeyboardInterrupt:
    print("\n程序已终止")
finally:
    # 清理资源（确保 LED 关闭）
    try:
        gpio.output(LED_PIN, 0)
    except Exception:
        pass