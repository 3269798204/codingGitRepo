#!/bin/bash
# 启动任务详情服务

echo "============================================================"
echo "🚀 启动任务详情HTML服务"
echo "============================================================"

# 检查依赖
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 安装依赖（如果需要）
echo "📦 检查依赖..."
pip3 install fastapi uvicorn 2>/dev/null || true

# 启动服务
echo ""
echo "📍 服务地址: http://localhost:8001"
echo "📄 任务详情: http://localhost:8001/task/<task_id>"
echo "💚 健康检查: http://localhost:8001/health"
echo ""
echo "============================================================"
echo "按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

python3 task_detail_api.py
