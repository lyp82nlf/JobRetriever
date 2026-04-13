"""
搜索任务抽象基类

所有搜索任务必须继承 BaseSearchTask 并实现 search() 方法。
每个搜索任务独立执行，互不干扰。
支持通过 ENV 配置 HTTP/SOCKS 代理。
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from processor.models import JobItem

logger = logging.getLogger(__name__)


def get_proxy_config() -> Optional[dict]:
    """
    从环境变量读取代理配置。

    ENV:
        HTTP_PROXY   - HTTP 代理，如 http://127.0.0.1:7890
        HTTPS_PROXY  - HTTPS 代理，如 http://127.0.0.1:7890
        SOCKS_PROXY  - SOCKS5 代理，如 socks5://127.0.0.1:7891

    优先级: SOCKS_PROXY > HTTP_PROXY/HTTPS_PROXY
    """
    socks = os.environ.get("SOCKS_PROXY", "").strip()
    http_proxy = os.environ.get("HTTP_PROXY", "").strip()
    https_proxy = os.environ.get("HTTPS_PROXY", "").strip()

    if socks:
        logger.info(f"🌐 使用 SOCKS 代理: {socks}")
        return {"http": socks, "https": socks}

    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        logger.info(f"🌐 使用 HTTP 代理: {proxies}")
        return proxies

    return None


class BaseSearchTask(ABC):
    """搜索任务抽象基类"""

    # 远程工作相关的常见关键词（子类可以扩展）
    REMOTE_KEYWORDS = [
        "remote", "远程", "居家", "在家办公", "work from home",
        "wfh", "全远程", "hybrid", "混合办公",
    ]

    def __init__(self):
        self.proxies = get_proxy_config()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        搜索源的唯一名称标识。
        例如: "linkedin", "indeed", "boss"
        """
        pass

    @abstractmethod
    def search(self, keywords: list[str]) -> list[JobItem]:
        """
        根据关键词列表搜索职位。

        Args:
            keywords: 关键词列表，如 ["android", "kotlin"]

        Returns:
            统一格式的 JobItem 列表。
            搜索任务需要负责判断 is_remote 字段。
        """
        pass

    def detect_remote(self, title: str, location: str, description: str = "") -> bool:
        """
        判断职位是否为远程工作。
        子类可以覆盖此方法以实现更精准的判断逻辑。

        Args:
            title: 职位标题
            location: 工作地点
            description: 职位描述

        Returns:
            是否为远程工作
        """
        text = f"{title} {location} {description}".lower()
        return any(kw in text for kw in self.REMOTE_KEYWORDS)

    def safe_search(self, keywords: list[str]) -> list[JobItem]:
        """
        安全执行搜索，捕获所有异常防止影响其他任务。

        Args:
            keywords: 关键词列表

        Returns:
            搜索结果，如果出错则返回空列表
        """
        try:
            logger.info(f"[{self.source_name}] 开始搜索，关键词: {keywords}")
            results = self.search(keywords)
            logger.info(f"[{self.source_name}] 搜索完成，找到 {len(results)} 条职位")
            return results
        except Exception as e:
            logger.error(f"[{self.source_name}] 搜索失败: {e}", exc_info=True)
            return []
