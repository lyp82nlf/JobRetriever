"""
飞书通知渠道

通过飞书自定义机器人 Webhook 发送富文本消息。
环境变量: FEISHU_WEBHOOK_URL
"""

import logging
import os

import requests

from notifier.base import BaseNotifier
from processor.models import JobItem

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """飞书通知"""

    env_keys = ["FEISHU_WEBHOOK_URL"]

    def __init__(self):
        self.webhook_url = os.environ["FEISHU_WEBHOOK_URL"]

    @property
    def channel_name(self) -> str:
        return "飞书"

    def notify(self, jobs: list[JobItem]) -> bool:
        """发送飞书富文本卡片通知"""
        content = self._build_content(jobs)
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"🔔 新职位通知 ({len(jobs)} 条)",
                    },
                    "template": "blue",
                },
                "elements": content,
            },
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0 and data.get("StatusCode") != 0:
                # 飞书返回 code=0 或 StatusCode=0 表示成功
                if data.get("msg") != "success" and data.get("StatusMessage") != "success":
                    logger.error(f"[飞书] API 返回错误: {data}")
                    return False
            return True
        except requests.RequestException as e:
            logger.error(f"[飞书] 发送失败: {e}")
            return False

    def _build_content(self, jobs: list[JobItem]) -> list[dict]:
        """构建飞书卡片内容元素"""
        elements = []

        for i, job in enumerate(jobs):
            # 分隔线（非第一条）
            if i > 0:
                elements.append({"tag": "hr"})

            # 职位信息
            fields = []
            fields.append({
                "is_short": False,
                "text": {
                    "tag": "lark_md",
                    "content": f"**📌 {job.title}**",
                },
            })

            if job.company:
                fields.append({
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"🏢 {job.company}"},
                })

            if job.location:
                fields.append({
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"📍 {job.location}"},
                })

            if job.salary:
                fields.append({
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"💰 {job.salary}"},
                })

            if job.keywords:
                fields.append({
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"🏷️ {', '.join(job.keywords)}"},
                })

            elements.append({"tag": "div", "fields": fields})

            # 链接按钮
            if job.url:
                elements.append({
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "url": job.url,
                            "type": "primary",
                        }
                    ],
                })

        return elements
