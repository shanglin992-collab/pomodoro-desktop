# 🍅 番茄钟 — macOS 使用指南

## 快速开始（3 步）

### 1. 把整个 `pomodoro-desktop-main` 文件夹拷贝到 Mac 上
用 U 盘、AirDrop、微信文件传输 或 iCloud 均可。

### 2. 安装 Python 3（如已装可跳过）
打开 **终端**（Terminal），输入：
```bash
python3 --version
```
如果显示 `Python 3.x.x` → 已装好，跳到第 3 步。
如果没有 → 去 https://www.python.org/downloads/ 下载安装。

### 3. 启动（二选一）

**方式 A：双击 `启动番茄钟_macOS.command`**  
（首次若提示"无法验证开发者"→ 右键 → 打开 → 仍要打开）

**方式 B：终端运行**  
```bash
cd ~/Desktop/pomodoro-desktop-main
python3 main.py
```

---

## 打包成 .app（一键安装版）

如果不想每次依赖终端 / Python，可以打一个独立的 `.app` 文件（像普通 Mac 应用一样，双击就用）：

```bash
cd ~/Desktop/pomodoro-desktop-main
chmod +x build_mac.sh
./build_mac.sh
```

等待 1-2 分钟，输出在 `dist/番茄钟.app`，拖到 `/Applications` 即可永久安装。

---

## 首次运行说明

- 首次启动会自动安装可选依赖（pystray / pillow / plyer），约需 10-30 秒。之后启动就是秒开。
- **系统托盘**：关闭窗口 → 自动缩到菜单栏图标（通过 pystray），双击图标恢复。
- **通知**：计时结束会在 macOS 通知中心弹出提醒（需要系统通知权限，首次会提示授权）。
- **音效**：使用 macOS 原生的 `afplay` 播放，支持 WAV 自定义音效（与 Windows 版共享音效目录 `~/.pomodoro-timer/sounds/`）。
- **数据共享**：配置和专注记录存储在 `~/.pomodoro-timer/`，与 Windows 版同一目录结构——跨平台共享同一份数据。

---

## 快捷键

| 键 | 功能 |
|---|---|
| `空格` | 开始 / 暂停 |
| `r` | 重置 |
| `s` | 跳过当前阶段 |
| `h` | 查看历史记录 |
| `1` / `2` / `3` | 切换专注 / 短休息 / 长休息 |

---

## 与 Windows 版的区别

所有功能完全一致。底层差异（对你透明）：
- 音频：macOS 用 `afplay`，Windows 用 `winsound`
- 通知：macOS 用原生通知中心，Windows 用 Toast 推送
- 字体：macOS 用苹方/Helvetica，Windows 用微软雅黑/Consolas
- 窗口置顶抢焦点：macOS 用 tkinter 内置方法（无 ctypes 依赖）

---

## 常见问题

### Q: 双击 .app 提示「无法验证开发者」
右键点击 `番茄钟.app` → **打开** → 点击「仍要打开」（只需一次，之后正常双击即可）。

### Q: .app 没有图标
重新跑 `./build_mac.sh`，确保 `番茄钟图标.png` 在项目根目录下。

### Q: 系统托盘不显示 / 菜单栏没图标
检查 Python 是否已装 pystray + pillow：
```bash
python3 -m pip install pystray pillow
```

### Q: 通知没有弹出
进入 **系统设置 → 通知**，找到「番茄钟」（或 Python / terminal），开启「允许通知」。
