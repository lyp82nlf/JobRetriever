#!/bin/bash

# 获取项目绝对路径
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.youfeng.jobretriever.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "配置 JobRetriever 开机自启..."

# 确保启动脚本有可执行权限
chmod +x "$PROJECT_DIR/start.sh"

# 生成 plist 文件
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youfeng.jobretriever</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/start.sh</string>
    </array>

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

echo "✅ 生成 LaunchAgent 配置文件: $PLIST_PATH"

# 如果之前已经加载过，先卸载
launchctl unload "$PLIST_PATH" 2>/dev/null

# 加载并启动服务
launchctl load -w "$PLIST_PATH"

echo "🎉 部署完成！"
echo "JobRetriever 现在已经在后台运行，并在每次 Mac 开机/登录后自动启动。"
echo "可以使用以下命令查看运行日志："
echo "tail -f $PROJECT_DIR/data/run.log"
