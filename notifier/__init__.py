"""
消息处理层 - 多渠道通知

通知渠道通过 ENV 环境变量自动注册：
填了对应的 Webhook/Token 即启用，未填则跳过。
"""

from notifier.base import BaseNotifier, create_active_notifiers

# 导入所有通知渠道实现，触发子类注册
from notifier import wecom  # noqa: F401
from notifier import feishu  # noqa: F401
from notifier import dingtalk  # noqa: F401
from notifier import telegram  # noqa: F401

__all__ = ["BaseNotifier", "create_active_notifiers"]
