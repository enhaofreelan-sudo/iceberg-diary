#!/bin/bash

# 获取当前脚本所在的目录，并切换到该目录，确保相对路径执行正确
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/server"

echo "==========================================="
echo "   正在启动 冰山日记 后端服务..."
echo "   启动后将自动打开开发者中控台"
echo "==========================================="

# 后台启动 FastAPI 服务
python3 app.py &
SERVER_PID=$!

# 等待服务就绪后打开中控台
sleep 2
echo "   ✅ 服务已启动，正在打开中控台..."
open "http://127.0.0.1:8900/dashboard.html"

# 等待后端进程，保持终端窗口不关闭
wait $SERVER_PID
