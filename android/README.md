# 🍅 番茄钟 · Android 版

把 Windows 桌面版番茄钟移植到安卓，**原生运行**（有自己的图标，可全屏，可装成 App）。
逻辑与桌面版完全一致：专注 25 / 短休 5 / 长休 15，每 4 个番茄进入长休，支持自动开始休息、今日会话计数、任务备注、完成通知与震动。

工程结构：

```
android/
├── main.py            # Kivy 界面（复刻桌面版 UI）
├── timer_core.py      # 纯逻辑状态机（与桌面版等价，无 GUI 依赖）
├── buildozer.spec     # 打包成 APK 的配置
├── requirements.txt   # 依赖：kivy + plyer
├── assets/icon.png    # 应用图标（512×512）
└── README.md          # 本文件
```

---

## 方式一：Termux 直接在手机上运行（最快，今天就能用）

> 优点：不用编译，手机上跑的就是这份 Python 代码，体验是原生全屏窗口。
> 缺点：入口是 Termux 命令行（可加 Termux:Widget 钉到桌面当快捷方式）。

1. 在手机上安装 **Termux**（F-Droid 版最佳，Google Play 版较旧）。
2. 打开 Termux，装 Python 与依赖：
   ```bash
   pkg update && pkg install python
   pip install kivy plyer
   ```
   > 若 Kivy 安装慢/报错，可改用 `pip install kivy` 的预编译 wheel；部分机型需先 `pkg install clang libffi`。
3. 把 `android/` 整个文件夹传到手机（可用 `termux-setup-storage` 后通过手机存储复制，或用 `git` / `scp`）。
4. 进入目录运行：
   ```bash
   cd android
   python main.py
   ```
   即可看到全屏番茄钟，开始/暂停、跳过、重置、设置都可用；完成时会震动 + 系统通知。

**钉到桌面（更像 App）：** 安装 Termux:Widget，按它的格式在 `~/.shortcuts/` 放一个执行 `python /路径/android/main.py` 的脚本，即可在桌面长按添加快捷方式。

---

## 方式二：Buildozer 打包成正式 APK（推荐长期使用）

> 优点：生成 `.apk`，可安装、可分享、有独立图标，真正的原生 App。
> 前提：**需要一台 Linux 机器**（或 WSL2 / 云服务器），并安装 Android SDK/NDK——本机 Windows 沙箱无法在此完成编译。

1. 在 Linux 环境准备工具链：
   ```bash
   sudo apt update
   sudo apt install -y python3-pip git zip unzip openjdk-17-jdk
   pip install buildozer
   # Buildozer 首次打包会自动下载 Android SDK/NDK（需联网，耗时较久）
   ```
2. 把 `android/` 目录拷到该 Linux 机器。
3. 在该目录执行（自动生成 `bin/番茄钟-1.0-arm64-v8a-debug.apk`）：
   ```bash
   buildozer android debug
   ```
4. 把生成的 `bin/*.apk` 传到手机，允许“未知来源”安装即可。

可选：生成正式发布包（需自己的签名密钥）：
```bash
buildozer android release
```

---

## 与原桌面版的对应

| 桌面版 | 安卓版 |
|---|---|
| tkinter 窗口 + pystray 托盘 | Kivy 全屏窗口（无系统托盘，手机也不需要） |
| winsound 提示音 | 震动 + 系统通知（plyer） |
| Windows Toast 通知 | plyer 通知 |
| 设置弹窗 | Kivy ModalView 设置弹窗 |
| 计时逻辑 / 模式切换 / 会话计数 | 完全复用 `timer_core.py` |

设置（时长、间隔、自动开关）会写入 `~/.pomodoro-timer/config.json`，与桌面版共用同一份配置目录结构。
