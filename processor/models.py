"""
统一数据模型 - JobItem

所有搜索任务的输出都必须转换为 JobItem，
确保数据处理层和消息处理层拥有一致的数据结构。
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class JobItem:
    """职位信息的统一数据模型"""

    title: str                              # 职位名称
    company: str                            # 公司名称
    url: str                                # 原始链接
    source: str                             # 来源标识（如 "linkedin"）
    location: str = ""                      # 工作地点
    published_at: Optional[datetime] = None # 发布时间
    description: str = ""                   # 职位描述（摘要）
    salary: str = ""                        # 薪资信息
    keywords: list[str] = field(default_factory=list)  # 匹配的关键词
    is_remote: bool = False                 # 是否远程（由搜索任务判断）
    job_id: str = ""                        # 唯一标识（自动生成）

    def __post_init__(self):
        """如果未提供 job_id，则根据 source + url 自动生成"""
        if not self.job_id:
            raw = f"{self.source}:{self.url}"
            self.job_id = hashlib.md5(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        """转换为字典，方便存储"""
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "description": self.description,
            "salary": self.salary,
            "keywords": ",".join(self.keywords),
            "is_remote": self.is_remote,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobItem":
        """从字典恢复 JobItem"""
        published_at = None
        if data.get("published_at"):
            try:
                published_at = datetime.fromisoformat(data["published_at"])
            except (ValueError, TypeError):
                pass

        keywords = []
        if data.get("keywords"):
            keywords = data["keywords"].split(",") if isinstance(data["keywords"], str) else data["keywords"]

        return cls(
            job_id=data.get("job_id", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            url=data.get("url", ""),
            source=data.get("source", ""),
            published_at=published_at,
            description=data.get("description", ""),
            salary=data.get("salary", ""),
            keywords=keywords,
            is_remote=bool(data.get("is_remote", False)),
        )
