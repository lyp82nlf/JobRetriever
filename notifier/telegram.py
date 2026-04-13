"""
Telegram 通知渠道

通过 Telegram Bot API 发送 HTML 格式的职位通知。
环境变量:
- TELEGRAM_BOT_TOKEN (必填)
- TELEGRAM_CHAT_ID (必填)
"""

import logging
import os

import requests

from notifier.base import BaseNotifier
from processor.models import JobItem

logger = logging.getLogger(__name__)

# Telegram 单条消息最大字符数
MAX_MESSAGE_LENGTH = 4096


class TelegramNotifier(BaseNotifier):
    """Telegram 通知"""

    env_keys = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]

    def __init__(self):
        self.bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = os.environ["TELEGRAM_CHAT_ID"]
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    @property
    def channel_name(self) -> str:
        return "Telegram"

    def notify(self, jobs: list[JobItem]) -> bool:
        """发送 Telegram HTML 通知"""
        messages = self._build_messages(jobs)
        success = True

        for msg in messages:
            try:
                resp = requests.post(
                    f"{self.api_base}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data.get("ok"):
                    logger.error(f"[Telegram] API 返回错误: {data}")
                    success = False
            except requests.RequestException as e:
                logger.error(f"[Telegram] 发送失败: {e}")
                success = False

        return success

    def _build_messages(self, jobs: list[JobItem]) -> list[str]:
        """构建消息列表，自动分批处理超长内容"""
        header = "🔔 <b>新职位通知</b>\n\n"
        messages = []
        current = header

        for i, job in enumerate(jobs):
            entry = self._format_job_entry(job, i + 1)

            if len(current + entry) > MAX_MESSAGE_LENGTH:
                if current != header:
                    messages.append(current)
                current = header + entry
            else:
                current += entry

        if current != header:
            messages.append(current)

        return messages

    def _format_job_entry(self, job: JobItem, index: int) -> str:
        """格式化单条职位为 Telegram HTML"""
        lines = [f"<b>{index}. {self._escape_html(job.title)}</b>"]
        if job.company:
            lines.append(f"🏢 {self._escape_html(job.company)}")
        if job.location:
            lines.append(f"📍 {self._escape_html(job.location)}")
        if job.source:
            lines.append(f"🌐 来源：{self._escape_html(job.source)}")
        if job.salary:
            lines.append(f"💰 {self._escape_html(job.salary)}")
        if job.keywords:
            lines.append(f"🏷️ {self._escape_html(', '.join(job.keywords))}")
        if job.url:
            lines.append(f'🔗 <a href="{job.url}">查看详情</a>')
        lines.append("")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _escape_html(text: str) -> str:
        """转义 HTML 特殊字符"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
