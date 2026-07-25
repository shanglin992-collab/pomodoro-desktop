#!/bin/bash
# 🍅 番茄钟 — macOS .app 打包脚本
# 用法：在 Mac 终端里 cd 到本项目目录，跑 ./build_mac.sh
# 输出：dist/番茄钟.app（拖到 /Applications 即安装）

set -e

APP_NAME="番茄钟"
BUNDLE_ID="com.pomodoro.timer"
ICON_PNG="番茄钟图标.png"
ICON_ICNS="番茄钟图标.icns"
MAIN_PY="main.py"

echo "============================================"
echo "   🍅 番茄钟 macOS .app 打包"
echo "============================================"

# ── 1. 检查环境 ──
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# ── 2. 安装/升级依赖 ──
echo ""
echo "📦 安装 Python 依赖…"
python3 -m pip install --quiet --upgrade pip 2>/dev/null || true
python3 -m pip install --quiet pyinstaller pystray pillow plyer
echo "✅ PyInstaller $(pyinstaller --version)"

# ── 3. 把 PNG 图标转成 macOS .icns ──
echo ""
if [ -f "$ICON_PNG" ]; then
    echo "🎨 生成 macOS 图标 $ICON_ICNS …"
    ICONSET="番茄钟.iconset"
    rm -rf "$ICONSET"

    # 创建临时 iconset 目录
    mkdir "$ICONSET"

    # 用 sips 生成各尺寸副本（macOS 内置工具，无需安装任何东西）
    declare -A SIZES=(
        ["icon_16x16.png"]=16
        ["icon_16x16@2x.png"]=32
        ["icon_32x32.png"]=32
        ["icon_32x32@2x.png"]=64
        ["icon_128x128.png"]=128
        ["icon_128x128@2x.png"]=256
        ["icon_256x256.png"]=256
        ["icon_256x256@2x.png"]=512
        ["icon_512x512.png"]=512
        ["icon_512x512@2x.png"]=1024
    )

    for name in "${!SIZES[@]}"; do
        size=${SIZES[$name]}
        sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET/$name" &>/dev/null
    done

    # 编译 iconset → .icns
    iconutil -c icns "$ICONSET" -o "$ICON_ICNS" 2>/dev/null || {
        # 如果 iconutil 失败（极少情况），直接用 png
        echo "⚠️  iconutil 失败，将跳过自定义图标"
        rm -rf "$ICONSET" "$ICON_ICNS"
        ICON_ICNS=""
    }

    rm -rf "$ICONSET"
    if [ -f "$ICON_ICNS" ]; then
        echo "✅ 图标已生成：$ICON_ICNS"
    fi
else
    echo "⚠️  未找到 $ICON_PNG，将不带自定义图标打包"
    ICON_ICNS=""
fi

# ── 4. PyInstaller 打包 ──
echo ""
echo "🔨 开始打包（约 1-2 分钟）…"

PYINSTALLER_ARGS=(
    --windowed                # macOS 应用（无终端窗口）
    --name "$APP_NAME"
    --osx-bundle-identifier "$BUNDLE_ID"
    --clean
    --noconfirm
)

# 有 icns 就加图标
if [ -n "$ICON_ICNS" ] && [ -f "$ICON_ICNS" ]; then
    PYINSTALLER_ARGS+=(--icon "$ICON_ICNS")
fi

# 主入口
PYINSTALLER_ARGS+=("$MAIN_PY")

pyinstaller "${PYINSTALLER_ARGS[@]}"

# ── 5. 完成 ──
APP_PATH="dist/${APP_NAME}.app"
echo ""
echo "============================================"
if [ -d "$APP_PATH" ]; then
    echo "   ✅ 打包成功！"
    echo ""
    echo "   📍 位置：$(pwd)/$APP_PATH"
    echo ""
    echo "   🚀 下一步："
    echo "      1. 双击 dist/${APP_NAME}.app 即可运行"
    echo "      2. 拖到 /Applications 永久安装"
    echo "      3. 首次开启时若遇到「无法验证开发者」："
    echo "         右键 → 打开 → 仍要打开"
    echo ""
    du -sh "$APP_PATH"
else
    echo "   ❌ 打包失败，请查看上方错误信息"
fi
echo "============================================"
