import threading
import time
import logging
from typing import Any, Callable, Optional, List
from queue import Queue, Empty, Full

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('producer_consumer')


class Producer(threading.Thread):
    """
    生产者线程：模拟嵌入式设备（如UART传感器）生成数据并放入队列
    支持多生产者并发，自动处理队列满的阻塞逻辑
    """
    def __init__(
        self,
        name: str,
        data_queue: Queue,
        data_generator: Callable[[], Any],
        produce_interval: float = 0.1,
        max_retry: int = 3
    ):
        """
        初始化生产者
        
        :param name: 生产者名称（用于标识）
        :param data_queue: 数据队列（与消费者共享）
        :param data_generator: 数据生成函数，每次调用返回一条数据
        :param produce_interval: 生产间隔（秒）
        :param max_retry: 队列满时的重试次数（超过则丢弃数据）
        """
        super().__init__(name=name, daemon=True)  # 设为守护线程，主线程退出时自动结束
        self.data_queue = data_queue
        self.data_generator = data_generator
        self.produce_interval = produce_interval
        self.max_retry = max_retry
        self._running = False  # 运行状态
        self.stats = {
            "produced_count": 0,
            "dropped_count": 0,
            "retry_count": 0
        }

    def start(self) -> None:
        """启动生产者线程"""
        self._running = True
        logger.info(f"生产者 {self.name} 启动（生产间隔：{self.produce_interval}秒）")
        super().start()

    def stop(self) -> None:
        """停止生产者线程"""
        self._running = False
        logger.info(f"生产者 {self.name} 停止指令已发出")

    def run(self) -> None:
        """生产者线程主逻辑：循环生成数据并放入队列"""
        while self._running:
            try:
                # 1. 生成数据（调用外部数据生成器，如UART设备帧生成）
                data = self.data_generator()
                self.stats["produced_count"] += 1

                # 2. 尝试将数据放入队列（支持重试）
                retry = 0
                while retry < self.max_retry:
                    try:
                        # 阻塞模式放入队列（超时1秒），避免无限等待
                        self.data_queue.put(data, block=True, timeout=1)
                        logger.debug(f"生产者 {self.name}：数据放入队列成功（队列大小：{self.data_queue.qsize()}）")
                        break
                    except Full:
                        retry += 1
                        self.stats["retry_count"] += 1
                        logger.warning(
                            f"生产者 {self.name}：队列已满，第{retry}次重试（共{self.max_retry}次）"
                        )
                        time.sleep(0.5)  # 重试间隔
                else:
                    # 重试超过上限，丢弃数据
                    self.stats["dropped_count"] += 1
                    logger.error(f"生产者 {self.name}：队列已满且重试超时，丢弃数据")

                # 3. 按生产间隔等待
                time.sleep(self.produce_interval)

            except Exception as e:
                logger.error(f"生产者 {self.name} 异常：{str(e)}", exc_info=True)
                time.sleep(1)  # 异常后延迟重试

        logger.info(
            f"生产者 {self.name} 已停止 - 统计："
            f"生产{self.stats['produced_count']}条，"
            f"重试{self.stats['retry_count']}次，"
            f"丢弃{self.stats['dropped_count']}条"
        )

    def get_stats(self) -> dict:
        """获取生产者统计信息"""
        return self.stats.copy()


class Consumer(threading.Thread):
    """
    消费者线程：从队列中获取数据并处理（如解析、存储）
    支持多消费者并发，自动处理队列空的阻塞逻辑
    """
    def __init__(
        self,
        name: str,
        data_queue: Queue,
        data_processor: Callable[[Any], bool],
        consume_interval: float = 0.05,
        batch_size: int = 1
    ):
        """
        初始化消费者
        
        :param name: 消费者名称
        :param data_queue: 数据队列（与生产者共享）
        :param data_processor: 数据处理函数，返回True表示处理成功
        :param consume_interval: 消费间隔（秒）
        :param batch_size: 批量消费大小（一次从队列取多条数据）
        """
        super().__init__(name=name, daemon=True)
        self.data_queue = data_queue
        self.data_processor = data_processor
        self.consume_interval = consume_interval
        self.batch_size = max(1, batch_size)  # 批量大小至少为1
        self._running = False
        self.stats = {
            "consumed_count": 0,
            "processed_success": 0,
            "processed_failed": 0,
            "empty_count": 0  # 队列空的次数
        }

    def start(self) -> None:
        """启动消费者线程"""
        self._running = True
        logger.info(
            f"消费者 {self.name} 启动（批量大小：{self.batch_size}，消费间隔：{self.consume_interval}秒）"
        )
        super().start()

    def stop(self) -> None:
        """停止消费者线程"""
        self._running = False
        logger.info(f"消费者 {self.name} 停止指令已发出")

    def run(self) -> None:
        """消费者线程主逻辑：循环从队列取数据并处理"""
        while self._running:
            try:
                # 1. 批量从队列获取数据
                batch_data = []
                for _ in range(self.batch_size):
                    try:
                        # 阻塞模式获取数据（超时2秒），避免无限等待
                        data = self.data_queue.get(block=True, timeout=2)
                        batch_data.append(data)
                        self.stats["consumed_count"] += 1
                    except Empty:
                        self.stats["empty_count"] += 1
                        logger.debug(f"消费者 {self.name}：队列空，等待数据（空队列次数：{self.stats['empty_count']}）")
                        break  # 队列空，停止批量获取

                # 2. 处理批量数据（若有数据）
                if batch_data:
                    logger.debug(
                        f"消费者 {self.name}：获取批量数据（{len(batch_data)}条），开始处理"
                    )
                    success_count = 0
                    for data in batch_data:
                        try:
                            # 调用外部处理函数（如UART帧解析、流水线存储）
                            if self.data_processor(data):
                                success_count += 1
                        except Exception as e:
                            logger.error(
                                f"消费者 {self.name}：数据处理失败：{str(e)}",
                                exc_info=True
                            )
                        finally:
                            # 确保在处理完每条数据后标记队列任务完成
                            try:
                                self.data_queue.task_done()
                            except ValueError:
                                # 防御性处理：避免task_done计数异常导致崩溃
                                logger.error(f"消费者 {self.name}：task_done 调用次数异常")

                    self.stats["processed_success"] += success_count
                    self.stats["processed_failed"] += len(batch_data) - success_count
                    logger.debug(
                        f"消费者 {self.name}：批量处理完成（成功{success_count}条，失败{len(batch_data)-success_count}条）"
                    )

                # 3. 按消费间隔等待
                time.sleep(self.consume_interval)

            except Exception as e:
                logger.error(f"消费者 {self.name} 异常：{str(e)}", exc_info=True)
                time.sleep(1)

        logger.info(
            f"消费者 {self.name} 已停止 - 统计："
            f"消费{self.stats['consumed_count']}条，"
            f"处理成功{self.stats['processed_success']}条，"
            f"处理失败{self.stats['processed_failed']}条，"
            f"空队列{self.stats['empty_count']}次"
        )

    def get_stats(self) -> dict:
        """获取消费者统计信息"""
        return self.stats.copy()


class ProducerConsumerManager:
    """
    生产者-消费者管理器：统一管理多个生产者和消费者，简化多线程调度
    适用于嵌入式多设备并发数据处理场景
    """
    def __init__(self, queue_maxsize: int = 100):
        """
        初始化管理器
        
        :param queue_maxsize: 队列最大容量（防止内存溢出）
        """
        self.data_queue = Queue(maxsize=queue_maxsize)
        self.producers: List[Producer] = []
        self.consumers: List[Consumer] = []
        self._running = False

    def add_producer(
        self,
        name: str,
        data_generator: Callable[[], Any],
        produce_interval: float = 0.1,
        max_retry: int = 3
    ) -> None:
        """添加生产者"""
        if self._running:
            raise RuntimeError("管理器已启动，无法添加新生产者")
        
        producer = Producer(
            name=name,
            data_queue=self.data_queue,
            data_generator=data_generator,
            produce_interval=produce_interval,
            max_retry=max_retry
        )
        self.producers.append(producer)
        logger.info(f"已添加生产者：{name}（当前总数：{len(self.producers)}）")

    def add_consumer(
        self,
        name: str,
        data_processor: Callable[[Any], bool],
        consume_interval: float = 0.05,
        batch_size: int = 1
    ) -> None:
        import os
        cpu_cores = os.cpu_count() or 4
        max_threads = 2 * cpu_cores
        if len(self.producers) + len(self.consumers) + 1 > max_threads:
            raise RuntimeError(
                f"线程总数超过上限（{max_threads}），当前已添加{len(self.producers)}个生产者+{len(self.consumers)}个消费者"
            )
        """添加消费者"""
        if self._running: 
            raise RuntimeError("管理器已启动，无法添加新消费者")
        
        consumer = Consumer(
            name=name,
            data_queue=self.data_queue,
            data_processor=data_processor,
            consume_interval=consume_interval,
            batch_size=batch_size
        )
        self.consumers.append(consumer)
        logger.info(f"已添加消费者：{name}（当前总数：{len(self.consumers)}）")

    def start(self) -> None:
        """启动所有生产者和消费者"""
        if self._running:
            logger.warning("管理器已处于运行状态，无需重复启动")
            return
        
        if not self.producers:
            logger.warning("无生产者，仅启动消费者（可能无数据可处理）")
        if not self.consumers:
            raise RuntimeError("无消费者，无法处理数据，启动失败")
        
        self._running = True
        # 启动所有生产者
        for producer in self.producers:
            producer.start()
        # 启动所有消费者
        for consumer in self.consumers:
            consumer.start()
        
        logger.info(
            f"生产者-消费者管理器启动完成："
            f"生产者{len(self.producers)}个，消费者{len(self.consumers)}个，队列容量{self.data_queue.maxsize}"
        )

    def stop(self, wait: bool = True) -> None:
        """
        停止所有生产者和消费者
        
        :param wait: 是否等待所有线程结束（True：等待队列数据处理完成）
        """
        if not self._running:
            return
        
        # 1. 停止所有生产者（不再生成新数据）
        for producer in self.producers:
            producer.stop()
        
        # 2. 若等待处理完成，等待队列清空
        if wait:
            logger.info(f"等待队列中所有数据处理完成（当前队列大小：{self.data_queue.qsize()}）")
            self.data_queue.join()  # 阻塞直到所有任务标记为done
        
        # 3. 停止所有消费者
        for consumer in self.consumers:
            consumer.stop()
        
        # 4. 等待所有线程结束（超时10秒）
        if wait:
            for thread in self.producers + self.consumers:
                thread.join(timeout=10)
        
        self._running = False
        logger.info("生产者-消费者管理器已完全停止")

    def get_overall_stats(self) -> dict:
        """获取整体统计信息"""
        # 汇总所有生产者统计
        producer_stats = {
            "total_produced": sum(p.get_stats()["produced_count"] for p in self.producers),
            "total_dropped": sum(p.get_stats()["dropped_count"] for p in self.producers),
            "total_retry": sum(p.get_stats()["retry_count"] for p in self.producers)
        }
        # 汇总所有消费者统计
        consumer_stats = {
            "total_consumed": sum(c.get_stats()["consumed_count"] for c in self.consumers),
            "total_success": sum(c.get_stats()["processed_success"] for c in self.consumers),
            "total_failed": sum(c.get_stats()["processed_failed"] for c in self.consumers),
            "total_empty": sum(c.get_stats()["empty_count"] for c in self.consumers)
        }
        # 队列当前状态
        queue_stats = {
            "current_queue_size": self.data_queue.qsize(),
            "max_queue_size": self.data_queue.maxsize
        }
        
        return {
            "producers": producer_stats,
            "consumers": consumer_stats,
            "queue": queue_stats,
            "running": self._running
        }