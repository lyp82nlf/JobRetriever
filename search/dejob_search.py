"""
DeJob 搜索任务

通过 DeJob (dejob.ai) 公开 API 搜索 Web3 相关职位。
"""

import logging
import time
from datetime import datetime
from typing import Optional

import requests

from processor.models import JobItem
from search.base import BaseSearchTask

logger = logging.getLogger(__name__)


class DeJobSearchTask(BaseSearchTask):
    """DeJob (dejob.ai) 职位搜索任务"""

    BASE_URL = "https://dejob.ai/api/worker/topics"

    # officeModeId 含义
    OFFICE_MODE_REMOTE = 1      # 远程
    OFFICE_MODE_ONSITE = 2      # 实地
    OFFICE_MODE_HYBRID = 0      # 远程/实地

    @property
    def source_name(self) -> str:
        return "dejob"

    def __init__(self):
        super().__init__()

    def search(self, keywords: list[str]) -> list[JobItem]:
        """搜索 DeJob 职位"""
        all_jobs = []

        for keyword in keywords:
            jobs = self._search_keyword(keyword)
            all_jobs.extend(jobs)

        return all_jobs

    def _search_keyword(self, keyword: str, max_pages: int = 3) -> list[JobItem]:
        """
        按关键词搜索，支持翻页。

        Args:
            keyword: 搜索关键词
            max_pages: 最多翻页数（每页20条）
        """
        all_jobs = []

        for page in range(1, max_pages + 1):
            jobs, total = self._fetch_page(keyword, page)
            all_jobs.extend(jobs)

            # 如果已获取全部结果，停止翻页
            if page * 20 >= total:
                break

            # 翻页间隔，避免请求过快
            time.sleep(0.5)

        return all_jobs

    def _fetch_page(self, keyword: str, page: int = 1, limit: int = 20) -> tuple[list[JobItem], int]:
        """
        请求单页数据。

        Returns:
            (职位列表, 总数)
        """
        params = {
            "page": page,
            "limit": limit,
            "keyword": keyword,
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh",
            "Referer": "https://dejob.ai/job",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                proxies=self.proxies,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errorCode") != 0:
                logger.error(f"[dejob] API 返回错误: {data.get('message')}")
                return [], 0

            results = data.get("data", {}).get("results", [])
            total = data.get("data", {}).get("page", {}).get("total", 0)

            jobs = []
            for item in results:
                job = self._parse_item(item, keyword)
                if job:
                    jobs.append(job)

            logger.info(
                f"[dejob] keyword={keyword}, page={page}, "
                f"本页 {len(jobs)} 条, 总共 {total} 条"
            )
            return jobs, total

        except requests.RequestException as e:
            logger.error(f"[dejob] 请求失败 (keyword={keyword}, page={page}): {e}")
            return [], 0

    def _parse_item(self, item: dict, keyword: str) -> Optional[JobItem]:
        """解析单条职位数据"""
        topic_id = item.get("topicId")
        if not topic_id:
            return None

        # 职位名称
        title = item.get("positionName", "")

        # 公司名称
        company = item.get("company", "")

        # 工作地点（base 字段，如 "深圳/北京", "远程", "remote"）
        location = item.get("base", "") or item.get("location", "")

        # 详情链接
        url = item.get("url", "") or f"https://dejob.ai/jobDetail?id={topic_id}"

        # 发布时间（毫秒时间戳）
        published_at = None
        create_time = item.get("createTime")
        if create_time:
            try:
                published_at = datetime.fromtimestamp(create_time / 1000)
            except (ValueError, TypeError, OSError):
                pass

        # 职位描述（岗位职责）
        description = item.get("content", "")

        # 薪资（minSalary / maxSalary，单位 USD）
        salary = self._format_salary(
            item.get("minSalary"), item.get("maxSalary")
        )

        # 是否远程（officeModeId: 1=远程, 0=远程/实地, 2=实地）
        office_mode_id = item.get("officeModeId")
        is_remote = office_mode_id in (self.OFFICE_MODE_REMOTE, self.OFFICE_MODE_HYBRID)

        # 也可以用 detect_remote 作为补充判断
        if not is_remote:
            is_remote = self.detect_remote(title, location, description)

        # 标签
        tags = [tag.get("tagName", "") for tag in item.get("tags", []) if tag.get("tagName")]

        # 额外信息拼接到描述
        content2 = item.get("content2", "")  # 任职要求
        content3 = item.get("content3", "")  # 福利/备注
        if content2:
            description += f"\n\n【任职要求】\n{content2}"
        if content3:
            description += f"\n\n【福利待遇】\n{content3}"

        # 工作类型
        work_type = item.get("workTypeName", "")  # 全职/兼职
        office_mode = item.get("officeModeName", "")  # 远程/实地

        return JobItem(
            job_id=f"dejob_{topic_id}",
            title=f"{title} ({work_type}/{office_mode})" if work_type else title,
            company=company,
            location=location,
            url=url,
            source=self.source_name,
            published_at=published_at,
            description=description,
            salary=salary,
            keywords=[keyword] + tags,
            is_remote=is_remote,
        )

    @staticmethod
    def _format_salary(min_salary: Optional[int], max_salary: Optional[int]) -> str:
        """格式化薪资范围（USD）"""
        if not min_salary and not max_salary:
            return "面议"

        if min_salary and max_salary:
            return f"${min_salary}-${max_salary}/月"
        elif min_salary:
            return f"${min_salary}+/月"
        elif max_salary:
            return f"最高${max_salary}/月"

        return "面议"
