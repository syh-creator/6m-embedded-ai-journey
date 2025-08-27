import time
import logging
import threading
import psutil
from typing import Dict, Optional, Callable, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Resource Monitor - %(levelname)s - %(message)s'
)
logger = logging.getLogger('resource_monitor')


class ResourceMonitor(threading.Thread):
    """
    嵌入式系统资源监控器：实时监控CPU、内存、存储资源，支持超限预警与自动处理
    适配树莓派、ESP32等嵌入式设备（需安装psutil，ESP32需适配micropython-psutil）
    """
    def __init__(
        self,
        monitor_interval: float = 5,  # 监控间隔（秒）
        cpu_threshold: float = 80.0,  # CPU占用预警阈值（%）
        memory_threshold: float = 85.0,  # 内存占用预警阈值（%）
        disk_threshold: float = 90.0,  # 磁盘占用预警阈值（%）
        alert_callback: Optional[Callable[[Dict, List[str]], None]] = None,  # 预警回调函数（stats, alerts）
        disk_path: str = "/"  # 监控的磁盘路径
    ):
        """
        初始化资源监控器
        
        :param monitor_interval: 监控间隔
        :param cpu_threshold: CPU占用预警阈值
        :param memory_threshold: 内存占用预警阈值
        :param disk_threshold: 磁盘占用预警阈值
        :param alert_callback: 资源超限的回调函数（如发送告警、自动优化），签名为 (stats: Dict, alerts: List[str]) -> None
        :param disk_path: 监控的磁盘路径（嵌入式设备可能为/mnt/sdcard）
        """
        super().__init__(name="ResourceMonitor", daemon=True)
        self.monitor_interval = max(1, monitor_interval)  # 最小间隔1秒
        self.thresholds = {
            "cpu": cpu_threshold,
            "memory": memory_threshold,
            "disk": disk_threshold
        }
        self.alert_callback = alert_callback
        self.disk_path = disk_path
        self._running = False
        # 资源统计历史（保留最近10条）
        self.stats_history: List[Dict] = []
        self.max_history = 10

    def start(self) -> None:
        """启动资源监控线程"""
        self._running = True
        logger.info(
            f"资源监控器启动（间隔：{self.monitor_interval}秒）- "
            f"阈值：CPU{self.thresholds['cpu']}%，内存{self.thresholds['memory']}%，磁盘{self.thresholds['disk']}%"
        )
        super().start()

    def stop(self) -> None:
        """停止资源监控线程"""
        self._running = False
        logger.info("资源监控器停止指令已发出")

    def _get_resource_stats(self) -> Dict:
        """获取当前系统资源统计"""
        timestamp = time.time()
        # 1. CPU统计（取1秒内的平均占用率，避免瞬时值偏差）
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)  # 逻辑CPU核心数

        # 2. 内存统计
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used / (1024 ** 2)  # 转换为MB
        memory_total = memory.total / (1024 ** 2)

        # 3. 磁盘统计（监控指定路径）
        try:
            disk = psutil.disk_usage(self.disk_path)
            disk_percent = disk.percent
            disk_used = disk.used / (1024 ** 3)  # 转换为GB
            disk_total = disk.total / (1024 ** 3)
        except Exception as e:
            logger.error(f"磁盘监控失败（路径：{self.disk_path}）：{str(e)}")
            disk_percent = -1.0
            disk_used = -1.0
            disk_total = -1.0

        # 4. 进程自身资源占用（当前Python进程）
        process = psutil.Process()
        process_cpu = process.cpu_percent(interval=0)  # 瞬时占用率
        process_memory = process.memory_percent()  # 占系统内存的百分比
        process_memory_rss = process.memory_info().rss / (1024 ** 2)  # 进程实际内存使用（MB）

        stats = {
            "timestamp": timestamp,
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "process_percent": process_cpu
            },
            "memory": {
                "percent": memory_percent,
                "used_mb": round(memory_used, 2),
                "total_mb": round(memory_total, 2),
                "process_percent": process_memory,
                "process_used_mb": round(process_memory_rss, 2)
            },
            "disk": {
                "percent": disk_percent,
                "used_gb": round(disk_used, 2),
                "total_gb": round(disk_total, 2),
                "path": self.disk_path
            },
            "alerts": {
                "cpu_alert": cpu_percent >= self.thresholds["cpu"],
                "memory_alert": memory_percent >= self.thresholds["memory"],
                "disk_alert": disk_percent >= self.thresholds["disk"] and disk_percent != -1.0
            }
        }

        # 添加到历史记录（保持最近10条）
        self.stats_history.append(stats)
        if len(self.stats_history) > self.max_history:
            self.stats_history.pop(0)

        return stats

    def _check_alerts(self, stats: Dict) -> List[str]:
        """检查资源是否超限，返回预警列表"""
        alerts = []
        if stats["alerts"]["cpu_alert"]:
            alerts.append(f"CPU占用超限（当前{stats['cpu']['percent']}%，阈值{self.thresholds['cpu']}%）")
        if stats["alerts"]["memory_alert"]:
            alerts.append(f"内存占用超限（当前{stats['memory']['percent']}%，阈值{self.thresholds['memory']}%）")
        if stats["alerts"]["disk_alert"]:
            alerts.append(f"磁盘占用超限（当前{stats['disk']['percent']}%，阈值{self.thresholds['disk']}%）")
        return alerts

    def run(self) -> None:
        """监控线程主逻辑：循环获取资源统计并检查预警"""
        while self._running:
            try:
                # 1. 获取资源统计
                stats = self._get_resource_stats()

                # 2. 打印资源统计日志（简化格式）
                logger.info(
                    f"资源统计 - "
                    f"CPU：{stats['cpu']['percent']}%（进程{stats['cpu']['process_percent']}%），"
                    f"内存：{stats['memory']['percent']}%（进程{stats['memory']['process_percent']}%），"
                    f"磁盘：{stats['disk']['percent']}%（已用{stats['disk']['used_gb']}GB）"
                )

                # 3. 检查预警并触发回调
                alerts = self._check_alerts(stats)
                if alerts and self.alert_callback:
                    logger.warning(f"资源预警：{'; '.join(alerts)}")
                    try:
                        self.alert_callback(stats, alerts)  # 调用外部预警处理函数
                    except Exception as e:
                        logger.error(f"预警回调函数执行失败：{str(e)}", exc_info=True)

                # 4. 按监控间隔等待（减去获取CPU统计的1秒）
                wait_time = max(0, self.monitor_interval - 1)
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"资源监控异常：{str(e)}", exc_info=True)
                time.sleep(self.monitor_interval)

        logger.info("资源监控器已停止")

    def get_latest_stats(self) -> Optional[Dict]:
        """获取最新的资源统计"""
        return self.stats_history[-1] if self.stats_history else None

    def get_stats_history(self) -> List[Dict]:
        """获取资源统计历史"""
        return self.stats_history.copy()

    def set_thresholds(self, **kwargs) -> None:
        """动态调整预警阈值（支持cpu/memory/disk）"""
        valid_keys = ["cpu", "memory", "disk"]
        for key, value in kwargs.items():
            if key in valid_keys and isinstance(value, (int, float)) and 0 < value < 100:
                self.thresholds[key] = float(value)
                logger.info(f"更新{key}预警阈值为{value}%")
            else:
                logger.warning(f"无效的阈值配置：{key}={value}（需为0-100的数字）")