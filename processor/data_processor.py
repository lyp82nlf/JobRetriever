"""
数据处理器

接收搜索层的 JobItem 列表，先进行筛选，
再与数据库对比去重，返回新增的职位并保存到数据库。
"""

import logging

from processor.filters import JobFilter
from processor.models import JobItem
from processor.storage import JobStorage

logger = logging.getLogger(__name__)


class DataProcessor:
    """数据处理层核心类"""

    def __init__(self, storage: JobStorage, job_filter: JobFilter | None = None):
        self.storage = storage
        self.job_filter = job_filter or JobFilter()

    def process(self, jobs: list[JobItem]) -> list[JobItem]:
        """
        处理搜索结果：
        1. 筛选（地区、远程、关键词等）
        2. 提取所有 job_id
        3. 批量查询已存在的 job_id
        4. 过滤出新增的 JobItem
        5. 保存新增数据到数据库
        6. 返回新增的 JobItem 列表
        """
        if not jobs:
            logger.info("没有需要处理的职位数据")
            return []

        # 第一步：筛选
        filtered_jobs = self.job_filter.filter(jobs)
        if not filtered_jobs:
            logger.info(f"搜索到 {len(jobs)} 条职位，筛选后无符合条件的")
            return []

        # 第二步：去重
        candidate_ids = [job.job_id for job in filtered_jobs]
        existing_ids = self.storage.get_existing_job_ids(candidate_ids)
        new_jobs = [job for job in filtered_jobs if job.job_id not in existing_ids]

        if not new_jobs:
            logger.info(
                f"搜索 {len(jobs)} → 筛选 {len(filtered_jobs)} → 无新增"
            )
            return []

        # 第三步：保存
        self.storage.save_jobs(new_jobs)

        logger.info(
            f"搜索 {len(jobs)} → 筛选 {len(filtered_jobs)} → "
            f"已存在 {len(existing_ids)} → 新增 {len(new_jobs)}"
        )

        return new_jobs
