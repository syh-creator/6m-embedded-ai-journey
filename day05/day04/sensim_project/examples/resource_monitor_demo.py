import time
import os
from typing import Dict, List
from sensim.utils.resource_mointor import ResourceMonitor

def alert_handler(stats: Dict, alerts: List[str]) -> None:
    """
    资源预警处理函数（示例：打印详细日志+生成预警文件）
    实际嵌入式场景可扩展为：发送MQTT告警、降低采样频率、清理缓存等
    """
    # 1. 打印详细预警信息
    print("\n" + "="*60)
    print("⚠️  资源超限预警")
    print("="*60)
    for alert in alerts:
        print(f"- {alert}")
    print(f"当前时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats['timestamp']))}")
    print(f"进程内存使用：{stats['memory']['process_used_mb']}MB")
    print("="*60 + "\n")

    # 2. 生成预警日志文件
    log_dir = "day05/logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"resource_alert_{int(stats['timestamp'])}.log")
    with open(log_file, "w") as f:
        f.write(f"预警时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats['timestamp']))}\n")
        f.write(f"预警列表：{'; '.join(alerts)}\n")
        f.write(f"CPU统计：{stats['cpu']['percent']}%（核心数：{stats['cpu']['count']}）\n")
        f.write(f"内存统计：{stats['memory']['percent']}%（已用：{stats['memory']['used_mb']}MB/总：{stats['memory']['total_mb']}MB）\n")
        f.write(f"磁盘统计：{stats['disk']['percent']}%（已用：{stats['disk']['used_gb']}GB/总：{stats['disk']['total_gb']}GB）\n")

    # 3. （可选）资源超限自动优化：降低数据采样频率（模拟）
    if "CPU占用超限" in alerts or "内存占用超限" in alerts:
        print("🔧 自动优化：降低数据采样频率（模拟）")
        # 实际场景中可通过全局变量或回调修改生产者的produce_interval


def main():
    # 1. 初始化资源监控器（设置较低阈值便于演示预警）
    monitor = ResourceMonitor(
        monitor_interval=3,  # 每3秒监控一次
        cpu_threshold=50.0,  # CPU超过50%触发预警（演示用）
        memory_threshold=60.0,  # 内存超过60%触发预警（演示用）
        alert_callback=alert_handler,  # 绑定预警处理函数
        disk_path="/"  # 监控系统根目录（Windows为"C:\\")
    )

    # 2. 启动监控器
    monitor.start()

    # 3. 模拟高负载场景（循环创建临时列表占用内存）
    print("资源监控演示启动（运行20秒，按Ctrl+C停止）...")
    print("提示：程序将模拟高负载，触发资源预警")
    temp_data = []
    try:
        for i in range(20):
            time.sleep(1)
            # 每2秒增加内存占用（模拟数据缓存增长）
            if i % 2 == 0:
                temp_data.extend([j for j in range(100000)])  # 每次增加约400KB内存（int类型）
                print(f"运行{i+1}秒 - 模拟内存占用增长（当前列表大小：{len(temp_data)}）")
        
        # 4. 停止监控器
        print("\n=== 停止资源监控器 ===")
        monitor.stop()
        monitor.join(timeout=5)

        # 5. 输出监控历史
        print("\n=== 监控历史统计（最近10条） ===")
        history = monitor.get_stats_history()
        for idx, stats in enumerate(reversed(history[-5:]), 1):  # 显示最近5条
            time_str = time.strftime('%H:%M:%S', time.localtime(stats['timestamp']))
            print(f"{idx}. {time_str} - CPU:{stats['cpu']['percent']}% 内存:{stats['memory']['percent']}% 磁盘:{stats['disk']['percent']}%")

    except KeyboardInterrupt:
        print("\n接收到手动停止指令")
        monitor.stop()
        monitor.join(timeout=5)


if __name__ == "__main__":
    main()