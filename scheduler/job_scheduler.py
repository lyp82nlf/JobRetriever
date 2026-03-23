"""
任务调度器

编排完整的流水线：搜索 → 数据处理 → 消息通知。
使用 APScheduler 实现定时调度，每个搜索任务独立执行。
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from notifier.base import BaseNotifier
from processor.data_processor import DataProcessor
from search.base import BaseSearchTask

logger = logging.getLogger(__name__)


class JobScheduler:
    """职位搜索调度器"""

    def __init__(
        self,
        search_tasks: list[BaseSearchTask],
        processor: DataProcessor,
        notifiers: list[BaseNotifier],
        keywords: list[str],
        interval_minutes: int = 30,
    ):
        self.search_tasks = search_tasks
        self.processor = processor
        self.notifiers = notifiers
        self.keywords = keywords
        self.interval_minutes = interval_minutes
        self.scheduler = BlockingScheduler()

    def run_once(self):
        """立即执行一次完整的搜索-处理-通知流水线"""
        logger.info("=" * 60)
        logger.info("🚀 开始执行职位搜索流水线")
        logger.info(f"   关键词: {self.keywords}")
        logger.info(f"   搜索任务: {[t.source_name for t in self.search_tasks]}")
        logger.info(f"   通知渠道: {[n.channel_name for n in self.notifiers]}")
        logger.info("=" * 60)

        # === 第一阶段：搜索 ===
        all_jobs = []
        for task in self.search_tasks:
            results = task.safe_search(self.keywords)
            all_jobs.extend(results)

        logger.info(f"📊 所有搜索任务共找到 {len(all_jobs)} 条职位")

        if not all_jobs:
            logger.info("⏹️ 没有搜索到任何职位，本轮结束")
            return

        # === 第二阶段：数据处理（去重） ===
        new_jobs = self.processor.process(all_jobs)

        if not new_jobs:
            logger.info("⏹️ 没有新增职位，本轮结束")
            return

        logger.info(f"🆕 发现 {len(new_jobs)} 条新职位")

        # === 第三阶段：消息通知 ===
        if not self.notifiers:
            logger.warning("⚠️ 没有可用的通知渠道，跳过消息发送")
            return

        for notifier in self.notifiers:
            notifier.safe_notify(new_jobs)

        logger.info("✅ 本轮职位搜索流水线执行完毕")

    def start(self):
        """启动定时调度"""
        logger.info(
            f"⏰ 启动定时调度，每 {self.interval_minutes} 分钟执行一次"
        )

        # 立即执行一次
        self.run_once()

        # 添加定时任务
        self.scheduler.add_job(
            self.run_once,
            "interval",
            minutes=self.interval_minutes,
            id="job_search_pipeline",
            name="职位搜索流水线",
        )

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 调度器已停止")
