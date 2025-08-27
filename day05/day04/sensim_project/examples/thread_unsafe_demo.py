import time
import threading

# 共享资源：计数器（多线程同时修改）
shared_counter = 0
total_count = 1000  # 每个线程要自增的次数

def increment_counter(thread_name: str) -> None:
    """模拟多线程修改共享计数器（线程不安全）"""
    global shared_counter
    for _ in range(total_count):
        # 非原子操作：读取→计算→写回
        current = shared_counter
        # 模拟处理延迟，放大竞态概率
        time.sleep(0.0001)
        shared_counter = current + 1
    print(f"线程 {thread_name} 执行完成，当前计数：{shared_counter}")

def main():
    print("=== 线程安全问题复现 ===")
    print(f"预期计数：{2 * total_count}（2个线程各自增{total_count}次）")
    
    # 创建两个线程同时修改共享计数器
    thread1 = threading.Thread(target=increment_counter, args=("Thread-1",))
    thread2 = threading.Thread(target=increment_counter, args=("Thread-2",))
    
    # 启动线程
    thread1.start()
    thread2.start()
    
    # 等待线程结束
    thread1.join()
    thread2.join()
    
    # 输出实际结果
    print(f"实际计数：{shared_counter}")
    if shared_counter != 2 * total_count:
        print("❌ 线程不安全：计数不符合预期（发生竞态写入丢失）")
    else:
        print("✅ 线程安全：计数符合预期（未出现竞态）")

if __name__ == "__main__":
    main()