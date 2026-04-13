#!/bin/bash

set -e

# 获取项目绝对路径
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_USER="${SUDO_USER:-$(whoami)}"
PLIST_NAME="com.youfeng.jobretriever.daemon.plist"
PLIST_PATH="/Library/LaunchDaemons/$PLIST_NAME"

if [ "$EUID" -ne 0 ]; then
  echo "请使用 sudo 运行此脚本，例如: sudo ./install_mac_daemon.sh"
  exit 1
fi

echo "配置 JobRetriever 开机守护运行（无需登录用户）..."
echo "服务运行用户: $SERVICE_USER"

# 确保启动脚本和日志目录可用
chmod +x "$PROJECT_DIR/start.sh"
mkdir -p "$PROJECT_DIR/data"
chown -R "$SERVICE_USER":staff "$PROJECT_DIR/data"

# 生成 plist 文件
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youfeng.jobretriever.daemon</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/start.sh</string>
    </array>

    <key>UserName</key>
    <string>$SERVICE_USER</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/data/launchd.out.log</string>

    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/data/launchd.err.log</string>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
</dict>
</plist>
EOF

chmod 644 "$PLIST_PATH"
chown root:wheel "$PLIST_PATH"

# 如果之前已经加载过，先卸载
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# 加载并启动服务
launchctl load -w "$PLIST_PATH"

echo "✅ 生成 LaunchDaemon 配置文件: $PLIST_PATH"
echo "🎉 部署完成！"
echo "JobRetriever 现在会在系统开机后自动运行，即使没有登录图形界面用户。"
echo "可以使用以下命令查看运行日志："
echo "tail -f $PROJECT_DIR/data/run.log"
