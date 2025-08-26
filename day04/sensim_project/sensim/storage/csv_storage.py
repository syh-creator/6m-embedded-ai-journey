import csv
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger('csv_storage')


class CSVStorage:
    """
    CSV数据存储类：支持批次写入、数据追加，适配嵌入式设备存储需求
    """
    def __init__(self, file_path: str, headers: Optional[List[str]] = None):
        """
        初始化CSV存储

        :param file_path: 存储文件路径
        :param headers: CSV表头（如未指定，从第一条数据自动提取）
        """
        self.file_path = file_path
        self.headers = headers
        # 确保存储目录存在
        self._ensure_dir_exists()

    def _ensure_dir_exists(self) -> None:
        """确保存储目录存在，不存在则创建"""
        dir_path = os.path.dirname(self.file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"创建存储目录: {dir_path}")

    def batch_write(self, data_list: List[Dict[str, Any]], mode: str = "w") -> None:
        """
        批次写入数据到CSV

        :param data_list: 数据列表（每个元素为字典）
        :param mode: 写入模式（w: 覆盖写入，a: 追加写入）
        :raises ValueError: 数据列表为空或表头不匹配时抛出
        """
        if not data_list:
            raise ValueError("写入数据不能为空列表")

        # 自动提取表头（若未指定）
        if not self.headers:
            self.headers = list(data_list[0].keys())
            logger.info(f"自动提取CSV表头: {self.headers}")

        # 验证所有数据的键与表头一致
        for idx, data in enumerate(data_list):
            if set(data.keys()) != set(self.headers):
                raise ValueError(f"第{idx+1}条数据键与表头不匹配: {list(data.keys())} vs {self.headers}")

        # 判断是否需要写表头
        write_header = mode == "w"
        if mode == "a" and (not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0):
            write_header = True

        # 批次写入
        with open(self.file_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            if write_header:
                writer.writeheader()
            writer.writerows(data_list)

        logger.info(f"成功写入{len(data_list)}条数据到CSV: {self.file_path}（模式: {mode}）")

    def append_data(self, data: Dict[str, Any]) -> None:
        """
        追加单条数据到CSV（内部转为批次写入，减少IO）

        :param data: 单条数据字典
        """
        self.batch_write([data], mode="a")

    def get_data_count(self) -> int:
        """获取CSV文件中的数据行数（不含表头）"""
        if not os.path.exists(self.file_path):
            return 0

        with open(self.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # 跳过表头，统计数据行
            next(reader, None)  # 忽略表头
            return sum(1 for _ in reader)