#!/bin/bash

# 获取脚本所在的实际目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 进入项目目录
cd "$DIR"

# 确保 data 目录存在，用于存放日志
mkdir -p "$DIR/data"

# 使用虚拟环境的 Python 执行 main.py
echo "Starting JobRetriever at $(date)" >> "$DIR/data/run.log"
"$DIR/.venv/bin/python" "$DIR/main.py" >> "$DIR/data/run.log" 2>&1
