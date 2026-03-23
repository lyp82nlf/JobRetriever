"""
职位筛选器

根据用户偏好对搜索结果进行筛选，支持：
- 地区筛选（指定城市/地区）
- 远程工作筛选
- 排除关键词（如排除某些公司或职位类型）

所有配置通过 ENV 环境变量管理，未填则使用默认值（不筛选）。
"""

import logging
import os
import re

from processor.models import JobItem

logger = logging.getLogger(__name__)


class JobFilter:
    """
    职位筛选器

    ENV 配置:
        JOB_FILTER_LOCATIONS      - 期望的地区，逗号分隔，如 "北京,上海,深圳"
        JOB_FILTER_REMOTE         - 是否只看远程职位: true/false（默认 false）
        JOB_FILTER_EXCLUDE_WORDS  - 排除包含这些关键词的职位，逗号分隔
        JOB_FILTER_INCLUDE_WORDS  - 必须包含这些关键词之一（标题/描述），逗号分隔
        JOB_FILTER_MIN_SALARY     - 最低薪资（数字，单位 K），如 15
        JOB_FILTER_COMPANIES_EXCLUDE - 排除的公司名，逗号分隔
    """

    def __init__(self):
        self.locations = self._parse_list("JOB_FILTER_LOCATIONS")
        self.remote_only = self._parse_bool("JOB_FILTER_REMOTE", False)
        self.exclude_words = self._parse_list("JOB_FILTER_EXCLUDE_WORDS")
        self.include_words = self._parse_list("JOB_FILTER_INCLUDE_WORDS")
        self.min_salary = self._parse_int("JOB_FILTER_MIN_SALARY", 0)
        self.companies_exclude = self._parse_list("JOB_FILTER_COMPANIES_EXCLUDE")

        self._log_config()

    def filter(self, jobs: list[JobItem]) -> list[JobItem]:
        """
        对职位列表进行筛选。

        Args:
            jobs: 待筛选的职位列表

        Returns:
            符合条件的职位列表
        """
        if not jobs:
            return []

        before = len(jobs)
        filtered = [job for job in jobs if self._match(job)]
        after = len(filtered)

        if before != after:
            logger.info(f"🔽 筛选: {before} 条 → {after} 条（过滤了 {before - after} 条）")
        else:
            logger.info(f"🔽 筛选: {before} 条全部通过")

        return filtered

    def _match(self, job: JobItem) -> bool:
        """检查单个职位是否符合所有筛选条件"""
        text = f"{job.title} {job.description}".lower()
        location_text = job.location.lower()

        # 1. 地区筛选
        if self.locations:
            location_match = any(loc.lower() in location_text for loc in self.locations)
            # 远程职位也算通过地区筛选
            if not location_match and not job.is_remote:
                return False

        # 2. 远程工作筛选（由搜索任务在抓取时判断并标记）
        if self.remote_only and not job.is_remote:
            return False

        # 3. 排除关键词
        if self.exclude_words:
            if any(word.lower() in text for word in self.exclude_words):
                return False

        # 4. 必须包含关键词
        if self.include_words:
            if not any(word.lower() in text for word in self.include_words):
                return False

        # 5. 排除公司
        if self.companies_exclude:
            company_lower = job.company.lower()
            if any(c.lower() in company_lower for c in self.companies_exclude):
                return False

        # 6. 最低薪资
        if self.min_salary > 0 and job.salary:
            salary_num = self._extract_salary(job.salary)
            if salary_num > 0 and salary_num < self.min_salary:
                return False

        return True

    @staticmethod
    def _extract_salary(salary_str: str) -> int:
        """
        从薪资字符串中提取数字（粗略提取最低值，单位 K）。
        例如: "15K-25K" → 15, "15000-25000" → 15, "面议" → 0
        """
        # 匹配 "15K" 或 "15k" 格式
        match = re.search(r"(\d+)\s*[kK]", salary_str)
        if match:
            return int(match.group(1))

        # 匹配纯数字（假设单位为元/月，转换为 K）
        match = re.search(r"(\d+)", salary_str)
        if match:
            num = int(match.group(1))
            if num >= 1000:
                return num // 1000
            return num

        return 0

    def _log_config(self):
        """打印当前筛选配置"""
        active = []
        if self.locations:
            active.append(f"地区={self.locations}")
        if self.remote_only:
            active.append("仅远程")
        if self.exclude_words:
            active.append(f"排除词={self.exclude_words}")
        if self.include_words:
            active.append(f"包含词={self.include_words}")
        if self.min_salary > 0:
            active.append(f"最低薪资={self.min_salary}K")
        if self.companies_exclude:
            active.append(f"排除公司={self.companies_exclude}")

        if active:
            logger.info(f"🔧 筛选器配置: {', '.join(active)}")
        else:
            logger.info("🔧 筛选器: 未设置任何筛选条件（全部通过）")

    @staticmethod
    def _parse_list(env_key: str) -> list[str]:
        """解析逗号分隔的环境变量为列表"""
        val = os.environ.get(env_key, "").strip()
        if not val:
            return []
        return [item.strip() for item in val.split(",") if item.strip()]

    @staticmethod
    def _parse_bool(env_key: str, default: bool) -> bool:
        """解析布尔型环境变量"""
        val = os.environ.get(env_key, "").strip().lower()
        if val in ("true", "1", "yes"):
            return True
        if val in ("false", "0", "no"):
            return False
        return default

    @staticmethod
    def _parse_int(env_key: str, default: int) -> int:
        """解析整数型环境变量"""
        val = os.environ.get(env_key, "").strip()
        if val.isdigit():
            return int(val)
        return default
