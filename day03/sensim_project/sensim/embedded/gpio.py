# 文件路径：sensim/embedded/gpio.py
"""
通用输入输出（GPIO）控制框架
模拟嵌入式设备的 GPIO 接口功能，用于学习和测试
"""
import time
import logging
from enum import Enum
from typing import Any, Dict, Callable

logger = logging.getLogger("gpio_controller")


class GPIODirection(Enum):
    """GPIO 引脚方向枚举类型"""
    INPUT = "input"
    OUTPUT = "output"


class GPIOEdge(Enum):
    """GPIO 中断边沿类型枚举"""
    RISING = "rising"    # 低电平到高电平转换
    FALLING = "falling"  # 高电平到低电平转换
    BOTH = "both"        # 两种转换都触发


class GPIOController:
    """GPIO 控制器类，模拟嵌入式设备的 GPIO 功能"""

    def __init__(self) -> None:
        """初始化 GPIO 控制器"""
        self.pins: Dict[int, Dict[str, Any]] = {}       # 存储引脚状态
        self.callbacks: Dict[int, Dict[str, Any]] = {}  # 存储中断回调

    def setup(self, pin: int, direction: GPIODirection) -> None:
        """
        配置 GPIO 引脚方向

        :param pin: 引脚编号（如 18, 17 等）
        :param direction: 引脚方向（输入/输出）
        """
        if pin in self.pins:
            logger.warning("引脚 %s 已配置，将重新初始化", pin)

        self.pins[pin] = {
            "direction": direction,
            "value": 0,  # 初始值
            "last_updated": time.time(),
        }
        logger.info("引脚 %s 已配置为 %s 模式", pin, direction.value)

    def output(self, pin: int, value: int) -> None:
        """
        设置输出引脚值

        :param pin: 引脚编号
        :param value: 输出值（0 或 1，低电平或高电平）
        :raises RuntimeError: 引脚未配置为输出模式时抛出
        :raises ValueError: 输出值不是 0 或 1 时抛出
        """
        pin_info = self.pins.get(pin)
        if not pin_info:
            raise RuntimeError(f"引脚 {pin} 未配置，请先调用 setup 方法")

        if pin_info["direction"] != GPIODirection.OUTPUT:
            raise RuntimeError(f"引脚 {pin} 未配置为输出模式")

        if value not in (0, 1):
            raise ValueError(f"输出值必须是 0 或 1，实际为 {value}")

        # 仅在值变化时更新
        if pin_info["value"] != value:
            pin_info["value"] = value
            pin_info["last_updated"] = time.time()
            logger.debug("引脚 %s 输出值更新为 %s", pin, value)

    def input(self, pin: int) -> int:
        """
        读取输入引脚值

        :param pin: 引脚编号
        :return: 引脚当前值（0 或 1）
        :raises RuntimeError: 引脚未配置为输入模式时抛出
        """
        pin_info = self.pins.get(pin)
        if not pin_info:
            raise RuntimeError(f"引脚 {pin} 未配置，请先调用 setup 方法")

        if pin_info["direction"] != GPIODirection.INPUT:
            raise RuntimeError(f"引脚 {pin} 未配置为输入模式")

        return int(pin_info["value"])

    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
    ) -> None:
        """
        配置引脚中断检测

        :param pin: 引脚编号
        :param edge: 触发中断的边沿类型
        :param callback: 中断触发时调用的回调函数
        :raises RuntimeError: 引脚未配置为输入模式时抛出
        """
        pin_info = self.pins.get(pin)
        if not pin_info:
            raise RuntimeError(f"引脚 {pin} 未配置，请先调用 setup 方法")

        if pin_info["direction"] != GPIODirection.INPUT:
            raise RuntimeError(f"引脚 {pin} 未配置为输入模式，无法检测中断")

        self.callbacks[pin] = {
            "edge": edge,
            "callback": callback,
            "last_value": int(pin_info["value"]),
        }
        logger.info("引脚 %s 已配置 %s 边沿检测", pin, edge.value)

    def remove_event_detect(self, pin: int) -> None:
        """
        移除引脚的中断检测
        :param pin: 引脚编号
        """
        if pin in self.callbacks:
            del self.callbacks[pin]
            logger.info("引脚 %s 的中断检测已移除", pin)

    def _simulate_input_change(self, pin: int, new_value: int) -> None:
        """
        模拟输入引脚状态变化（硬件信号模拟）

        :param pin: 引脚编号
        :param new_value: 新的引脚值（0 或 1）
        """
        if pin not in self.pins:
            logger.warning("无法模拟未配置引脚 %s 的状态变化", pin)
            return

        if new_value not in (0, 1):
            raise ValueError(f"输入值必须是 0 或 1，实际为 {new_value}")

        pin_info = self.pins[pin]
        old_value = int(pin_info["value"])

        # 更新引脚状态
        pin_info["value"] = new_value
        pin_info["last_updated"] = time.time()

        # 检查是否需要触发中断
        callback_info = self.callbacks.get(pin)
        if callback_info:
            last_value = int(callback_info["last_value"])
            edge = callback_info["edge"]

            should_trigger = (
                (edge == GPIOEdge.RISING and new_value > last_value) or
                (edge == GPIOEdge.FALLING and new_value < last_value) or
                (edge == GPIOEdge.BOTH and new_value != last_value)
            )

            if should_trigger:
                logger.debug("引脚 %s 触发 %s 中断", pin, edge.value)
                callback_info["callback"](pin)

            # 更新最后一次的值
            callback_info["last_value"] = new_value