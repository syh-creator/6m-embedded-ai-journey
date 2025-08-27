import sqlite3
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger('sqlite_storage')


class SQLiteStorage:
    """
    SQLite数据存储类：适配嵌入式设备的轻量级数据库存储方案
    支持传感器数据的增删改查，内置事务与数据迁移支持
    """

    def __init__(self, db_path: str = "data/sensor_db.sqlite"):
        """
        初始化SQLite存储
        :param db_path: 数据库文件路径（默认存储在data目录）
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        # 确保存储目录存在
        self._ensure_dir_exists()
        # 初始化数据库连接
        self._init_connection()
        # 创建传感器数据表
        self._create_tables()

    def _ensure_dir_exists(self) -> None:
        """确保数据库存储目录存在"""
        dir_path = os.path.dirname(self.db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"创建数据库目录: {dir_path}")

    def _init_connection(self) -> None:
        """初始化数据库连接（线程不安全，嵌入式单线程场景适用）"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # 嵌入式单线程环境关闭线程检查
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # 设置行工厂，查询结果返回字典格式
            self.conn.row_factory = sqlite3.Row
            # 基础PRAGMA设置，提升一致性与性能
            with self.conn:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.execute("PRAGMA synchronous=NORMAL;")  # 可按设备选择 FULL/NORMAL
                self.conn.execute("PRAGMA foreign_keys=ON;")
            logger.info(f"成功连接数据库: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise RuntimeError(f"SQLite连接错误: {str(e)}") from e

    def _ensure_connection(self) -> None:
        """确保连接可用（若已关闭则重连）"""
        if self.conn is None:
            self._init_connection()

    def _create_tables(self) -> None:
        """创建传感器数据表结构"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            data_type TEXT NOT NULL,
            raw_value REAL NOT NULL,
            is_outlier INTEGER NOT NULL DEFAULT 0, -- SQLite用0/1表示布尔
            sequence INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            -- 唯一约束，避免重插
            UNIQUE(sensor_id, sequence)
        );
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(create_table_sql)
            # 索引优化（SQLite需独立CREATE INDEX）
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_id ON sensor_data(sensor_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_type ON sensor_data(data_type);")
            self.conn.commit()
            logger.info("传感器数据表初始化完成（或已存在）")
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"创建数据表失败: {str(e)}")
            raise

    def batch_insert(self, data_list: List[Dict]) -> int:
        """
        批次插入传感器数据（支持事务）

        :param data_list: 数据列表，每个元素需包含sensor_id/data_type/raw_value等字段
        :return: 成功插入的记录数
        """
        if not data_list:
            logger.warning("插入数据为空列表，跳过操作")
            return 0

        # 定义插入SQL模板
        insert_sql = """
        INSERT OR IGNORE INTO sensor_data 
        (sensor_id, data_type, raw_value, is_outlier, sequence, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        # 准备插入数据（按SQL字段顺序整理）
        insert_data = []
        required_fields = ["sensor_id", "data_type", "raw_value", "is_outlier", "sequence", "timestamp"]
        for data in data_list:
            # 验证必填字段
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                logger.warning(f"数据缺少必填字段 {missing_fields}，跳过该条数据: {data}")
                continue
            # 转换布尔值（SQLite无布尔类型，用0/1存储）
            is_outlier = 1 if data["is_outlier"] else 0
            insert_data.append([
                data["sensor_id"],
                data["data_type"],
                data["raw_value"],
                is_outlier,
                data["sequence"],
                data["timestamp"]
            ])

        if not insert_data:
            logger.warning("无有效数据可插入，跳过操作")
            return 0

        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            before_changes = self.conn.total_changes
            # 执行批次插入（executemany效率高于循环execute）
            cursor.executemany(insert_sql, insert_data)
            self.conn.commit()
            inserted_count = self.conn.total_changes - before_changes  # 更准确（考虑OR IGNORE）
            logger.info(f"成功插入{inserted_count}条数据（重复数据已忽略）")
            return inserted_count
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"批次插入失败: {str(e)}")
            raise

    def query_data(
        self,
        sensor_id: Optional[str] = None,
        data_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        is_outlier: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        多条件查询传感器数据

        :param sensor_id: 传感器ID（精确匹配）
        :param data_type: 数据类型（精确匹配）
        :param start_time: 开始时间戳（大于等于）
        :param end_time: 结束时间戳（小于等于）
        :param is_outlier: 是否异常值（0/1）
        :param limit: 查询条数限制
        :param offset: 查询偏移量（分页用）
        :return: 查询结果列表（字典格式）
        """
        # 构建查询条件
        query_conditions = []
        query_params = []

        if sensor_id:
            query_conditions.append("sensor_id = ?")
            query_params.append(sensor_id)
        if data_type:
            query_conditions.append("data_type = ?")
            query_params.append(data_type)
        if start_time is not None:
            query_conditions.append("timestamp >= ?")
            query_params.append(start_time)
        if end_time is not None:
            query_conditions.append("timestamp <= ?")
            query_params.append(end_time)
        if is_outlier is not None:
            query_conditions.append("is_outlier = ?")
            query_params.append(1 if is_outlier else 0)

        # 构建完整SQL
        where_clause = "WHERE " + " AND ".join(query_conditions) if query_conditions else ""
        query_sql = f"""
        SELECT id, sensor_id, data_type, raw_value, is_outlier, 
               sequence, timestamp, create_time
        FROM sensor_data
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?;
        """
        # 添加分页参数
        query_params.extend([limit, offset])

        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute(query_sql, query_params)
            # 将Row对象转换为字典
            results = [dict(row) for row in cursor.fetchall()]
            logger.info(f"查询到{len(results)}条数据（条件: {query_conditions}）")
            return results
        except sqlite3.Error as e:
            logger.error(f"数据查询失败: {str(e)}")
            raise

    def get_data_count(self, **query_filters) -> int:
        """
        获取符合条件的数据总数（用于分页计算）

        :param query_filters: 查询过滤条件（同query_data方法）
        :return: 符合条件的记录数
        """
        # 复用query_data的条件构建逻辑
        query_conditions = []
        query_params = []

        if "sensor_id" in query_filters and query_filters["sensor_id"] is not None:
            query_conditions.append("sensor_id = ?")
            query_params.append(query_filters["sensor_id"])
        if "data_type" in query_filters and query_filters["data_type"] is not None:
            query_conditions.append("data_type = ?")
            query_params.append(query_filters["data_type"])
        if "is_outlier" in query_filters and query_filters["is_outlier"] is not None:
            query_conditions.append("is_outlier = ?")
            query_params.append(1 if query_filters["is_outlier"] else 0)

        where_clause = "WHERE " + " AND ".join(query_conditions) if query_conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM sensor_data {where_clause};"

        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute(count_sql, query_params)
            result = cursor.fetchone()
            total = result["total"] if result else 0
            logger.info(f"符合条件的数据总数: {total}")
            return total
        except sqlite3.Error as e:
            logger.error(f"计数查询失败: {str(e)}")
            raise

    def close(self) -> None:
        """关闭数据库连接（嵌入式设备休眠前必须调用）"""
        if self.conn:
            self.conn.close()
            logger.info(f"数据库连接已关闭: {self.db_path}")
            self.conn = None

    def __del__(self) -> None:
        """析构函数：确保对象销毁时关闭连接"""
        try:
            self.close()
        except Exception:
            pass