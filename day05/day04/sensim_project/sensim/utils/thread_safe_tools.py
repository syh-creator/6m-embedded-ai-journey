import threading
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger('thread_safe_tools')

class ThreadSafeCache:
    """
    线程安全的数据缓存：基于互斥锁实现多线程安全的缓存操作
    适用于嵌入式多设备并发数据收集场景
    """
    def __init__(self, max_size: int = 1000):
        """
        初始化线程安全缓存
        
        :param max_size: 缓存最大容量，超过时自动清空最旧数据
        """
        self.max_size = max_size
        self._cache: List[Any] = []
        # 互斥锁：确保同一时间只有一个线程修改缓存
        self._lock = threading.Lock()
        # 缓存统计
        self.stats = {
            "total_added": 0,
            "total_removed": 0,
            "current_size": 0
        }

    def add(self, item: Any) -> bool:
        """
        向缓存添加数据（线程安全）
        
        :param item: 要添加的缓存项
        :return: 添加成功返回True，失败返回False
        """
        # 获取锁（阻塞直到获取到锁，防止多线程同时修改）
        with self._lock:
            # 检查缓存是否已满
            if len(self._cache) >= self.max_size:
                # 移除最旧的10%数据（或1条，取较大值）
                remove_count = max(1, int(self.max_size * 0.1))
                self._cache = self._cache[remove_count:]
                self.stats["total_removed"] += remove_count
                logger.warning(f"缓存已满（{self.max_size}），移除{remove_count}条最旧数据")
            
            # 添加新数据
            self._cache.append(item)
            self.stats["total_added"] += 1
            self.stats["current_size"] = len(self._cache)
            return True

    def batch_add(self, items: List[Any]) -> int:
        """
        批量添加数据（线程安全）
        
        :param items: 要添加的缓存项列表
        :return: 成功添加的数量
        """
        if not items:
            return 0
        
        with self._lock:
            added_count = 0
            for item in items:
                if len(self._cache) < self.max_size:
                    self._cache.append(item)
                    added_count += 1
                    self.stats["total_added"] += 1
                else:
                    logger.warning(f"缓存已满，无法添加剩余{len(items)-added_count}条数据")
                    break
            
            self.stats["current_size"] = len(self._cache)
            return added_count

    def get_all(self) -> List[Any]:
        """获取缓存中的所有数据（线程安全，返回副本避免外部修改）"""
        with self._lock:
            return self._cache.copy()

    def clear(self) -> int:
        """清空缓存（线程安全）"""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self.stats["current_size"] = 0
            self.stats["total_removed"] += cleared_count
            return cleared_count

    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._lock:
            return self.stats.copy()  # 返回副本避免外部修改统计数据

class ThreadSafeCounter:
    """
    线程安全计数器：基于互斥锁实现多线程安全的计数操作
    适用于嵌入式多设备数据计数、请求计数等场景
    """
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()

    def increment(self, step: int = 1) -> int:
        """增加计数（线程安全）"""
        with self._lock:
            self._value += step
            return self._value

    def decrement(self, step: int = 1) -> int:
        """减少计数（线程安全）"""
        with self._lock:
            if self._value - step < 0:
                raise ValueError("计数器值不能为负")
            self._value -= step
            return self._value

    def get_value(self) -> int:
        """获取当前计数值（线程安全）"""
        with self._lock:
            return self._value

    def reset(self, value: int = 0) -> None:
        """重置计数器（线程安全）"""
        with self._lock:
            self._value = value