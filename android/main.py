#!/usr/bin/env python3
"""
🍅 番茄钟 — Android 版（Kivy）
与 Windows 桌面版逻辑完全一致，可：
  1) 在手机 Termux 中直接原生运行（SDL2 全屏窗口）；
  2) 用 Buildozer 打包成正式 APK 安装。
"""

import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.utils import get_color_from_hex

from timer_core import PomodoroTimer

# ── Catppuccin 配色（与桌面版一致）──
C = {
    "bg": "#1e1e2e", "surface": "#313244", "surface2": "#45475a",
    "text": "#cdd6f4", "subtext": "#a6adc8", "muted": "#6c7086",
    "border": "#585b70", "red": "#f38ba8", "green": "#a6e3a1",
    "blue": "#89b4fa", "white": "#ffffff",
}
MODE_COLOR = {"pomodoro": C["red"], "short_break": C["green"], "long_break": C["blue"]}
MODE_TEXT = {"pomodoro": "🍅 专注", "short_break": "☕ 短休息", "long_break": "🌿 长休息"}

try:
    from plyer import notification, vibrator
    HAS_PLYER = True
except Exception:
    HAS_PLYER = False


def hx(name):
    return get_color_from_hex(C[name])


class Ring(Widget):
    """进度环（用 canvas 画圆 + 弧）。"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.remaining = 1.0
        self.total = 1.0
        self.color_name = "red"

    def redraw(self):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.width, self.height) / 2 - 16
        if r <= 0:
            return
        with self.canvas:
            Color(*hx("surface"))
            Line(circle=(cx, cy, r), width=10)
            frac = (self.remaining / self.total) if self.total else 0
            Color(*hx(self.color_name))
            # 从 90° 起顺时针（与桌面版一致）
            Line(circle=(cx, cy, r, 90, 90 - frac * 360), width=10)


class PomodoroApp(App):
    def build(self):
        self.timer = PomodoroTimer()
        self.timer.on_tick = lambda rem, tot: self._refresh()
        self.timer.on_complete = self._on_complete
        self.timer.on_session = lambda c: self._refresh_session()
        self.timer.on_state = self._refresh

        root = BoxLayout(orientation="vertical", spacing=10, padding=18)
        root.bind(size=self._on_root_size)

        # ── 头部 ──
        head = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40)
        title = Label(text="🍅 番茄钟", font_size=20, bold=True,
                      color=hx("text"), halign="left", size_hint=(1, 1))
        title.bind(size=title.setter("text_size"))
        head.add_widget(title)
        btn_set = Button(text="⚙", font_size=20, size_hint=(None, 1), width=44,
                         background_color=hx("surface"), color=hx("subtext"))
        btn_set.bind(on_release=lambda *a: self._open_settings())
        head.add_widget(btn_set)
        root.add_widget(head)

        # ── 模式标签页 ──
        tabs = BoxLayout(orientation="horizontal", size_hint=(1, None), height=44,
                         spacing=4, padding=2)
        tabs.canvas.before.add(Color(*hx("surface")))
        from kivy.graphics import Rectangle
        with tabs.canvas.before:
            Color(*hx("surface"))
            self._tabs_bg = Rectangle(pos=tabs.pos, size=tabs.size)
        tabs.bind(pos=lambda i, v: setattr(self._tabs_bg, "pos", v))
        tabs.bind(size=lambda i, v: setattr(self._tabs_bg, "size", v))
        self.tabs = {}
        for key in ("pomodoro", "short_break", "long_break"):
            b = Button(text=MODE_TEXT[key], font_size=14, bold=True,
                       background_color=hx("surface"), color=hx("subtext"))
            b.bind(on_release=lambda *a, k=key: self.timer.set_mode(k))
            tabs.add_widget(b)
            self.tabs[key] = b
        root.add_widget(tabs)

        # ── 进度环 + 文字 ──
        center = FloatLayout(size_hint=(1, None), height=300)
        self.ring = Ring(size_hint=(1, 1))
        center.add_widget(self.ring)
        self.time_lbl = Label(text="25:00", font_size=52, bold=True,
                              color=hx("red"), size_hint=(1, 1))
        self.status_lbl = Label(text="准备开始", font_size=15,
                                color=hx("subtext"), size_hint=(1, 1),
                                pos_hint={"center_x": 0.5, "center_y": 0.38})
        self.session_lbl = Label(text="今日 0 🍅", font_size=15,
                                 color=hx("subtext"), size_hint=(1, 1),
                                 pos_hint={"center_x": 0.5, "center_y": 0.22})
        center.add_widget(self.time_lbl)
        center.add_widget(self.status_lbl)
        center.add_widget(self.session_lbl)
        root.add_widget(center)

        # ── 控制按钮 ──
        ctrl = BoxLayout(orientation="horizontal", size_hint=(1, None), height=64,
                         spacing=14, padding=(20, 0))
        self.btn_reset = Button(text="↺", font_size=26, color=hx("subtext"),
                                background_color=hx("surface"))
        self.btn_start = Button(text="▶", font_size=30, bold=True, color=hx("white"),
                                background_color=hx("red"))
        self.btn_skip = Button(text="⏭", font_size=26, color=hx("subtext"),
                               background_color=hx("surface"))
        self.btn_reset.bind(on_release=lambda *a: self.timer.reset())
        self.btn_start.bind(on_release=lambda *a: self.timer.toggle())
        self.btn_skip.bind(on_release=lambda *a: self.timer.skip())
        ctrl.add_widget(self.btn_reset)
        ctrl.add_widget(self.btn_start)
        ctrl.add_widget(self.btn_skip)
        root.add_widget(ctrl)

        # ── 任务输入 ──
        self.task_ph = "✏️  当前正在做什么？"
        self.task = TextInput(text=self.task_ph, font_size=15,
                              foreground_color=hx("subtext"),
                              background_color=hx("surface"),
                              cursor_color=hx("text"),
                              size_hint=(1, None), height=44,
                              padding=(10, 10, 10, 10))
        self.task.bind(focus=self._on_task_focus)
        root.add_widget(self.task)

        Clock.schedule_interval(self._update, 0.2)
        self._refresh()
        return root

    # ── 自适应：保持圆环为正方形 ──
    def _on_root_size(self, *a):
        pass

    def _update(self, dt):
        self.timer.tick(dt)

    def _refresh(self):
        t = self.timer
        self.time_lbl.text = t.time_str()
        self.time_lbl.color = hx(
            {"pomodoro": "red", "short_break": "green", "long_break": "blue"}[t.mode]
        )
        self.ring.remaining = t.remaining
        self.ring.total = t.total
        self.ring.color_name = {"pomodoro": "red", "short_break": "green", "long_break": "blue"}[t.mode]
        self.ring.redraw()

        # 状态文字
        if t.running and not t.paused:
            txt = {"pomodoro": "专注中…", "short_break": "休息中…", "long_break": "长休息中…"}[t.mode]
        else:
            txt = {"pomodoro": "准备开始", "short_break": "准备休息", "long_break": "准备长休息"}[t.mode]
        self.status_lbl.text = txt

        # 标签页颜色
        for key, b in self.tabs.items():
            if key == t.mode:
                b.background_color = hx(
                    {"pomodoro": "red", "short_break": "green", "long_break": "blue"}[key]
                )
                b.color = hx("white")
            else:
                b.background_color = hx("surface")
                b.color = hx("subtext")

        # 开始/暂停按钮
        if t.running and not t.paused:
            self.btn_start.text = "⏸"
            self.btn_start.background_color = hx("subtext")
        else:
            self.btn_start.text = "▶"
            self.btn_start.background_color = hx("red")

        self._refresh_session()

    def _refresh_session(self):
        self.session_lbl.text = f"今日 {self.timer.sessions_today} 🍅"

    def _on_complete(self, mode):
        if mode == "pomodoro":
            title = "🍅 番茄完成！休息一下吧～"
        else:
            title = "⏰ 休息结束！继续加油～"
        body = (self.task.text or "").strip()
        if body == self.task_ph:
            body = ""
        if HAS_PLYER:
            try:
                notification.notify(title=title, message=body, app_name="番茄钟")
            except Exception:
                pass
            try:
                vibrator.vibrate(time=0.4)
            except Exception:
                pass

    def _on_task_focus(self, ti, focused):
        if focused and ti.text == self.task_ph:
            ti.text = ""
            ti.foreground_color = hx("text")
        elif not focused and not ti.text.strip():
            ti.text = self.task_ph
            ti.foreground_color = hx("subtext")

    # ── 设置弹窗 ──
    def _open_settings(self):
        view = ModalView(size_hint=(0.9, 0.8), background_color=hx("bg"))
        box = BoxLayout(orientation="vertical", spacing=10, padding=18)
        box.add_widget(Label(text="⚙ 番茄钟设置", font_size=20, bold=True,
                             color=hx("text"), size_hint=(1, None), height=36))

        rows = [
            ("🍅 专注时长（分钟）", "pomodoro", 1, 120),
            ("☕ 短休息（分钟）", "short_break", 1, 30),
            ("🌿 长休息（分钟）", "long_break", 1, 60),
            ("📏 长休息间隔（几个番茄）", "interval", 1, 10),
        ]
        spinners = {}
        for label, key, lo, hi in rows:
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=44, spacing=8)
            row.add_widget(Label(text=label, font_size=14, color=hx("text"),
                                 halign="left", size_hint=(1, 1)))
            row.children[0].bind(size=row.children[0].setter("text_size"))
            cur = self.timer.long_interval if key == "interval" else self.timer.durations[key] // 60
            sp = Spinner(text=str(cur), values=[str(i) for i in range(lo, hi + 1)],
                         size_hint=(None, 1), width=90, background_color=hx("surface2"),
                         color=hx("text"))
            spinners[key] = sp
            row.add_widget(sp)
            box.add_widget(row)

        auto_break = Button(text="🔔 专注结束→自动休息", size_hint=(1, None), height=44,
                            background_color=hx("surface"), color=hx("subtext"))
        auto_pom = Button(text="🔔 休息结束→自动专注", size_hint=(1, None), height=44,
                          background_color=hx("surface"), color=hx("subtext"))

        def toggle_btn(btn, attr):
            val = not getattr(self.timer, attr)
            setattr(self.timer, attr, val)
            btn.background_color = hx("red") if val else hx("surface")
            btn.color = hx("white") if val else hx("subtext")

        auto_break.bind(on_release=lambda *a: toggle_btn(auto_break, "auto_break"))
        auto_pom.bind(on_release=lambda *a: toggle_btn(auto_pom, "auto_pom"))
        if self.timer.auto_break:
            auto_break.background_color = hx("red"); auto_break.color = hx("white")
        if self.timer.auto_pom:
            auto_pom.background_color = hx("red"); auto_pom.color = hx("white")
        box.add_widget(auto_break)
        box.add_widget(auto_pom)

        btns = BoxLayout(orientation="horizontal", size_hint=(1, None), height=48, spacing=10)
        cancel = Button(text="取消", background_color=hx("surface2"), color=hx("subtext"))
        save = Button(text="✓ 保存", background_color=hx("red"), color=hx("white"), bold=True)

        def do_save(*a):
            self.timer.set_settings(
                durations={
                    "pomodoro": int(spinners["pomodoro"].text) * 60,
                    "short_break": int(spinners["short_break"].text) * 60,
                    "long_break": int(spinners["long_break"].text) * 60,
                },
                long_interval=int(spinners["interval"].text),
            )
            self._refresh()
            view.dismiss()

        cancel.bind(on_release=view.dismiss)
        save.bind(on_release=do_save)
        btns.add_widget(cancel)
        btns.add_widget(save)
        box.add_widget(btns)

        view.add_widget(box)
        view.open()


if __name__ == "__main__":
    PomodoroApp().run()
