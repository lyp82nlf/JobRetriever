"""
JobRetriever - 职位抓取与通知系统

使用方式:
    # 立即执行一次（测试用）
    python main.py --once

    # 启动定时调度
    python main.py
"""

import argparse
import logging
import os
import sys

import yaml
from dotenv import load_dotenv

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notifier import create_active_notifiers
from processor.data_processor import DataProcessor
from processor.storage import JobStorage
from scheduler.job_scheduler import JobScheduler
from search.dejob_search import DeJobSearchTask
from search.linkedin_search import LinkedInSearchTask


# ============================================================
# 搜索任务注册表
# key = settings.yaml 中的 search_tasks 名称
# value = 搜索任务类
# ============================================================
SEARCH_TASK_REGISTRY = {
    "dejob": DeJobSearchTask,
    "linkedin": LinkedInSearchTask,
}


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 降低第三方库日志级别
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """加载 YAML 配置文件"""
    abs_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), config_path
    )
    with open(abs_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_search_tasks(task_names: list[str]) -> list:
    """根据配置创建搜索任务实例"""
    tasks = []
    for name in task_names:
        cls = SEARCH_TASK_REGISTRY.get(name)
        if cls:
            tasks.append(cls())
            logging.info(f"✅ 搜索任务已注册: {name}")
        else:
            logging.warning(
                f"⚠️ 未知的搜索任务: {name}，"
                f"可用: {list(SEARCH_TASK_REGISTRY.keys())}"
            )
    return tasks


def main():
    """主入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="JobRetriever - 职位抓取与通知系统"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="立即执行一次搜索（不启动定时调度）",
    )
    args = parser.parse_args()

    # 初始化
    setup_logging()
    logger = logging.getLogger(__name__)

    # 加载 .env 环境变量
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)

    # 加载配置
    config = load_config()
    db_path = config.get("database_path", "data/jobs.db")
    task_names = config.get("search_tasks", ["linkedin"])

    # 从 ENV 读取关键词和调度间隔
    keywords_str = os.environ.get("JOB_SEARCH_KEYWORDS", "android").strip()
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    interval = int(os.environ.get("JOB_SCHEDULE_INTERVAL", "30"))

    logger.info("=" * 60)
    logger.info("🚀 JobRetriever 启动")
    logger.info(f"   关键词: {keywords}")
    logger.info(f"   调度间隔: {interval} 分钟")
    logger.info(f"   数据库: {db_path}")
    logger.info("=" * 60)

    # 创建搜索任务
    search_tasks = create_search_tasks(task_names)
    if not search_tasks:
        logger.error("❌ 没有可用的搜索任务，请检查 settings.yaml")
        sys.exit(1)

    # 创建数据处理层
    abs_db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), db_path
    )
    storage = JobStorage(abs_db_path)
    processor = DataProcessor(storage)

    # 创建通知渠道（自动根据 ENV 注册）
    notifiers = create_active_notifiers()

    # 创建调度器
    scheduler = JobScheduler(
        search_tasks=search_tasks,
        processor=processor,
        notifiers=notifiers,
        keywords=keywords,
        interval_minutes=interval,
    )

    # 执行
    if args.once:
        logger.info("📋 单次执行模式")
        scheduler.run_once()
    else:
        scheduler.start()


if __name__ == "__main__":
    main()
