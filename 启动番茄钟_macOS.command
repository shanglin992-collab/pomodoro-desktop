#!/bin/bash
# 🍅 番茄钟 — macOS 一键启动
# 双击此文件即可运行（首次可能需要右键 → 打开）

cd "$(dirname "$0")"

# 检查 Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ 未找到 Python。请先安装 Python 3：https://www.python.org/downloads/"
    read -p "按回车退出..."
    exit 1
fi

echo "✅ Python: $($PYTHON --version)"

# 安装可选依赖（系统托盘 + 通知）
echo "📦 安装依赖…"
$PYTHON -m pip install --quiet pystray pillow plyer 2>/dev/null

# 运行
echo "🚀 启动番茄钟…"
$PYTHON main.py
