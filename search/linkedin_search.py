"""
LinkedIn 搜索任务

通过 LinkedIn 职位搜索页面抓取职位信息。
注意：这是一个示例实现，实际使用时可能需要根据
LinkedIn 的反爬策略进行调整（如使用代理、增加延迟等）。
"""

import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from processor.models import JobItem
from search.base import BaseSearchTask

logger = logging.getLogger(__name__)


class LinkedInSearchTask(BaseSearchTask):
    """LinkedIn 职位搜索任务"""

    # LinkedIn 公开的职位搜索 API（不需要登录）
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    @property
    def source_name(self) -> str:
        return "linkedin"

    def search(self, keywords: list[str]) -> list[JobItem]:
        """搜索 LinkedIn 职位"""
        all_jobs = []

        for keyword in keywords:
            jobs = self._search_keyword(keyword)
            all_jobs.extend(jobs)

        return all_jobs

    def _search_keyword(self, keyword: str, location: str = "", start: int = 0) -> list[JobItem]:
        """按单个关键词搜索"""
        params = {
            "keywords": keyword,
            "location": location,
            "start": start,
            "f_TPR": "r86400",  # 过去24小时
            "f_sort": "DD",     # 按日期排序
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                proxies=self.proxies,
                timeout=30,
            )
            response.raise_for_status()
            return self._parse_response(response.text, keyword)
        except requests.RequestException as e:
            logger.error(f"[linkedin] 请求失败 (keyword={keyword}): {e}")
            return []

    def _parse_response(self, html: str, keyword: str) -> list[JobItem]:
        """解析 LinkedIn 搜索结果页面"""
        jobs = []
        soup = BeautifulSoup(html, "html.parser")

        job_cards = soup.find_all("div", class_="base-card")

        for card in job_cards:
            try:
                job = self._parse_job_card(card, keyword)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[linkedin] 解析职位卡片失败: {e}")
                continue

        return jobs

    def _parse_job_card(self, card, keyword: str) -> Optional[JobItem]:
        """解析单个职位卡片"""
        # 职位标题
        title_elem = card.find("h3", class_="base-search-card__title")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # 公司名称
        company_elem = card.find("h4", class_="base-search-card__subtitle")
        company = company_elem.get_text(strip=True) if company_elem else ""

        # 工作地点
        location_elem = card.find("span", class_="job-search-card__location")
        location = location_elem.get_text(strip=True) if location_elem else ""

        # 链接
        link_elem = card.find("a", class_="base-card__full-link")
        url = link_elem.get("href", "").strip() if link_elem else ""

        # 发布时间
        time_elem = card.find("time")
        published_at = None
        if time_elem and time_elem.get("datetime"):
            try:
                published_at = datetime.fromisoformat(time_elem["datetime"])
            except (ValueError, TypeError):
                pass

        if not title or not url:
            return None

        # 由搜索任务判断是否远程
        is_remote = self.detect_remote(title, location)

        return JobItem(
            title=title,
            company=company,
            location=location,
            url=url,
            source=self.source_name,
            published_at=published_at,
            keywords=[keyword],
            is_remote=is_remote,
        )
