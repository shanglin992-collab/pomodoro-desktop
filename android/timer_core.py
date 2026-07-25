#!/usr/bin/env python3
"""
番茄钟核心逻辑（与 Windows 桌面版保持一致的纯逻辑模块，无 GUI 依赖）
PomodoroTimer —— pure state machine, reused by the Kivy Android app.

回调接口（由 UI 层注入）：
    on_tick(remaining, total)        每秒多次触发，用于刷新显示
    on_complete(mode)                某一阶段自然结束
    on_session(count)                完成一个专注，刷新今日计数
    on_state()                       状态变化（start/pause/reset/mode 切换等）
"""

import json
from datetime import date
from pathlib import Path


class PomodoroTimer:
    # 模式对应的中文标签
    LABELS = {
        "pomodoro": "专注",
        "short_break": "短休",
        "long_break": "长休",
    }

    def __init__(self, app_dir=None):
        # ── 默认设置（与桌面版一致）──
        self.durations = {"pomodoro": 25 * 60, "short_break": 5 * 60, "long_break": 15 * 60}
        self.long_interval = 4
        self.auto_break = True
        self.auto_pom = False

        # ── 运行状态 ──
        self.mode = "pomodoro"
        self.remaining = self.durations["pomodoro"]
        self.total = self.durations["pomodoro"]
        self.running = False
        self.paused = False
        self.sessions_today = 0
        self.streak = 0

        # ── 持久化目录 ──
        self.app_dir = Path(app_dir) if app_dir else (Path.home() / ".pomodoro-timer")
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.app_dir / "config.json"
        self.sessions_file = self.app_dir / "sessions.json"

        # 回调占位
        self.on_tick = None
        self.on_complete = None
        self.on_session = None
        self.on_state = None

        self._load_config()
        self._load_sessions()
        self._reset_current()

    # ════════════════════════════════════════════════════
    #  持久化
    # ════════════════════════════════════════════════════
    def _load_config(self):
        try:
            if self.config_file.exists():
                d = json.loads(self.config_file.read_text(encoding="utf-8"))
                if "durations" in d:
                    self.durations.update(d["durations"])
                self.long_interval = d.get("long_interval", 4)
                self.auto_break = d.get("auto_break", True)
                self.auto_pom = d.get("auto_pom", False)
        except Exception:
            pass

    def _save_config(self):
        try:
            self.config_file.write_text(
                json.dumps(
                    {
                        "durations": self.durations,
                        "long_interval": self.long_interval,
                        "auto_break": self.auto_break,
                        "auto_pom": self.auto_pom,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load_sessions(self):
        today = date.today().isoformat()
        try:
            if self.sessions_file.exists():
                data = json.loads(self.sessions_file.read_text(encoding="utf-8"))
                self.sessions_today = data.get(today, 0)
        except Exception:
            self.sessions_today = 0

    def _save_sessions(self):
        today = date.today().isoformat()
        try:
            data = {}
            if self.sessions_file.exists():
                data = json.loads(self.sessions_file.read_text(encoding="utf-8"))
            data[today] = self.sessions_today
            self.sessions_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    # ════════════════════════════════════════════════════
    #  逻辑
    # ════════════════════════════════════════════════════
    def _reset_current(self):
        self.total = self.durations[self.mode]
        self.remaining = self.total

    def set_settings(self, durations=None, long_interval=None, auto_break=None, auto_pom=None):
        if durations:
            self.durations.update(durations)
        if long_interval is not None:
            self.long_interval = long_interval
        if auto_break is not None:
            self.auto_break = auto_break
        if auto_pom is not None:
            self.auto_pom = auto_pom
        self._save_config()
        if not self.running and not self.paused:
            self._reset_current()

    def start(self):
        if self.remaining <= 0.1:
            self._reset_current()
        self.running = True
        self.paused = False
        if self.on_state:
            self.on_state()

    def pause(self):
        self.paused = True
        self.running = True
        if self.on_state:
            self.on_state()

    def resume(self):
        self.paused = False
        if self.on_state:
            self.on_state()

    def reset(self):
        self.running = False
        self.paused = False
        self._reset_current()
        if self.on_state:
            self.on_state()

    def toggle(self):
        if not self.running:
            self.start()
        elif self.paused:
            self.resume()
        else:
            self.pause()

    def skip(self):
        self.running = False
        self.paused = False
        self._advance(completed=False)
        if self.on_state:
            self.on_state()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.running = False
        self.paused = False
        if mode == "long_break":
            self.streak = 0
        self.mode = mode
        self._reset_current()
        if self.on_state:
            self.on_state()

    def _advance(self, completed=True):
        """阶段结束后的模式切换（与桌面版一致）。"""
        if self.mode == "pomodoro":
            self.sessions_today += 1
            self.streak += 1
            self._save_sessions()
            if self.on_session:
                self.on_session(self.sessions_today)
            if self.streak >= self.long_interval:
                self.mode = "long_break"
                self.streak = 0
            else:
                self.mode = "short_break"
        else:
            self.mode = "pomodoro"
        self._reset_current()

    def tick(self, dt):
        """由 UI 的时钟按固定步长调用。dt 为秒。"""
        if not self.running or self.paused:
            return
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
            self.running = False
            self.paused = False
            if self.on_complete:
                self.on_complete(self.mode)
            self._advance(completed=True)
            # 自动进入下一阶段（与桌面版 auto_break / auto_pom 行为一致）
            if self.mode != "pomodoro" and self.auto_break:
                self.start()
            elif self.mode == "pomodoro" and self.auto_pom:
                self.start()
            if self.on_state:
                self.on_state()
            return
        if self.on_tick:
            self.on_tick(self.remaining, self.total)

    # 便捷只读属性
    @property
    def label(self):
        return self.LABELS[self.mode]

    def time_str(self):
        m, s = divmod(int(self.remaining), 60)
        return f"{m:02d}:{s:02d}"
