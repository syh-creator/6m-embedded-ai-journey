import time
import logging
import psutil  # 用于监控系统资源（嵌入式场景可选）
from typing import Dict, Optional
from sensim.embedded.data_generator import sensor_data_generator
from sensim.storage.csv_storage import CSVStorage
from sensim.storage.sqlite_storage import SQLiteStorage
from sensim.analysis import analyze_sensor_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sensor_pipeline')


class SensorDataPipeline:
    """
    传感器数据处理流水线：整合数据生成、过滤、存储、分析全流程
    支持CSV和SQLite双存储方案，适配不同嵌入式设备需求
    """

    def __init__(
        self,
        sensor_id: str,
        data_type: str,
        storage_type: str = "sqlite",  # 支持sqlite/csv/both
        csv_path: str = "data/pipeline_sensor.csv",
        db_path: str = "data/pipeline_sensor.sqlite",
        resource_monitor_interval: int = 10, # 资源监控间隔（秒）
        
    ):
        """
        初始化数据处理流水线

        :param sensor_id: 传感器ID
        :param data_type: 数据类型（temperature/humidity/pressure）
        :param storage_type: 存储类型
        :param csv_path: CSV存储路径（storage_type包含csv时生效）
        :param db_path: 数据库路径（storage_type包含sqlite时生效）
        :param resource_monitor_interval: 资源监控间隔（0表示关闭监控）
        """
        self.sensor_id = sensor_id
        self.data_type = data_type
        self.storage_type = storage_type.lower()
        self.resource_monitor_interval = resource_monitor_interval
        self._running = False  # 流水线运行状态
        self._last_monitor_time = 0  # 上次资源监控时间
        # __init__ 内新增
        self.batch_cache_size = 10  # 每10条数据批量插入一次
        self.data_cache = []        # 数据缓存列表
        # 初始化存储组件
        self.storages = self._init_storages(csv_path, db_path)

        # 初始化数据生成器（默认无限生成，外部控制停止）
        self.data_generator = sensor_data_generator(
            sensor_id=sensor_id,
            data_type=data_type,
            total_count=None,
            filter_method="zscore",
            noise_level=0.15  # 适度提高噪声模拟真实环境
        )

    def _init_storages(self, csv_path: str, db_path: str) -> Dict:
        """初始化存储组件"""
        storages: Dict[str, object] = {}
        # 初始化CSV存储
        if self.storage_type in ["csv", "both"]:
            try:
                storages["csv"] = CSVStorage(
                    file_path=csv_path,
                    headers=["sensor_id", "timestamp", "data_type", "raw_value", "is_outlier", "sequence"]
                )
                logger.info(f"CSV存储初始化完成: {csv_path}")
            except Exception as e:
                logger.error(f"CSV存储初始化失败: {str(e)}")
                raise

        # 初始化SQLite存储
        if self.storage_type in ["sqlite", "both"]:
            try:
                storages["sqlite"] = SQLiteStorage(db_path=db_path)
                logger.info(f"SQLite存储初始化完成: {db_path}")
            except Exception as e:
                logger.error(f"SQLite存储初始化失败: {str(e)}")
                raise

        if not storages:
            raise ValueError(f"不支持的存储类型: {self.storage_type}，支持sqlite/csv/both")
        return storages

    def _monitor_resources(self) -> None:
        """监控系统资源（CPU/内存），嵌入式场景防止资源耗尽"""
        current_time = time.time()
        if self.resource_monitor_interval <= 0 or (current_time - self._last_monitor_time) < self.resource_monitor_interval:
            return

        # 获取当前进程资源占用
        process = psutil.Process()
        cpu_usage = process.cpu_percent(interval=0.1)
        memory_usage = process.memory_percent()
        # 获取系统内存使用
        system_memory = psutil.virtual_memory()

        # 日志输出资源状态
        logger.info(
            f"资源监控 - CPU占用: {cpu_usage}%, 进程内存占用: {memory_usage}%, "
            f"系统内存占用: {system_memory.percent}%"
        )

        # 资源阈值预警（嵌入式场景可根据设备配置调整）
        if cpu_usage > 80:
            logger.warning(f"CPU占用过高（{cpu_usage}%），建议降低采样频率")
        if system_memory.percent > 90:
            logger.error(f"系统内存不足（{system_memory.percent}%），可能导致程序崩溃")

        self._last_monitor_time = current_time

    # def _process_single_data(self, data: Dict) -> None:
    #     """处理单条传感器数据：存储+实时分析"""
    #     try:
    #         # 1. 数据存储（多存储类型支持）
    #         if "csv" in self.storages:
    #             self.storages["csv"].append_data(data)
    #         if "sqlite" in self.storages:
    #             # SQLite批次插入更高效，这里暂用单条插入（后续可优化为批量缓存）
    #             self.storages["sqlite"].batch_insert([data])

    #         # 2. 实时简单分析（每10条数据输出一次统计）
    #         if data.get("sequence", 0) % 10 == 0 and "sqlite" in self.storages:
    #             # 查询最近10条数据进行分析
    #             recent_data = self.storages["sqlite"].query_data(
    #                 sensor_id=self.sensor_id,
    #                 data_type=self.data_type,
    #                 limit=10
    #             )
    #             if recent_data:
    #                 values = [d["raw_value"] for d in recent_data]
    #                 analysis = analyze_sensor_data(values)
    #                 logger.info(
    #                     f"实时分析（第{data['sequence']}条） - 均值: {analysis.get('mean')}, "
    #                     f"趋势: {analysis.get('trend')}, 异常值占比: {sum(1 for d in recent_data if d['is_outlier'])/len(recent_data)*100:.1f}%"
    #                 )

    #         # 3. 资源监控
    #         self._monitor_resources()

    #     except Exception as e:
    #         logger.error(f"单条数据处理失败: {str(e)}", exc_info=True)
    # 修改 _process_single_data：先缓存，达到缓存大小再批量插入
    def _process_single_data(self, data: Dict) -> None:
        try:
            # CSV 仍逐条写入，便于实时观测
            if "csv" in self.storages:
                self.storages["csv"].append_data(data)

            # 缓存SQLite数据
            self.data_cache.append(data)
            if len(self.data_cache) >= self.batch_cache_size and "sqlite" in self.storages:
                self.storages["sqlite"].batch_insert(self.data_cache)
                self.data_cache = []

            # 实时分析（每10条触发一次）
            if data.get("sequence", 0) % 10 == 0 and "sqlite" in self.storages:
                recent_data = self.storages["sqlite"].query_data(
                    sensor_id=self.sensor_id,
                    data_type=self.data_type,
                    limit=10
                )
                if recent_data:
                    values = [d["raw_value"] for d in recent_data]
                    analysis = analyze_sensor_data(values)
                    logger.info(
                        f"实时分析（第{data['sequence']}条） - 均值: {analysis.get('mean')}, "
                        f"趋势: {analysis.get('trend')}, 异常值占比: {sum(1 for d in recent_data if d['is_outlier'])/len(recent_data)*100:.1f}%"
                    )

            self._monitor_resources()

        except Exception as e:
            logger.error(f"单条数据处理失败: {str(e)}", exc_info=True)

    def start(self, run_duration: Optional[int] = None) -> None:
        """
        启动数据处理流水线

        :param run_duration: 运行时长（秒），None表示无限运行（按Ctrl+C停止）
        """
        if self._running:
            logger.warning("流水线已处于运行状态，无需重复启动")
            return

        self._running = True
        start_time = time.time()
        logger.info(
            f"传感器数据处理流水线启动 - 传感器ID: {self.sensor_id}, "
            f"数据类型: {self.data_type}, 存储类型: {self.storage_type}, "
            f"预计运行时长: {'无限' if run_duration is None else f'{run_duration}秒'}"
        )

        try:
            for data in self.data_generator:
                # 检查是否达到运行时长
                if run_duration and (time.time() - start_time) >= run_duration:
                    logger.info(f"已达到预设运行时长（{run_duration}秒），准备停止流水线")
                    break

                # 处理单条数据
                self._process_single_data(data)

                # 控制流水线运行状态
                if not self._running:
                    break

        except KeyboardInterrupt:
            logger.info("接收到手动停止指令（Ctrl+C）")
        except Exception as e:
            logger.error(f"流水线运行异常: {str(e)}", exc_info=True)
        finally:
            # 停止流水线与资源清理
            self.stop()

    # def stop(self) -> None:
    #     """停止流水线并清理资源"""
    #     if not self._running:
    #         # 即便未运行，也确保资源关闭
    #         for storage_name, storage in self.storages.items():
    #             if hasattr(storage, "close"):
    #                 try:
    #                     storage.close()
    #                 except Exception:
    #                     pass
    #         return

    #     # 1. 停止数据生成器
    #     if self.data_generator:
    #         try:
    #             self.data_generator.close()
    #         except Exception:
    #             pass
    #         logger.info("数据生成器已停止")

    #     # 2. 关闭存储连接
    #     for storage_name, storage in self.storages.items():
    #         if hasattr(storage, "close"):
    #             storage.close()
    #             logger.info(f"{storage_name.upper()}存储已关闭")

    #     # 3. 更新运行状态
    #     self._running = False
    #     logger.info("传感器数据处理流水线已完全停止")
        # 在 stop() 中批量缓存的收尾冲刷
    def stop(self) -> None:
        if not self._running:
            # 若外部重复调用，也确保资源关闭
            for storage_name, storage in self.storages.items():
                if hasattr(storage, "close"):
                    try:
                        storage.close()
                    except Exception:
                        pass
            return

        # 先冲刷缓存，避免丢数据
        if hasattr(self, "data_cache") and self.data_cache and "sqlite" in self.storages:
            try:
                self.storages["sqlite"].batch_insert(self.data_cache)
                logger.info(f"缓存数据已批量写入（{len(self.data_cache)}条）")
            except Exception as e:
                logger.error(f"缓存数据写入失败: {e}")
            finally:
                self.data_cache = []

        # 其余与原实现一致...
        if self.data_generator:
            try:
                self.data_generator.close()
            except Exception:
                pass
            logger.info("数据生成器已停止")

        for storage_name, storage in self.storages.items():
            if hasattr(storage, "close"):
                storage.close()
                logger.info(f"{storage_name.upper()}存储已关闭")

        self._running = False
        logger.info("传感器数据处理流水线已完全停止")

    def get_pipeline_status(self) -> Dict:
        """获取流水线运行状态"""
        # 查询已存储的数据总量
        data_count = 0
        if "sqlite" in self.storages:
            try:
                data_count = self.storages["sqlite"].get_data_count(
                    sensor_id=self.sensor_id,
                    data_type=self.data_type
                )
            except Exception:
                data_count = 0

        return {
            "running": self._running,
            "sensor_id": self.sensor_id,
            "data_type": self.data_type,
            "storage_type": self.storage_type,
            "stored_data_count": data_count,
            "resource_monitor_enabled": self.resource_monitor_interval > 0
        }