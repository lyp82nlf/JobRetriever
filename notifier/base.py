"""
通知渠道抽象基类 + 自动注册工厂

每个通知渠道只需要：
1. 继承 BaseNotifier
2. 声明 env_keys（依赖的环境变量名）
3. 实现 notify() 和 channel_name

系统启动时自动扫描所有子类，
对已配置 ENV 的渠道进行实例化。
"""

import logging
import os
from abc import ABC, abstractmethod

from processor.models import JobItem

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """通知渠道抽象基类"""

    # 子类必须声明依赖的环境变量名列表
    # 例如: env_keys = ["WECOM_WEBHOOK_URL"]
    env_keys: list[str] = []

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """通知渠道名称，如 "企业微信", "飞书" """
        pass

    @abstractmethod
    def notify(self, jobs: list[JobItem]) -> bool:
        """
        发送职位通知。

        Args:
            jobs: 新增的职位列表

        Returns:
            是否发送成功
        """
        pass

    @classmethod
    def is_configured(cls) -> bool:
        """检查该渠道所有必需的环境变量是否已设置"""
        return all(os.environ.get(k) for k in cls.env_keys)

    def safe_notify(self, jobs: list[JobItem]) -> bool:
        """
        安全发送通知，捕获所有异常。

        Args:
            jobs: 新增的职位列表

        Returns:
            是否发送成功
        """
        if not jobs:
            return True

        try:
            logger.info(f"[{self.channel_name}] 开始发送 {len(jobs)} 条职位通知")
            result = self.notify(jobs)
            if result:
                logger.info(f"[{self.channel_name}] 通知发送成功")
            else:
                logger.warning(f"[{self.channel_name}] 通知发送失败")
            return result
        except Exception as e:
            logger.error(f"[{self.channel_name}] 通知发送异常: {e}", exc_info=True)
            return False

    def _format_job_text(self, job: JobItem) -> str:
        """格式化单条职位信息为文本（子类可覆盖）"""
        parts = [f"📌 {job.title}"]
        if job.company:
            parts.append(f"🏢 {job.company}")
        if job.location:
            parts.append(f"📍 {job.location}")
        if job.salary:
            parts.append(f"💰 {job.salary}")
        if job.url:
            parts.append(f"🔗 {job.url}")
        return "\n".join(parts)


def create_active_notifiers() -> list[BaseNotifier]:
    """
    扫描所有 BaseNotifier 子类，自动实例化已配置的通知渠道。

    Returns:
        已配置的通知渠道实例列表
    """
    active = []

    for cls in BaseNotifier.__subclasses__():
        if cls.is_configured():
            try:
                notifier = cls()
                active.append(notifier)
                logger.info(f"✅ 通知渠道已启用: {notifier.channel_name}")
            except Exception as e:
                logger.error(f"❌ 通知渠道初始化失败 [{cls.__name__}]: {e}")
        else:
            missing = [k for k in cls.env_keys if not os.environ.get(k)]
            logger.debug(
                f"⏭️ 通知渠道未配置: {cls.__name__} "
                f"(缺少环境变量: {', '.join(missing)})"
            )

    if not active:
        logger.warning("⚠️ 没有任何通知渠道被启用，请检查 .env 配置")

    return active
