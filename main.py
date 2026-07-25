#!/usr/bin/env python3
"""
🍅 番茄钟 — 跨平台桌面版 (Windows / macOS / Linux)
Pomodoro Timer — cross-platform desktop app
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import re
import sys
import subprocess
import platform
import tempfile
import wave
import struct
import math
import os as _os
from io import BytesIO
from datetime import date, datetime
from pathlib import Path

# ── Optional imports ──
HAS_PYSTRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except Exception:
    pass

# ── Platform helpers ──
_IS_MAC = platform.system() == "Darwin"
_IS_WIN = platform.system() == "Windows"

# ── Cross-platform audio ──
def _generate_tone_wav(freq: float, duration_ms: int, volume: float = 1.0) -> bytes:
    """Generate a sine-tone WAV in memory (no external deps)."""
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000.0)
    buf = bytearray()
    fade = max(1, n_samples // 10)
    for i in range(n_samples):
        t = i / sample_rate
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n_samples - fade:
            env = (n_samples - i) / fade
        value = int(32767 * volume * env * math.sin(2.0 * math.pi * freq * t))
        buf.extend(struct.pack("<h", max(-32768, min(32767, value))))
    wav_buf = BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(buf)
    return wav_buf.getvalue()


def _emit_tone(freq: float, duration_ms: int, volume: float = 1.0):
    """Play a sine tone: generate temp WAV → OS-native player."""
    wav_bytes = _generate_tone_wav(freq, duration_ms, volume)
    _play_wav_bytes(wav_bytes)


def _play_wav_bytes(wav_bytes: bytes):
    """Write WAV bytes to temp file, play with OS command, clean up."""
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        _os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(wav_bytes)
        _play_wav_file(tmp_path)
    except Exception:
        pass
    finally:
        if tmp_path:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass


def _play_wav_file(path: str):
    """Play a .wav file using the OS-native audio command."""
    try:
        if _IS_MAC:
            subprocess.run(["afplay", path], check=False, capture_output=True)
        elif _IS_WIN:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        else:  # Linux
            for cmd in (["paplay", path], ["aplay", "-q", path]):
                r = subprocess.run(cmd, check=False, capture_output=True)
                if r.returncode == 0:
                    break
    except Exception:
        pass


def _validate_wav_file(filepath):
    """Return True if filepath is a valid WAV file."""
    try:
        with wave.open(str(filepath), "rb") as wf:
            return wf.getnchannels() > 0
    except Exception:
        return False

# ── Config paths ──
APP_DIR = Path.home() / ".pomodoro-timer"
CONFIG_FILE = APP_DIR / "config.json"
SESSIONS_FILE = APP_DIR / "sessions.json"
LOGS_FILE = APP_DIR / "session_logs.json"
SOUNDS_DIR = APP_DIR / "sounds"
APP_DIR.mkdir(parents=True, exist_ok=True)
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

# ── Sound presets ──
# 内置音效预设：value -> 显示名
PRESET_LABELS = {
    "soft_triad": "柔和三连音",
    "beep_digital": "电子滴音",
    "low_hum": "低频嗡鸣",
}
CUSTOM_OPTION = "➕ 自定义文件…"
DEFAULT_PRESET = "soft_triad"


def _sound_options():
    """返回下拉框选项列表 [(显示名, value), ...]，含已上传的自定义 .wav。"""
    opts = [(PRESET_LABELS["soft_triad"], "soft_triad"),
            (PRESET_LABELS["beep_digital"], "beep_digital"),
            (PRESET_LABELS["low_hum"], "low_hum")]
    try:
        for wav in sorted(SOUNDS_DIR.glob("*.wav")):
            opts.append((wav.name, wav.name))
    except Exception:
        pass
    opts.append((CUSTOM_OPTION, "__custom__"))
    return opts


def _display_for_value(value):
    """根据存储的 value 找到下拉框应显示的文本。"""
    for d, v in _sound_options():
        if v == value:
            return d
    return PRESET_LABELS.get(DEFAULT_PRESET, "柔和三连音")

# ── Colors ──
C = {
    "bg": "#1e1e2e", "surface": "#313244", "surface2": "#45475a",
    "text": "#cdd6f4", "subtext": "#a6adc8", "muted": "#6c7086",
    "border": "#585b70", "red": "#f38ba8", "green": "#a6e3a1",
    "blue": "#89b4fa", "white": "#ffffff", "yellow": "#f9e2af",
}

# ── Fonts ──
_FONT_UI = "PingFang SC" if _IS_MAC else "Microsoft YaHei UI"
_FONT_MONO = "SF Mono" if _IS_MAC else "Consolas"
_FONT_SYMBOL = "Helvetica Neue" if _IS_MAC else "Segoe UI"
F_TITLE = (_FONT_UI, 11, "bold")
F_LABEL = (_FONT_UI, 9)
F_TIME  = (_FONT_MONO, 46, "bold")
F_SMALL = (_FONT_UI, 8)
F_TAB   = (_FONT_UI, 9, "bold")
F_BODY  = (_FONT_UI, 10)


# ═══════════════════════════════════════════════════════════
#  MARKDOWN → tk.Text 渲染（支持标题/粗体/斜体/行内代码/列表）
# ═══════════════════════════════════════════════════════════

def _md_config_tags(tw):
    tw.tag_configure("h1", font=(_FONT_UI, 15, "bold"),
                     foreground=C["red"], spacing1=4, spacing3=6)
    tw.tag_configure("h2", font=(_FONT_UI, 13, "bold"),
                     foreground=C["blue"], spacing1=3, spacing3=4)
    tw.tag_configure("h3", font=(_FONT_UI, 11, "bold"),
                     foreground=C["green"], spacing1=2, spacing3=3)
    tw.tag_configure("bold", font=(_FONT_UI, 10, "bold"))
    tw.tag_configure("italic", font=(_FONT_UI, 10, "italic"))
    tw.tag_configure("code", font=(_FONT_MONO, 10),
                     background=C["surface2"], foreground=C["green"])
    tw.tag_configure("bullet", foreground=C["subtext"])
    tw.tag_configure("plain", font=F_BODY, foreground=C["text"])


_INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+?`|\*[^*]+?\*)")


def _md_insert_inline(tw, text):
    idx = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > idx:
            tw.insert("end", text[idx:m.start()], ("plain",))
        tok = m.group(1)
        if tok.startswith("**"):
            tw.insert("end", tok[2:-2], ("bold",))
        elif tok.startswith("`"):
            tw.insert("end", tok[1:-1], ("code",))
        else:
            tw.insert("end", tok[1:-1], ("italic",))
        idx = m.end()
    if idx < len(text):
        tw.insert("end", text[idx:], ("plain",))


def render_markdown(tw, md):
    """把 markdown 文本渲染进一个（只读）Text 组件。"""
    was_disabled = str(tw.cget("state")) == "disabled"
    tw.configure(state="normal")
    tw.delete("1.0", "end")
    _md_config_tags(tw)
    for line in (md or "").splitlines():
        stripped = line.strip()
        if line.startswith("### "):
            tw.insert("end", line[4:] + "\n", ("h3",))
        elif line.startswith("## "):
            tw.insert("end", line[3:] + "\n", ("h2",))
        elif line.startswith("# "):
            tw.insert("end", line[2:] + "\n", ("h1",))
        elif stripped.startswith(("- ", "* ")):
            tw.insert("end", "   •  ", ("bullet",))
            _md_insert_inline(tw, stripped[2:])
            tw.insert("end", "\n")
        elif stripped == "":
            tw.insert("end", "\n")
        else:
            _md_insert_inline(tw, line)
            tw.insert("end", "\n")
    if was_disabled:
        tw.configure(state="disabled")


class SettingsDialog:
    """Modal settings dialog — completely independent window."""

    W, H = 410, 700

    def __init__(self, parent, app):
        self.app = app
        self.result = None

        self.top = tk.Toplevel(parent)
        self.top.title("⚙ 番茄钟设置")
        self.top.geometry(f"{self.W}x{self.H}")
        self.top.resizable(False, False)
        self.top.configure(bg=C["bg"])
        self.top.transient(parent)
        self.top.grab_set()

        # Center on parent
        self.top.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.H) // 2
        self.top.geometry(f"+{px}+{py}")

        self._build()
        self._load_values()

        # Close with Escape
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)

        # Wait until closed
        parent.wait_window(self.top)

    def _build(self):
        top = self.top
        pad = {"padx": 16, "pady": 4}

        # Title
        tk.Label(top, text="⚙  番茄钟设置", font=F_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(anchor="w", padx=16, pady=(14, 10))

        # ── Duration rows ──
        self._vars = {}
        self._labels = {}
        rows = [
            ("🍅  专注时长（分钟）", "pomodoro", 1, 120),
            ("☕  短休息时长（分钟）", "short_break", 1, 30),
            ("🌿  长休息时长（分钟）", "long_break", 1, 60),
            ("📏  长休息间隔（几个番茄后）", "interval", 1, 10),
        ]
        for text, key, lo, hi in rows:
            row = tk.Frame(top, bg=C["bg"])
            row.pack(fill="x", **pad)
            tk.Label(row, text=text, font=F_LABEL,
                     fg=C["text"], bg=C["bg"]).pack(side="left")

            ctrl = tk.Frame(row, bg=C["bg"])
            ctrl.pack(side="right")

            val = self.app.long_interval if key == "interval" else self.app.durations[key] // 60
            self._vars[key] = val

            # Minus
            b1 = tk.Button(ctrl, text="−", font=(_FONT_SYMBOL, 12, "bold"),
                           fg=C["text"], bg=C["surface2"], relief="flat", bd=0,
                           activebackground=C["red"], activeforeground=C["white"],
                           width=2, cursor="hand2",
                           command=self._make_dec(key, lo))
            b1.pack(side="left")

            # Value label
            lbl = tk.Label(ctrl, text=str(val), font=(_FONT_MONO, 13, "bold"),
                           fg=C["text"], bg=C["surface2"], width=4)
            lbl.pack(side="left", ipady=4)
            self._labels[key] = lbl

            # Plus
            b2 = tk.Button(ctrl, text="+", font=(_FONT_SYMBOL, 12, "bold"),
                           fg=C["text"], bg=C["surface2"], relief="flat", bd=0,
                           activebackground=C["green"], activeforeground=C["white"],
                           width=2, cursor="hand2",
                           command=self._make_inc(key, hi))
            b2.pack(side="left")

        # ── Checkboxes ──
        self._auto_break = tk.BooleanVar(value=self.app.auto_break)
        cb1 = tk.Checkbutton(top, text="🔔 专注结束 → 自动开始休息",
                             variable=self._auto_break,
                             font=F_LABEL, fg=C["text"], bg=C["bg"],
                             selectcolor=C["surface2"],
                             activebackground=C["bg"], activeforeground=C["text"],
                             relief="flat", bd=0)
        cb1.pack(anchor="w", padx=16, pady=(8, 2))

        self._auto_pom = tk.BooleanVar(value=self.app.auto_pom)
        cb2 = tk.Checkbutton(top, text="🔔 休息结束 → 自动开始专注",
                             variable=self._auto_pom,
                             font=F_LABEL, fg=C["text"], bg=C["bg"],
                             selectcolor=C["surface2"],
                             activebackground=C["bg"], activeforeground=C["text"],
                             relief="flat", bd=0)
        cb2.pack(anchor="w", padx=16, pady=2)

        # ── NEW: bring window to front on timer end ──
        self._bring_front = tk.BooleanVar(value=self.app.bring_to_front)
        cb3 = tk.Checkbutton(top, text="⬆ 计时结束置顶窗口（抢占焦点）",
                             variable=self._bring_front,
                             font=F_LABEL, fg=C["text"], bg=C["bg"],
                             selectcolor=C["surface2"],
                             activebackground=C["bg"], activeforeground=C["text"],
                             relief="flat", bd=0)
        cb3.pack(anchor="w", padx=16, pady=2)

        self._log_prompt = tk.BooleanVar(value=self.app.log_prompt)
        cb4 = tk.Checkbutton(top, text="📝 专注结束 → 弹出记录窗口",
                             variable=self._log_prompt,
                             font=F_LABEL, fg=C["text"], bg=C["bg"],
                             selectcolor=C["surface2"],
                             activebackground=C["bg"], activeforeground=C["text"],
                             relief="flat", bd=0)
        cb4.pack(anchor="w", padx=16, pady=2)

        # ── Sound section ──
        tk.Label(top, text="🔊  音效设置", font=F_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(anchor="w", padx=16, pady=(10, 4))

        self._sound_enabled = tk.BooleanVar(value=self.app.sound_enabled)
        cb_snd = tk.Checkbutton(top, text="🔔 启用结束音效",
                                variable=self._sound_enabled,
                                font=F_LABEL, fg=C["text"], bg=C["bg"],
                                selectcolor=C["surface2"],
                                activebackground=C["bg"], activeforeground=C["text"],
                                relief="flat", bd=0)
        cb_snd.pack(anchor="w", padx=16, pady=2)

        self._sound_per_mode = tk.BooleanVar(value=self.app.sound_per_mode)
        cb_pm = tk.Checkbutton(top, text="不同模式使用不同音效",
                               variable=self._sound_per_mode,
                               font=F_LABEL, fg=C["text"], bg=C["bg"],
                               selectcolor=C["surface2"],
                               activebackground=C["bg"], activeforeground=C["text"],
                               relief="flat", bd=0,
                               command=self._on_per_mode_toggle)
        cb_pm.pack(anchor="w", padx=16, pady=2)

        # 预设下拉区域（统一 vs 每模式）
        self._preset_container = tk.Frame(top, bg=C["bg"])
        self._preset_container.pack(fill="x", padx=16, pady=(2, 2))

        self._preset_rows = {}
        self._preset_selected_value = {}

        self._shared_preset_frame = tk.Frame(self._preset_container, bg=C["bg"])
        self._build_preset_row(self._shared_preset_frame, "统一音效", "sound_preset")

        self._per_mode_frames = {}
        for _m, _lbl in [("pomodoro", "专注"), ("short_break", "短休息"), ("long_break", "长休息")]:
            _fr = tk.Frame(self._preset_container, bg=C["bg"])
            self._build_preset_row(_fr, _lbl, "sound_preset_" + _m)
            self._per_mode_frames[_m] = _fr

        if self.app.sound_per_mode:
            for _fr in self._per_mode_frames.values():
                _fr.pack(fill="x", pady=2)
        else:
            self._shared_preset_frame.pack(fill="x", pady=2)

        # ── Volume ──
        vol_frame = tk.Frame(top, bg=C["bg"])
        vol_frame.pack(fill="x", padx=16, pady=(4, 2))
        tk.Label(vol_frame, text="🔉 音量", font=F_LABEL,
                 fg=C["text"], bg=C["bg"]).pack(side="left")
        self._sound_volume = tk.IntVar(value=self.app.sound_volume)
        self._vol_label = tk.Label(vol_frame, text=f"{self.app.sound_volume}%",
                                   font=F_LABEL, fg=C["subtext"], bg=C["bg"])
        scale = tk.Scale(vol_frame, from_=0, to=100, orient="horizontal",
                         variable=self._sound_volume, showvalue=False,
                         bg=C["bg"], fg=C["text"], troughcolor=C["surface2"],
                         sliderrelief="flat", length=180,
                         command=lambda v: self._vol_label.configure(text=f"{int(float(v))}%"))
        scale.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self._vol_label.pack(side="left")

        # ── Test button ──
        tk.Button(top, text="🔊 测试", font=F_LABEL,
                  fg=C["subtext"], bg=C["surface2"], relief="flat", bd=0,
                  activebackground=C["surface"], activeforeground=C["text"],
                  padx=18, pady=5, cursor="hand2",
                  command=self._test_sound).pack(anchor="e", padx=16, pady=(2, 8))

        # ── Buttons ──
        btn_frame = tk.Frame(top, bg=C["bg"])
        btn_frame.pack(pady=(16, 12))

        tk.Button(btn_frame, text="取消", font=F_LABEL,
                  fg=C["subtext"], bg=C["surface2"], relief="flat", bd=0,
                  activebackground=C["surface"], activeforeground=C["text"],
                  padx=20, pady=6, cursor="hand2",
                  command=self.top.destroy).pack(side="left", padx=6)

        tk.Button(btn_frame, text="✓  保存", font=(_FONT_UI, 9, "bold"),
                  fg=C["white"], bg=C["red"], relief="flat", bd=0,
                  activebackground="#f5a0b8", activeforeground=C["white"],
                  padx=24, pady=6, cursor="hand2",
                  command=self._save).pack(side="left", padx=6)

    def _make_dec(self, key, lo):
        def fn():
            cur = self._vars[key]
            if cur > lo:
                cur -= 1
                self._vars[key] = cur
                self._labels[key].configure(text=str(cur))
        return fn

    def _make_inc(self, key, hi):
        def fn():
            cur = self._vars[key]
            if cur < hi:
                cur += 1
                self._vars[key] = cur
                self._labels[key].configure(text=str(cur))
        return fn

    def _load_values(self):
        self._vars["pomodoro"] = self.app.durations["pomodoro"] // 60
        self._vars["short_break"] = self.app.durations["short_break"] // 60
        self._vars["long_break"] = self.app.durations["long_break"] // 60
        self._vars["interval"] = self.app.long_interval
        for key in ["pomodoro", "short_break", "long_break", "interval"]:
            self._labels[key].configure(text=str(self._vars[key]))

    def _save(self):
        self.app.durations["pomodoro"] = self._vars["pomodoro"] * 60
        self.app.durations["short_break"] = self._vars["short_break"] * 60
        self.app.durations["long_break"] = self._vars["long_break"] * 60
        self.app.long_interval = self._vars["interval"]
        self.app.auto_break = self._auto_break.get()
        self.app.auto_pom = self._auto_pom.get()
        self.app.bring_to_front = self._bring_front.get()
        self.app.log_prompt = self._log_prompt.get()
        # ── sound settings ──
        self.app.sound_enabled = self._sound_enabled.get()
        self.app.sound_per_mode = self._sound_per_mode.get()
        self.app.sound_preset = self._preset_selected_value.get("sound_preset", self.app.sound_preset)
        self.app.sound_preset_pomodoro = self._preset_selected_value.get("sound_preset_pomodoro", self.app.sound_preset_pomodoro)
        self.app.sound_preset_short_break = self._preset_selected_value.get("sound_preset_short_break", self.app.sound_preset_short_break)
        self.app.sound_preset_long_break = self._preset_selected_value.get("sound_preset_long_break", self.app.sound_preset_long_break)
        self.app.sound_volume = self._sound_volume.get()
        self.app._save_config()
        if not self.app.running and not self.app.paused:
            self.app._reset_current()
            self.app._sync_ui()
        self.top.destroy()


    # ── Sound-related helpers ──
    def _build_preset_row(self, parent, label, attr):
        """构建一行：标签 + 音效预设下拉框（含已上传的自定义 .wav）。"""
        tk.Label(parent, text=label, font=F_LABEL,
                 fg=C["text"], bg=C["bg"]).pack(side="left")
        var = tk.StringVar(value=_display_for_value(getattr(self.app, attr)))
        cb = ttk.Combobox(parent, textvariable=var, state="readonly",
                          width=20, font=F_LABEL)
        cb["values"] = [d for d, _ in _sound_options()]
        cb.pack(side="left", padx=(8, 0))
        cb.bind("<<ComboboxSelected>>",
                lambda e: self._on_preset_selected(cb, var, attr))
        self._preset_rows[attr] = (cb, var)
        self._preset_selected_value[attr] = getattr(self.app, attr)

    def _on_preset_selected(self, cb, var, attr):
        selected = var.get()
        if selected == CUSTOM_OPTION:
            newfile = self._upload_custom()
            if newfile:
                # 刷新本行下拉选项以包含新上传文件
                cb["values"] = [d for d, _ in _sound_options()]
                var.set(newfile)
                self._preset_selected_value[attr] = newfile
            else:
                # 取消则还原到此前已选值
                var.set(_display_for_value(self._preset_selected_value.get(attr)))
            return
        # 普通预设：显示名 -> value
        value = selected
        for d, v in _sound_options():
            if d == selected:
                value = v
                break
        self._preset_selected_value[attr] = value

    def _on_per_mode_toggle(self):
        """切换「统一 / 每模式」预设下拉的显隐。"""
        if self._sound_per_mode.get():
            self._shared_preset_frame.pack_forget()
            for _fr in self._per_mode_frames.values():
                _fr.pack(fill="x", pady=2)
        else:
            for _fr in self._per_mode_frames.values():
                _fr.pack_forget()
            self._shared_preset_frame.pack(fill="x", pady=2)

    def _upload_custom(self):
        """弹出文件框选择 .wav，校验后复制到 SOUNDS_DIR，返回文件名或 None。"""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="选择音效文件（.wav）",
            filetypes=[("WAV 音频", "*.wav"), ("所有文件", "*.*")])
        if not path:
            return None
        src = Path(path)
        if src.suffix.lower() != ".wav":
            messagebox.showerror("格式不支持", "仅支持 .wav 格式的音效文件。")
            return None
        # 校验：尝试用 wave 模块预读，失败则判定为无效音频
        if not _validate_wav_file(src):
            messagebox.showerror("无效音频文件", "所选文件不是有效的 WAV 音频文件。")
            return None
        # 复制到音效目录
        dest = SOUNDS_DIR / src.name
        try:
            import shutil
            shutil.copyfile(src, dest)
        except Exception:
            messagebox.showerror("复制失败", "无法将文件复制到音效目录。")
            return None
        return src.name

    def _test_sound(self):
        """立即用当前设置播放一次选中的音效（忽略启用开关）。"""
        if self._sound_per_mode.get():
            attr = {"pomodoro": "sound_preset_pomodoro",
                    "short_break": "sound_preset_short_break",
                    "long_break": "sound_preset_long_break"}[self.app.mode]
        else:
            attr = "sound_preset"
        value = self._preset_selected_value.get(attr, getattr(self.app, attr))
        vol = self._sound_volume.get()
        threading.Thread(target=self.app._play_preset,
                         args=(value, vol), daemon=True).start()


class SessionLogDialog:
    """
    计时结束记录弹窗 — 非阻塞（不 wait_window，不阻塞主线程/计时）。
    模态：transient + grab_set；层级：-topmost 强制高于主窗口。
    """

    W, H = 460, 500
    PH = "这段时间你完成了什么？"

    def __init__(self, app, start_dt, end_dt, duration_min, task):
        self.app = app
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.duration_min = duration_min
        self.task = task or ""
        self._saved = False
        self._preview_on = False

        parent = app.root
        self.top = tk.Toplevel(parent)
        self.top.title("记录本次专注")
        self.top.geometry(f"{self.W}x{self.H}")
        self.top.minsize(400, 440)
        self.top.configure(bg=C["bg"])
        self.top.transient(parent)

        # 弹窗强制高于主窗口
        self.top.attributes("-topmost", True)

        # Center on parent
        self.top.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.H) // 2
        if px < 0 or py < 0:
            px, py = 200, 120
        self.top.geometry(f"+{px}+{py}")

        self._build()

        # 模态但非阻塞：grab 输入焦点，但不 wait_window
        try:
            self.top.grab_set()
        except Exception:
            pass

        # 全局（窗口级）快捷键关闭弹窗
        self.top.bind("<Escape>", lambda e: self._skip())
        self.top.bind("<Control-Return>", lambda e: self._save())
        self.top.bind("<Control-s>", lambda e: (self._save(), "break"))
        self.top.protocol("WM_DELETE_WINDOW", self._skip)

        self.top.after(60, self._focus_editor)

    def _build(self):
        top = self.top

        tk.Label(top, text="📝  记录本次专注", font=F_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(anchor="w", padx=18, pady=(14, 6))

        # ── Metadata ──
        meta = tk.Frame(top, bg=C["surface"])
        meta.pack(fill="x", padx=18, pady=(0, 10))
        info = [
            ("📅 日期", self.start_dt.strftime("%Y-%m-%d")),
            ("▶ 开始", self.start_dt.strftime("%H:%M:%S")),
            ("⏹ 结束", self.end_dt.strftime("%H:%M:%S")),
            ("⏱ 设定时长", f"{self.duration_min} 分钟"),
        ]
        if self.task:
            info.append(("✏️ 任务", self.task))
        grid = tk.Frame(meta, bg=C["surface"])
        grid.pack(fill="x", padx=12, pady=10)
        for i, (k, v) in enumerate(info):
            tk.Label(grid, text=k, font=F_SMALL, fg=C["subtext"], bg=C["surface"],
                     anchor="w").grid(row=i, column=0, sticky="w", padx=(0, 12), pady=1)
            tk.Label(grid, text=v, font=F_LABEL, fg=C["text"], bg=C["surface"],
                     anchor="w").grid(row=i, column=1, sticky="w", pady=1)

        # ── Editor / preview toolbar ──
        bar = tk.Frame(top, bg=C["bg"])
        bar.pack(fill="x", padx=18)
        tk.Label(bar, text="支持 **Markdown** 格式", font=F_SMALL,
                 fg=C["muted"], bg=C["bg"]).pack(side="left")
        self._preview_btn = tk.Button(
            bar, text="👁 预览", font=F_SMALL,
            fg=C["subtext"], bg=C["surface"], relief="flat", bd=0,
            activebackground=C["surface2"], activeforeground=C["text"],
            padx=10, pady=2, cursor="hand2", command=self._toggle_preview)
        self._preview_btn.pack(side="right")

        # ── Text area container ──
        box = tk.Frame(top, bg=C["border"])
        box.pack(fill="both", expand=True, padx=18, pady=(6, 10))

        self._editor = tk.Text(box, font=F_BODY, fg=C["subtext"], bg=C["surface"],
                               insertbackground=C["text"], relief="flat", bd=0,
                               wrap="word", height=6, padx=10, pady=8,
                               undo=True)
        self._editor.pack(fill="both", expand=True, padx=1, pady=1)
        self._editor.insert("1.0", self.PH)
        self._editor.bind("<FocusIn>", self._on_focus_in)
        self._editor.bind("<FocusOut>", self._on_focus_out)

        # preview widget (created lazily, same box)
        self._preview = tk.Text(box, font=F_BODY, fg=C["text"], bg=C["surface"],
                                relief="flat", bd=0, wrap="word", height=6,
                                padx=10, pady=8, state="disabled")

        # ── Buttons ──
        btns = tk.Frame(top, bg=C["bg"])
        btns.pack(fill="x", padx=18, pady=(0, 14))

        tk.Button(btns, text="跳过", font=F_LABEL,
                  fg=C["subtext"], bg=C["surface2"], relief="flat", bd=0,
                  activebackground=C["surface"], activeforeground=C["text"],
                  padx=22, pady=7, cursor="hand2",
                  command=self._skip).pack(side="left")

        tk.Label(btns, text="Esc 跳过 · Ctrl+S 保存", font=F_SMALL,
                 fg=C["muted"], bg=C["bg"]).pack(side="left", padx=12)

        tk.Button(btns, text="✓  保存记录", font=(_FONT_UI, 9, "bold"),
                  fg=C["white"], bg=C["green"], relief="flat", bd=0,
                  activebackground="#b8ecb0", activeforeground=C["bg"],
                  padx=24, pady=7, cursor="hand2",
                  command=self._save).pack(side="right")

    # ── placeholder handling ──
    def _on_focus_in(self, e):
        if self._editor.get("1.0", "end-1c") == self.PH:
            self._editor.delete("1.0", "end")
            self._editor.configure(fg=C["text"])

    def _on_focus_out(self, e):
        if not self._editor.get("1.0", "end-1c").strip():
            self._editor.delete("1.0", "end")
            self._editor.insert("1.0", self.PH)
            self._editor.configure(fg=C["subtext"])

    def _focus_editor(self):
        try:
            self.top.lift()
            self.top.focus_force()
            self._editor.focus_set()
        except Exception:
            pass

    def _current_text(self):
        t = self._editor.get("1.0", "end-1c")
        if t.strip() == self.PH or not t.strip():
            return ""
        return t.rstrip()

    def _toggle_preview(self):
        if not self._preview_on:
            render_markdown(self._preview, self._current_text() or "_（暂无内容）_")
            self._editor.pack_forget()
            self._preview.pack(fill="both", expand=True, padx=1, pady=1)
            self._preview_btn.configure(text="✎ 编辑", fg=C["green"])
            self._preview_on = True
        else:
            self._preview.pack_forget()
            self._editor.pack(fill="both", expand=True, padx=1, pady=1)
            self._preview_btn.configure(text="👁 预览", fg=C["subtext"])
            self._preview_on = False
            self._editor.focus_set()

    def _save(self):
        note = self._current_text()
        record = {
            "date": self.start_dt.strftime("%Y-%m-%d"),
            "start": self.start_dt.strftime("%H:%M:%S"),
            "end": self.end_dt.strftime("%H:%M:%S"),
            "duration_min": self.duration_min,
            "task": self.task,
            "note": note,
            "ts": self.end_dt.isoformat(timespec="seconds"),
        }
        self.app._append_log(record)
        self._saved = True
        self._close()

    def _skip(self):
        # 跳过：不保存空记录，直接关闭
        self._close()

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
        except Exception:
            pass


class HistoryDialog:
    """历史记录查看面板 — 左侧列表，右侧 Markdown 渲染。"""

    W, H = 640, 460

    def __init__(self, app):
        self.app = app
        self.logs = app._load_logs()
        # newest first
        self.logs = list(reversed(self.logs))

        parent = app.root
        self.top = tk.Toplevel(parent)
        self.top.title("📖 专注历史记录")
        self.top.geometry(f"{self.W}x{self.H}")
        self.top.minsize(520, 360)
        self.top.configure(bg=C["bg"])
        self.top.transient(parent)

        self.top.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.H) // 2
        if px < 0 or py < 0:
            px, py = 160, 100
        self.top.geometry(f"+{px}+{py}")

        self._build()
        self.top.bind("<Escape>", lambda e: self.top.destroy())

    def _build(self):
        top = self.top

        head = tk.Frame(top, bg=C["bg"])
        head.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(head, text="📖  专注历史记录", font=F_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(side="left")
        tk.Label(head, text=f"共 {len(self.logs)} 条", font=F_SMALL,
                 fg=C["subtext"], bg=C["bg"]).pack(side="left", padx=10)

        body = tk.Frame(top, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # ── left list ──
        left = tk.Frame(body, bg=C["surface"], width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._listbox = tk.Listbox(
            left, font=F_LABEL, fg=C["text"], bg=C["surface"],
            selectbackground=C["red"], selectforeground=C["white"],
            relief="flat", bd=0, highlightthickness=0, activestyle="none")
        self._listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── right preview ──
        right = tk.Frame(body, bg=C["border"])
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self._detail = tk.Text(right, font=F_BODY, fg=C["text"], bg=C["surface"],
                               relief="flat", bd=0, wrap="word",
                               padx=12, pady=10, state="disabled")
        self._detail.pack(fill="both", expand=True, padx=1, pady=1)

        if not self.logs:
            self._listbox.insert("end", "（暂无记录）")
            render_markdown(self._detail, "# 还没有专注记录\n\n完成一次专注并保存记录后，这里就会出现历史。")
            return

        for r in self.logs:
            task = r.get("task", "").strip()
            note = r.get("note", "").strip()
            head_txt = task or (note.splitlines()[0] if note else "（无备注）")
            if len(head_txt) > 16:
                head_txt = head_txt[:16] + "…"
            label = f"{r.get('date','')[5:]} {r.get('start','')[:5]} · {head_txt}"
            self._listbox.insert("end", label)

        self._listbox.selection_set(0)
        self._show(0)

    def _on_select(self, e):
        sel = self._listbox.curselection()
        if sel:
            self._show(sel[0])

    def _show(self, idx):
        if idx < 0 or idx >= len(self.logs):
            return
        r = self.logs[idx]
        meta = (
            f"# {r.get('date','')}  ·  {r.get('start','')}–{r.get('end','')}\n"
            f"**设定时长：** {r.get('duration_min','?')} 分钟\n"
        )
        if r.get("task"):
            meta += f"**任务：** {r.get('task')}\n"
        meta += "\n---\n\n"
        note = r.get("note", "").strip() or "_（本次未填写记录）_"
        render_markdown(self._detail, meta + note)


class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.geometry("380x530")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])

        # ── State ──
        self.mode = "pomodoro"
        self.durations = {"pomodoro": 25*60, "short_break": 5*60, "long_break": 15*60}
        self.long_interval = 4
        self.auto_break = True
        self.auto_pom = False
        self.on_top = False
        self.bring_to_front = False      # NEW: raise + steal focus when timer ends
        self.log_prompt = True           # NEW: pop log dialog after a focus session

        # ── Sound (audio) settings ──
        self.sound_enabled = True
        self.sound_per_mode = False
        self.sound_preset = DEFAULT_PRESET
        self.sound_preset_pomodoro = DEFAULT_PRESET
        self.sound_preset_short_break = DEFAULT_PRESET
        self.sound_preset_long_break = DEFAULT_PRESET
        self.sound_volume = 80

        self.remaining = 25 * 60
        self.total = 25 * 60
        self.running = False
        self.paused = False
        self.sessions_today = 0
        self.streak = 0
        self._stop = threading.Event()
        self._timer_thread = None
        self._session_start_dt = None    # NEW: when current focus session began

        # Tray
        self._tray = None
        self._tray_thread = None
        self._quitting = False

        # Task placeholder
        self._task_ph = "✏️  当前正在做什么？"

        # Load data
        self._load_config()
        self._load_sessions()
        self._reset_current()

        # Build
        self._build_ui()
        self._sync_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_tray()

    # ═══════════════════════════════════════════════════════════
    #  PERSISTENCE
    # ═══════════════════════════════════════════════════════════

    def _load_config(self):
        try:
            if CONFIG_FILE.exists():
                d = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                if "durations" in d:
                    self.durations.update(d["durations"])
                self.long_interval = d.get("long_interval", 4)
                self.auto_break = d.get("auto_break", True)
                self.auto_pom = d.get("auto_pom", False)
                self.on_top = d.get("on_top", False)
                self.bring_to_front = d.get("bring_to_front", False)
                self.log_prompt = d.get("log_prompt", True)
                # ── sound settings (兼容旧配置：缺失时取默认值) ──
                self.sound_enabled = d.get("sound_enabled", True)
                self.sound_per_mode = d.get("sound_per_mode", False)
                self.sound_preset = d.get("sound_preset", DEFAULT_PRESET)
                self.sound_preset_pomodoro = d.get("sound_preset_pomodoro", DEFAULT_PRESET)
                self.sound_preset_short_break = d.get("sound_preset_short_break", DEFAULT_PRESET)
                self.sound_preset_long_break = d.get("sound_preset_long_break", DEFAULT_PRESET)
                self.sound_volume = d.get("sound_volume", 80)
        except Exception:
            pass

    def _save_config(self):
        try:
            CONFIG_FILE.write_text(json.dumps({
                "durations": self.durations,
                "long_interval": self.long_interval,
                "auto_break": self.auto_break,
                "auto_pom": self.auto_pom,
                "on_top": self.on_top,
                "bring_to_front": self.bring_to_front,
                "log_prompt": self.log_prompt,
                "sound_enabled": self.sound_enabled,
                "sound_per_mode": self.sound_per_mode,
                "sound_preset": self.sound_preset,
                "sound_preset_pomodoro": self.sound_preset_pomodoro,
                "sound_preset_short_break": self.sound_preset_short_break,
                "sound_preset_long_break": self.sound_preset_long_break,
                "sound_volume": self.sound_volume,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load_sessions(self):
        today = date.today().isoformat()
        try:
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
                self.sessions_today = data.get(today, 0)
        except Exception:
            self.sessions_today = 0

    def _save_sessions(self):
        today = date.today().isoformat()
        try:
            data = {}
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            data[today] = self.sessions_today
            SESSIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load_logs(self):
        try:
            if LOGS_FILE.exists():
                data = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _append_log(self, record):
        try:
            data = self._load_logs()
            data.append(record)
            LOGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  TIMER ENGINE
    # ═══════════════════════════════════════════════════════════

    def _reset_current(self):
        key = {"pomodoro": "pomodoro", "short_break": "short_break",
               "long_break": "long_break"}[self.mode]
        self.total = self.durations[key]
        self.remaining = self.total

    def _stop_timer(self):
        self._stop.set()
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=0.5)

    def _run_timer(self):
        while not self._stop.is_set() and self.remaining > 0:
            time.sleep(0.2)
            if self._stop.is_set():
                return
            self.remaining -= 0.2
            if self.remaining < 0:
                self.remaining = 0
            self.root.after(0, self._on_tick)
        if self.remaining <= 0 and not self._stop.is_set():
            self.root.after(0, self._on_complete)

    def _on_tick(self):
        self._draw_ring()
        self._update_time_label()
        self._update_tray_tooltip()

    def _on_complete(self):
        self.running = False
        self.paused = False
        self._sync_ui()
        self._play_sound()
        self._notify()
        self._update_tray_tooltip()

        completed_mode = self.mode

        # ── 计时归零 → 按偏好置顶抢焦点，否则仅轻闪 ──
        if self.bring_to_front:
            self._bring_to_front()
        else:
            self._flash_window()

        if completed_mode == "pomodoro":
            # capture session metadata BEFORE switching mode / resetting
            end_dt = datetime.now()
            start_dt = self._session_start_dt or end_dt
            duration_min = self.durations["pomodoro"] // 60
            task = self._current_task_text()

            self.sessions_today += 1
            self.streak += 1
            self._save_sessions()
            self._update_session_label()

            # 记录弹窗（非阻塞）
            if self.log_prompt:
                self._show_log_dialog(start_dt, end_dt, duration_min, task)

            self._session_start_dt = None

            if self.streak >= self.long_interval:
                self.mode = "long_break"
                self.streak = 0
            else:
                self.mode = "short_break"
            self._reset_current()
            self._sync_ui()
            if self.auto_break:
                self.root.after(800, self.start)
        else:
            self.mode = "pomodoro"
            self._reset_current()
            self._sync_ui()
            if self.auto_pom:
                self.root.after(800, self.start)

    def _show_log_dialog(self, start_dt, end_dt, duration_min, task):
        try:
            self._active_log_dialog = SessionLogDialog(
                self, start_dt, end_dt, duration_min, task)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  ACTIONS
    # ═══════════════════════════════════════════════════════════

    def start(self):
        if self.remaining <= 0.1:
            self._reset_current()
        if self.mode == "pomodoro" and self._session_start_dt is None:
            self._session_start_dt = datetime.now()
        self.running = True
        self.paused = False
        self._stop.clear()
        self._sync_ui()
        self._timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self._timer_thread.start()
        self._update_tray_tooltip()

    def pause(self):
        self.paused = True
        self._stop_timer()
        self.running = True
        self._sync_ui()
        self._update_tray_tooltip()

    def resume(self):
        self.paused = False
        self._stop.clear()
        self._sync_ui()
        self._timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self._timer_thread.start()
        self._update_tray_tooltip()

    def toggle(self):
        if not self.running:
            self.start()
        elif self.paused:
            self.resume()
        else:
            self.pause()

    def reset(self):
        self._stop_timer()
        self.running = False
        self.paused = False
        self._session_start_dt = None
        self._reset_current()
        self._sync_ui()
        self._update_tray_tooltip()

    def skip(self):
        self._stop_timer()
        self.running = False
        self.paused = False

        if self.mode == "pomodoro":
            self.sessions_today += 1
            self.streak += 1
            self._save_sessions()
            self._update_session_label()
            self._session_start_dt = None
            if self.streak >= self.long_interval:
                self.mode = "long_break"
                self.streak = 0
            else:
                self.mode = "short_break"
        else:
            self.mode = "pomodoro"

        self._reset_current()
        self._sync_ui()
        self._update_tray_tooltip()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        if self.running or self.paused:
            if not messagebox.askyesno("切换模式", "计时将被放弃，确定切换吗？"):
                return
        self._stop_timer()
        self.running = False
        self.paused = False
        self._session_start_dt = None
        if mode == "long_break":
            self.streak = 0
        self.mode = mode
        self._reset_current()
        self._sync_ui()

    def open_settings(self):
        """Open the settings dialog."""
        SettingsDialog(self.root, self)

    def open_history(self):
        """Open the history panel."""
        HistoryDialog(self)

    def _current_task_text(self):
        t = (self._task_var.get() or "").strip()
        if t == self._task_ph:
            return ""
        return t

    # ═══════════════════════════════════════════════════════════
    #  AUDIO & NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════

    def _play_sound(self):
        """计时结束音效：依据 sound_enabled 与（每模式）预设决定播放内容。"""
        if not self.sound_enabled:
            return
        preset = self._resolve_preset()
        self._emit_sound(preset, self.sound_volume)

    def _resolve_preset(self, mode=None):
        """返回当前应播放的音效预设 value（支持每模式独立）。"""
        if mode is None:
            mode = self.mode
        if self.sound_per_mode:
            return {
                "pomodoro": self.sound_preset_pomodoro,
                "short_break": self.sound_preset_short_break,
                "long_break": self.sound_preset_long_break,
            }[mode]
        return self.sound_preset

    def _emit_sound(self, preset, volume):
        """在后台线程播放，避免阻塞主线程/界面。"""
        threading.Thread(target=self._play_preset,
                         args=(preset, volume), daemon=True).start()

    def _play_preset(self, preset, volume=None):
        """
        实际播放（应在独立线程中调用）。
        - 内置预设用正弦波合成（跨平台）；
        - 自定义 .wav 用 OS 原生命令播放；
        - 音量控制通过波形振幅缩放；
        - 任何异常静默忽略，不弹窗不中断。
        """
        try:
            if volume is None:
                volume = self.sound_volume
            vol = max(0.0, min(1.0, int(volume) / 100.0))
            # 等效响度缩放（0.2~1.0，避免完全听不见）
            amp = 0.2 + 0.8 * vol

            if preset == "soft_triad":
                tones = [(523, 200), (659, 200), (784, 200)]
                for i, (f, d) in enumerate(tones):
                    _emit_tone(f, max(20, int(d * amp)), amp)
                    if i < 2:
                        time.sleep(0.15)
            elif preset == "beep_digital":
                _emit_tone(880, max(20, int(100 * amp)), amp)
            elif preset == "low_hum":
                _emit_tone(220, max(20, int(300 * amp)), amp)
            else:
                # 自定义文件：文件名即 value
                path = SOUNDS_DIR / preset
                if path.exists() and path.is_file():
                    try:
                        _play_wav_file(str(path))
                    except Exception:
                        self._play_fallback_triad(amp)
                else:
                    self._play_fallback_triad(amp)
        except Exception:
            pass

    def _play_fallback_triad(self, amp):
        try:
            for i, (f, d) in enumerate([(523, 200), (659, 200), (784, 200)]):
                _emit_tone(f, max(20, int(d * amp)), amp)
                if i < 2:
                    time.sleep(0.15)
        except Exception:
            pass

    def _notify(self):
        title = "🍅 番茄完成！休息一下吧～" if self.mode == "pomodoro" else "⏰ 休息结束！继续加油～"
        body = (self._task_var.get() or "").strip()
        if body == self._task_ph:
            body = ""

        try:
            if _IS_MAC:
                # macOS notification center via osascript
                # Escape double-quotes for AppleScript
                safe_title = title.replace('"', '\\"')
                safe_body = body.replace('"', '\\"')
                script = f'display notification "{safe_body}" with title "{safe_title}" sound name "Glass"'
                subprocess.run(["osascript", "-e", script],
                               check=False, capture_output=True)
            elif _IS_WIN:
                # Windows Toast notification
                ps = (
                    '[Windows.UI.Notifications.ToastNotificationManager,'
                    ' Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;'
                    f'$t = [Windows.UI.Notifications.ToastNotificationManager]'
                    f'::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);'
                    f'$n = $t.GetElementsByTagName("text");'
                    f'$n.Item(0).AppendChild($t.CreateTextNode("{title}")) > $null;'
                    f'$n.Item(1).AppendChild($t.CreateTextNode("{body}")) > $null;'
                    f'$toast = [Windows.UI.Notifications.ToastNotification]::new($t);'
                    f'[Windows.UI.Notifications.ToastNotificationManager]'
                    f'::CreateToastNotifier("Pomodoro").Show($toast)'
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Linux: notify-send
                subprocess.run(["notify-send", title, body],
                               check=False, capture_output=True)
        except Exception:
            pass

    def _flash_window(self):
        try:
            self.root.attributes("-topmost", True)
            self.root.after(400, lambda: self.root.attributes("-topmost", self.on_top))
        except Exception:
            pass

    def _bring_to_front(self):
        """
        强制把主窗口置顶并夺取系统焦点（覆盖所有其他应用之上）。
        - 跨平台：deiconify + lift + -topmost 切换 + focus_force
        - Windows：ctypes SetForegroundWindow + AttachThreadInput 可靠夺焦
        计时归零时结束后恢复到用户手动设置的 on_top 状态。
        """
        try:
            self.root.deiconify()
        except Exception:
            pass
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

        if sys.platform == "win32":
            self._win_force_foreground()

        # 恢复到用户设定的常驻置顶偏好（bring_to_front 只是"结束一瞬"抢焦点）
        self.root.after(2000, lambda: self._restore_topmost())

    def _restore_topmost(self):
        try:
            self.root.attributes("-topmost", self.on_top)
        except Exception:
            pass

    def _win_hwnd(self):
        try:
            import ctypes
            # GetParent(client-hwnd) → 真正的顶层窗口句柄
            return ctypes.windll.user32.GetParent(self.root.winfo_id())
        except Exception:
            return None

    def _win_force_foreground(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = self._win_hwnd()
            if not hwnd:
                return
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)

            fg = user32.GetForegroundWindow()
            cur_tid = kernel32.GetCurrentThreadId()
            fg_tid = user32.GetWindowThreadProcessId(fg, None)

            attached = False
            if fg_tid and fg_tid != cur_tid:
                attached = bool(user32.AttachThreadInput(fg_tid, cur_tid, True))
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            if attached:
                user32.AttachThreadInput(fg_tid, cur_tid, False)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  SYSTEM TRAY
    # ═══════════════════════════════════════════════════════════

    def _start_tray(self):
        if not HAS_PYSTRAY:
            return
        try:
            self._tray_thread = threading.Thread(target=self._tray_main, daemon=True)
            self._tray_thread.start()
        except Exception:
            pass

    def _tray_main(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([10, 14, 54, 56], fill="#f38ba8")
        draw.ellipse([24, 6, 40, 20], fill="#a6e3a1")

        menu = pystray.Menu(
            pystray.MenuItem("显示番茄钟", self._tray_show, default=True),
            pystray.MenuItem("开始 / 暂停", self._tray_toggle),
            pystray.MenuItem("跳过当前阶段", self._tray_skip),
            pystray.MenuItem("专注历史记录", self._tray_history),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._tray_quit),
        )
        self._tray = pystray.Icon("pomodoro", img, "番茄钟", menu)
        try:
            self._tray.run()
        except Exception:
            pass

    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self._show_window)

    def _tray_toggle(self, icon=None, item=None):
        self.root.after(0, self.toggle)

    def _tray_skip(self, icon=None, item=None):
        self.root.after(0, self.skip)

    def _tray_history(self, icon=None, item=None):
        self.root.after(0, self.open_history)

    def _tray_quit(self, icon=None, item=None):
        self._quitting = True
        try:
            self._tray.stop()
        except Exception:
            pass
        self.root.after(0, self.root.destroy)

    def _update_tray_tooltip(self):
        if not self._tray:
            return
        try:
            m, s = divmod(int(self.remaining), 60)
            icon = "⏸" if self.paused else "▶" if self.running else "■"
            label = {"pomodoro": "专注", "short_break": "短休", "long_break": "长休"}[self.mode]
            self._tray.title = f"{icon} {label} {m:02d}:{s:02d}"
        except Exception:
            pass

    def _on_close(self):
        if HAS_PYSTRAY and not self._quitting:
            self.root.withdraw()
        else:
            self._quitting = True
            try:
                if self._tray:
                    self._tray.stop()
            except Exception:
                pass
            self.root.destroy()

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ═══════════════════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        r = self.root
        r.configure(bg=C["bg"])

        # ── Header ──
        hdr = tk.Frame(r, bg=C["bg"])
        hdr.pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(hdr, text="🍅 番茄钟", font=F_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(side="left")

        top_btns = tk.Frame(hdr, bg=C["bg"])
        top_btns.pack(side="right")

        def mk_hdr_btn(text, cmd):
            return tk.Button(
                top_btns, text=text, font=F_SMALL,
                fg=C["subtext"], bg=C["surface"], relief="flat", bd=0,
                activebackground=C["surface2"], activeforeground=C["text"],
                padx=8, pady=4, cursor="hand2", command=cmd)

        self._btn_top = mk_hdr_btn("📌 置顶", self._toggle_ontop)
        self._btn_top.pack(side="right", padx=2)

        self._btn_settings = mk_hdr_btn("⚙ 设置", self.open_settings)
        self._btn_settings.pack(side="right", padx=2)

        self._btn_history = mk_hdr_btn("📖 历史", self.open_history)
        self._btn_history.pack(side="right", padx=2)

        # ── Mode tabs ──
        tab_outer = tk.Frame(r, bg=C["surface"])
        tab_outer.pack(fill="x", padx=18, pady=(0, 14))
        tab_inner = tk.Frame(tab_outer, bg=C["surface"])
        tab_inner.pack(fill="x", padx=3, pady=3)

        self._tabs = {}
        modes = [("pomodoro", "🍅 专注"), ("short_break", "☕ 短休息"), ("long_break", "🌿 长休息")]
        for key, label in modes:
            btn = tk.Button(tab_inner, text=label, font=F_TAB,
                            relief="flat", bd=0, padx=6, pady=8, cursor="hand2",
                            command=lambda k=key: self.set_mode(k))
            btn.pack(side="left", fill="x", expand=True, padx=1)
            self._tabs[key] = btn

        # ── Canvas ring ──
        self._cv_size = 220
        cv_frame = tk.Frame(r, bg=C["bg"])
        cv_frame.pack(pady=(0, 4))
        self._cv = tk.Canvas(cv_frame, width=self._cv_size, height=self._cv_size,
                             bg=C["bg"], highlightthickness=0)
        self._cv.pack()

        cx = self._cv_size // 2
        self._time_id = self._cv.create_text(
            cx, cx - 6, text="25:00", font=F_TIME, fill=C["red"], anchor="center")
        self._status_id = self._cv.create_text(
            cx, cx + 30, text="准备开始", font=F_SMALL, fill=C["subtext"], anchor="center")

        # ── Session counter ──
        self._session_lbl = tk.Label(r, text="今日 0 🍅", font=F_LABEL,
                                     fg=C["subtext"], bg=C["bg"])
        self._session_lbl.pack(pady=(0, 10))

        # ── Control buttons ──
        ctrl = tk.Frame(r, bg=C["bg"])
        ctrl.pack(pady=(0, 6))

        def mkbtn(t, f, fg, bg, cmd, w, h):
            return tk.Button(ctrl, text=t, font=f, fg=fg, bg=bg,
                             relief="flat", bd=0, width=w, height=h,
                             activebackground=C["surface2"], activeforeground=C["text"],
                             cursor="hand2", command=cmd)

        self._btn_reset = mkbtn("↺", (_FONT_SYMBOL, 14), C["subtext"], C["surface"], self.reset, 3, 2)
        self._btn_reset.pack(side="left", padx=6)
        self._btn_start = mkbtn("▶", (_FONT_SYMBOL, 18, "bold"), C["white"], C["red"], self.toggle, 4, 2)
        self._btn_start.pack(side="left", padx=6)
        self._btn_skip = mkbtn("⏭", (_FONT_SYMBOL, 14), C["subtext"], C["surface"], self.skip, 3, 2)
        self._btn_skip.pack(side="left", padx=6)

        # ── Task input ──
        task_frame = tk.Frame(r, bg=C["bg"])
        task_frame.pack(fill="x", padx=18, pady=(8, 10))

        self._task_var = tk.StringVar(value=self._task_ph)
        self._task_entry = tk.Entry(
            task_frame, textvariable=self._task_var,
            font=(_FONT_UI, 10), fg=C["subtext"], bg=C["surface"],
            insertbackground=C["text"], relief="flat", bd=0,
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["red"])
        self._task_entry.pack(fill="x", ipady=7, padx=1)
        self._task_entry.bind("<FocusIn>", self._on_task_focus_in)
        self._task_entry.bind("<FocusOut>", self._on_task_focus_out)

        # ── Keyboard shortcuts ──
        r.bind("<space>", lambda e: self.toggle())
        r.bind("r", lambda e: self.reset())
        r.bind("s", lambda e: self.skip())
        r.bind("h", lambda e: self.open_history())
        r.bind("1", lambda e: self.set_mode("pomodoro"))
        r.bind("2", lambda e: self.set_mode("short_break"))
        r.bind("3", lambda e: self.set_mode("long_break"))

    def _toggle_ontop(self):
        self.on_top = not self.on_top
        self.root.attributes("-topmost", self.on_top)
        self._save_config()
        if self.on_top:
            self._btn_top.configure(text="📌 已置顶", fg=C["red"])
        else:
            self._btn_top.configure(text="📌 置顶", fg=C["subtext"])

    def _on_task_focus_in(self, e):
        if self._task_var.get() == self._task_ph:
            self._task_var.set("")
            self._task_entry.configure(fg=C["text"])

    def _on_task_focus_out(self, e):
        if not self._task_var.get().strip():
            self._task_var.set(self._task_ph)
            self._task_entry.configure(fg=C["subtext"])

    # ═══════════════════════════════════════════════════════════
    #  UI SYNC
    # ═══════════════════════════════════════════════════════════

    def _sync_ui(self):
        self._update_time_label()
        self._draw_ring()
        self._update_tab_colors()
        self._update_button()
        self._update_status_text()
        self._update_session_label()
        self._update_title_bar()

    def _update_time_label(self):
        m, s = divmod(int(self.remaining), 60)
        self._cv.itemconfig(self._time_id, text=f"{m:02d}:{s:02d}")
        color = {"pomodoro": C["red"], "short_break": C["green"], "long_break": C["blue"]}[self.mode]
        self._cv.itemconfig(self._time_id, fill=color)

    def _update_status_text(self):
        if self.running and not self.paused:
            txt = {"pomodoro": "专注中…", "short_break": "休息中…", "long_break": "长休息中…"}[self.mode]
        else:
            txt = {"pomodoro": "准备开始", "short_break": "准备休息", "long_break": "准备长休息"}[self.mode]
        self._cv.itemconfig(self._status_id, text=txt)

    def _update_title_bar(self):
        m, s = divmod(int(self.remaining), 60)
        self.root.title(f"{m:02d}:{s:02d} - 番茄钟")

    def _draw_ring(self):
        self._cv.delete("ring")
        cx = self._cv_size // 2
        r, w = 92, 9
        color = {"pomodoro": C["red"], "short_break": C["green"], "long_break": C["blue"]}[self.mode]

        self._cv.create_oval(cx - r, cx - r, cx + r, cx + r,
                             outline=C["surface"], width=w, tags="ring")
        if self.total > 0:
            fraction = self.remaining / self.total
            self._cv.create_arc(cx - r, cx - r, cx + r, cx + r,
                                start=90, extent=-(fraction * 360),
                                outline=color, width=w, style="arc", tags="ring")

    def _update_tab_colors(self):
        colors = {"pomodoro": C["red"], "short_break": C["green"], "long_break": C["blue"]}
        for key, btn in self._tabs.items():
            if key == self.mode:
                btn.configure(bg=colors[key], fg=C["white"])
            else:
                btn.configure(bg=C["surface"], fg=C["subtext"])

    def _update_button(self):
        if self.running and not self.paused:
            self._btn_start.configure(text="⏸", bg=C["subtext"])
        else:
            self._btn_start.configure(text="▶", bg=C["red"])

    def _update_session_label(self):
        self._session_lbl.configure(text=f"今日 {self.sessions_today} 🍅")

    def _update_tray_tooltip(self):
        if not self._tray:
            return
        try:
            m, s = divmod(int(self.remaining), 60)
            icon = "⏸" if self.paused else "▶" if self.running else "■"
            label = {"pomodoro": "专注", "short_break": "短休", "long_break": "长休"}[self.mode]
            self._tray.title = f"{icon} {label} {m:02d}:{s:02d}"
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  RUN
    # ═══════════════════════════════════════════════════════════

    def run(self):
        if self.on_top:
            self.root.attributes("-topmost", True)
            self._btn_top.configure(text="📌 已置顶", fg=C["red"])
        self.root.mainloop()


def main():
    app = PomodoroApp()
    app.run()


if __name__ == "__main__":
    main()
