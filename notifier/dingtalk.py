"""
钉钉通知渠道

通过钉钉自定义机器人 Webhook 发送 Markdown 消息。
支持可选的签名验证（加签模式）。

环境变量:
- DINGTALK_WEBHOOK_URL (必填)
- DINGTALK_SECRET (可选，加签验证密钥)
"""

import hashlib
import hmac
import base64
import logging
import os
import time
from urllib.parse import quote_plus

import requests

from notifier.base import BaseNotifier
from processor.models import JobItem

logger = logging.getLogger(__name__)


class DingTalkNotifier(BaseNotifier):
    """钉钉通知"""

    env_keys = ["DINGTALK_WEBHOOK_URL"]

    def __init__(self):
        self.webhook_url = os.environ["DINGTALK_WEBHOOK_URL"]
        self.secret = os.environ.get("DINGTALK_SECRET", "")

    @property
    def channel_name(self) -> str:
        return "钉钉"

    def _get_signed_url(self) -> str:
        """如果配置了加签密钥，则生成带签名的 URL"""
        if not self.secret:
            return self.webhook_url

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))

        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def notify(self, jobs: list[JobItem]) -> bool:
        """发送钉钉 Markdown 通知"""
        title = f"🔔 新职位通知 ({len(jobs)} 条)"
        text = self._build_markdown(jobs)

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            },
        }

        try:
            url = self._get_signed_url()
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"[钉钉] API 返回错误: {data}")
                return False
            return True
        except requests.RequestException as e:
            logger.error(f"[钉钉] 发送失败: {e}")
            return False

    def _build_markdown(self, jobs: list[JobItem]) -> str:
        """构建钉钉 Markdown 消息"""
        lines = [f"## 🔔 新职位通知\n"]

        for i, job in enumerate(jobs, 1):
            lines.append(f"### {i}. {job.title}")
            if job.company:
                lines.append(f"- 🏢 公司：{job.company}")
            if job.location:
                lines.append(f"- 📍 地点：{job.location}")
            if job.salary:
                lines.append(f"- 💰 薪资：{job.salary}")
            if job.keywords:
                lines.append(f"- 🏷️ 关键词：{', '.join(job.keywords)}")
            if job.url:
                lines.append(f"- 🔗 [查看详情]({job.url})")
            lines.append("")

        return "\n".join(lines)
