import time
import threading
from sensim.utils.thread_safe_tools import ThreadSafeCache

# 线程安全缓存（最大容量2000）
safe_cache = ThreadSafeCache(max_size=2000)
total_count = 1000  # 每个线程要添加的数据量

def add_data_safely(thread_name: str) -> None:
    """使用线程安全缓存添加数据"""
    for i in range(total_count):
        time.sleep(0.0001)
        # 使用线程安全的add方法
        safe_cache.add(f"{thread_name}-data-{i}")
    stats = safe_cache.get_stats()
    print(f"线程 {thread_name} 执行完成，当前缓存长度：{stats['current_size']}")

def main():
    print("=== 线程安全优化演示 ===")
    print(f"预期缓存长度：{2 * total_count}（2个线程各添加{total_count}条）")
    
    # 创建两个线程同时添加数据
    thread1 = threading.Thread(target=add_data_safely, args=("Thread-1",))
    thread2 = threading.Thread(target=add_data_safely, args=("Thread-2",))
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    # 输出最终结果
    final_stats = safe_cache.get_stats()
    print(f"实际缓存长度：{final_stats['current_size']}")
    print(f"总添加数据：{final_stats['total_added']}，总移除数据：{final_stats['total_removed']}")
    
    if final_stats['current_size'] == 2 * total_count:
        print("✅ 线程安全：缓存长度符合预期（无数据丢失）")
    else:
        print("❌ 线程安全优化失败：缓存长度不符合预期")

if __name__ == "__main__":
    main()