# 🍅 番茄钟 — 跨平台桌面计时器

Windows / macOS / Linux 全平台 Python 原生应用，专注高效的番茄工作法计时。附带 Android 版（Kivy）。

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Platform](https://img.shields.io/badge/Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 功能

- 番茄钟 / 短休息 / 长休息三种模式自动切换
- **计时中任意拖动窗口或切换全屏，不会打断计时**
- 三种内置提示音（柔和三连音 / 电子滴音 / 低频嗡鸣），支持自定义 WAV
- 系统托盘常驻（最小化到托盘）
- 完成时系统通知（Window Toast / macOS 通知中心 / Linux notify-send）
- 专注记录与统计分析（日志、专注时长分布、累计统计）
- 每轮记录附带 Markdown 任务笔记，支持标题、加粗、斜体、行内代码
- 桌面快捷方式（Windows 自动检测安装路径）

---

## 快速开始

### Windows

#### 方式一：直接运行源码（推荐）
```powershell
# 1. 确保已装 Python 3.8+（python.org 下载）
python --version

# 2. 进入项目目录
cd pomodoro-desktop-main

# 3. 安装可选依赖（系统托盘 + 通知）
python -m pip install pystray pillow plyer

# 4. 启动
pythonw main.py
```
或直接双击 `启动番茄钟.bat`。

#### 方式二：打包为独立 EXE
```powershell
.\build_exe.bat
```
输出：`dist\番茄钟.exe`（双击即用，无需 Python）。

### macOS

#### 方式一：源码运行
```bash
cd pomodoro-desktop-main
python3 -m pip install pystray pillow plyer
python3 main.py
```
或双击 `启动番茄钟_macOS.command`。

#### 方式二：打包为独立 .app
```bash
chmod +x build_mac.sh
./build_mac.sh
```
输出：`dist/番茄钟.app`（拖到 `/Applications` 即安装）。

### Android

在手机上安装 Termux，然后：
```bash
pkg update && pkg install python sdl2 sdl2-image sdl2-ttf sdl2-mixer -y
pip install kivy plyer
cd android
python main.py
```
详见 `android/手机运行步骤.md`。

---

## 快捷键

| 键 | 功能 |
|---|---|
| `空格` | 开始 / 暂停 |
| `r` | 重置 |
| `s` | 跳过当前阶段 |
| `h` | 历史记录 |
| `1` / `2` / `3` | 专注 / 短休息 / 长休息 |

---

## 目录结构

```
pomodoro-desktop-main/
├── main.py                 # 桌面版主程序（跨平台）
├── requirements.txt        # Python 依赖
├── 番茄钟.spec             # PyInstaller 打包配置
├── 番茄钟图标.ico          # Windows 图标
├── 番茄钟图标.png          # 图标源文件
├── build_exe.bat           # Windows 一键打包脚本
├── build_mac.sh            # macOS 一键打包脚本
├── 启动番茄钟.bat           # Windows 一键启动
├── 启动番茄钟_macOS.command # macOS 一键启动
├── macOS使用指南.md         # Mac 详细说明
│
├── android/                # Android 版（Kivy）
│   ├── main.py             # Kivy GUI
│   ├── timer_core.py       # 计时引擎（纯逻辑）
│   ├── buildozer.spec      # APK 打包配置
│   └── 手机运行步骤.md      # Termux 教程
│
├── build/                  # PyInstaller 中间文件（gitignore）
└── dist/                   # 打包输出（gitignore）
```

---

## 数据存储

所有配置和记录存在 `~/.pomodoro-timer/`：

- `config.json` — 用户设置
- `sessions.json` — 专注记录
- `session_logs.json` — 详细日志
- `sounds/` — 自定义音效（.wav）

跨平台共享：同一目录结构，Windows/Mac 可直接互通数据。

---

## 常见问题

### 系统托盘不显示
确认已安装可选依赖：`pip install pystray pillow`

### macOS 提示"无法验证开发者"
右键点击应用 → 打开 → 仍要打开（首次只需一次）

### 自定义音效没声音
确认是 `.wav` 格式，放在 `~/.pomodoro-timer/sounds/` 目录，然后在设置里选 `➕ 自定义文件…`。
