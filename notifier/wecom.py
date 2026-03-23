"""
企业微信通知渠道

通过企业微信群机器人 Webhook 发送 Markdown 格式的职位通知。
环境变量: WECOM_WEBHOOK_URL
"""

import logging
import os

import requests

from notifier.base import BaseNotifier
from processor.models import JobItem

logger = logging.getLogger(__name__)

# 企业微信单条消息最大字节数
MAX_CONTENT_BYTES = 4096


class WeComNotifier(BaseNotifier):
    """企业微信通知"""

    env_keys = ["WECOM_WEBHOOK_URL"]

    def __init__(self):
        self.webhook_url = os.environ["WECOM_WEBHOOK_URL"]

    @property
    def channel_name(self) -> str:
        return "企业微信"

    def notify(self, jobs: list[JobItem]) -> bool:
        """发送企业微信 Markdown 通知"""
        messages = self._build_messages(jobs)
        success = True

        for msg in messages:
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": msg},
            }
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("errcode") != 0:
                    logger.error(f"[企业微信] API 返回错误: {data}")
                    success = False
            except requests.RequestException as e:
                logger.error(f"[企业微信] 发送失败: {e}")
                success = False

        return success

    def _build_messages(self, jobs: list[JobItem]) -> list[str]:
        """构建消息列表，自动分批处理超长内容"""
        header = "## 🔔 新职位通知\n\n"
        messages = []
        current = header

        for i, job in enumerate(jobs):
            entry = self._format_job_entry(job, i + 1)

            # 检查是否超过限制
            if len((current + entry).encode("utf-8")) > MAX_CONTENT_BYTES:
                if current != header:
                    messages.append(current)
                current = header + entry
            else:
                current += entry

        if current != header:
            messages.append(current)

        return messages

    def _format_job_entry(self, job: JobItem, index: int) -> str:
        """格式化单条职位为企业微信 Markdown"""
        lines = [f"### {index}. {job.title}"]
        if job.company:
            lines.append(f"> 🏢 公司：{job.company}")
        if job.location:
            lines.append(f"> 📍 地点：{job.location}")
        if job.salary:
            lines.append(f"> 💰 薪资：{job.salary}")
        if job.keywords:
            lines.append(f"> 🏷️ 关键词：{', '.join(job.keywords)}")
        lines.append(f"> 🔗 [查看详情]({job.url})")
        lines.append("")
        return "\n".join(lines) + "\n"
