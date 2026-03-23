"""
SQLite 持久化存储

负责 JobItem 的持久化和去重查询。
"""

import logging
import os
import sqlite3
from typing import Optional

from processor.models import JobItem

logger = logging.getLogger(__name__)


class JobStorage:
    """基于 SQLite 的职位数据存储"""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self):
        """初始化数据库表"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT DEFAULT '',
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published_at TEXT,
                    description TEXT DEFAULT '',
                    salary TEXT DEFAULT '',
                    keywords TEXT DEFAULT '',
                    is_remote INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)
            """)

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def get_existing_job_ids(self, job_ids: list[str]) -> set[str]:
        """批量检查哪些 job_id 已存在"""
        if not job_ids:
            return set()

        with self._connect() as conn:
            placeholders = ",".join("?" for _ in job_ids)
            cursor = conn.execute(
                f"SELECT job_id FROM jobs WHERE job_id IN ({placeholders})",
                job_ids,
            )
            return {row[0] for row in cursor.fetchall()}

    def save_jobs(self, jobs: list[JobItem]) -> int:
        """
        批量保存职位数据，返回实际保存的数量。
        使用 INSERT OR IGNORE 避免重复插入。
        """
        if not jobs:
            return 0

        saved = 0
        with self._connect() as conn:
            for job in jobs:
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO jobs 
                        (job_id, title, company, location, url, source, 
                         published_at, description, salary, keywords, is_remote)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job.job_id,
                            job.title,
                            job.company,
                            job.location,
                            job.url,
                            job.source,
                            job.published_at.isoformat() if job.published_at else None,
                            job.description,
                            job.salary,
                            ",".join(job.keywords),
                            1 if job.is_remote else 0,
                        ),
                    )
                    if conn.total_changes:
                        saved += 1
                except sqlite3.Error as e:
                    logger.error(f"保存职位失败 [{job.job_id}]: {e}")

        logger.info(f"保存了 {saved}/{len(jobs)} 条职位数据")
        return saved

    def job_exists(self, job_id: str) -> bool:
        """检查单个 job_id 是否已存在"""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
            )
            return cursor.fetchone() is not None

    def get_job_count(self) -> int:
        """获取总职位数"""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            return cursor.fetchone()[0]
