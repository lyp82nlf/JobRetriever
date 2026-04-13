# JobRetriever

职位抓取与通知系统 — 自动搜索多个招聘网站的最新职位，通过多种渠道推送通知。

## 架构

```
搜索层 (Search)  →  数据处理层 (Processor)  →  消息处理层 (Notifier)
   ↑                                              
调度层 (Scheduler)
```

- **搜索层**：每个搜索任务独立实现，互不干扰，输出统一 `JobItem`，负责判断 `is_remote`
- **数据处理层**：筛选 → 去重 → 新增检测 → SQLite 持久化
- **消息处理层**：通过 ENV 驱动自动注册，支持企业微信/飞书/钉钉/Telegram
- **调度层**：APScheduler 定时调度

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置（编辑 .env，所有配置集中在这里）
cp .env.example .env
vim .env

# 立即执行一次（测试）
python main.py --once

# 启动定时调度
python main.py
```

## macOS 后台守护部署

如果你打算在一台 Mac （或 Mac 服务器）上全天候运行本服务，项目内置了一键配置开机自启的脚本。它会使用原生 `launchd` 让抓取任务真后台运行：

```bash
# 赋予执行权限并部署
chmod +x start.sh install_mac_service.sh
./install_mac_service.sh

# 查看抓取日志
tail -f data/run.log
```

## 配置说明（全在 .env 中）

### 搜索配置

| 配置 | 环境变量 | 示例 |
|------|----------|------|
| 搜索关键词 | `JOB_SEARCH_KEYWORDS` | `android,kotlin,flutter` |
| 调度间隔 | `JOB_SCHEDULE_INTERVAL` | `30`（分钟） |

### 代理配置

| 配置 | 环境变量 | 示例 |
|------|----------|------|
| HTTP 代理 | `HTTP_PROXY` | `http://127.0.0.1:7890` |
| HTTPS 代理 | `HTTPS_PROXY` | `http://127.0.0.1:7890` |
| SOCKS5 代理 | `SOCKS_PROXY` | `socks5://127.0.0.1:7891`（优先级最高） |

### 通知渠道（填了即启用）

| 渠道 | 环境变量 |
|------|----------|
| 企业微信 | `WECOM_WEBHOOK_URL` |
| 飞书 | `FEISHU_WEBHOOK_URL` |
| 钉钉 | `DINGTALK_WEBHOOK_URL` + `DINGTALK_SECRET`（可选） |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |

### 职位筛选（不填则不筛选）

| 功能 | 环境变量 | 示例 |
|------|----------|------|
| 地区筛选 | `JOB_FILTER_LOCATIONS` | `北京,上海,深圳` |
| 仅远程 | `JOB_FILTER_REMOTE` | `true`（默认 `false`） |
| 排除关键词 | `JOB_FILTER_EXCLUDE_WORDS` | `实习,兼职` |
| 包含关键词 | `JOB_FILTER_INCLUDE_WORDS` | `senior,高级` |
| 最低薪资 | `JOB_FILTER_MIN_SALARY` | `15`（单位 K） |
| 排除公司 | `JOB_FILTER_COMPANIES_EXCLUDE` | `某公司A,某公司B` |

## 扩展

**新增搜索源**：继承 `search.base.BaseSearchTask`，在 `main.py` 的 `SEARCH_TASK_REGISTRY` 中注册。

**新增通知渠道**：继承 `notifier.base.BaseNotifier`，声明 `env_keys`，在 `notifier/__init__.py` 中导入即可。
