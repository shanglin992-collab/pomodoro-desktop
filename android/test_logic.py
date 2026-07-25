import sys, os, shutil
sys.path.insert(0, os.path.dirname(__file__))
from timer_core import PomodoroTimer

completes = []
sessions = []

t = PomodoroTimer(app_dir="./_test_home")
t.on_tick = lambda r, tot: None
t.on_complete = lambda mode: completes.append(mode)
t.on_session = lambda c: sessions.append(c)

# 用很短的时长加速测试
t.durations = {"pomodoro": 2, "short_break": 2, "long_break": 2}
t.long_interval = 4
t.auto_break = True
t.auto_pom = False
t._reset_current()

# 逐段推进，直到累计完成 4 个番茄；记录每次番茄完成后的下一段模式
transitions = []
pomodoro_count = 0
while pomodoro_count < 4:
    if not t.running:
        t.start()
    before = t.mode
    t.tick(t.remaining + 0.5)        # 把当前段跑完
    if before == "pomodoro":
        pomodoro_count += 1
        transitions.append(t.mode)    # 该番茄结束后的下一段

print("专注完成次数:", completes.count("pomodoro"))
print("今日会话数:", t.sessions_today)
print("每段番茄后的下一段模式:", transitions)

assert t.sessions_today == 4, "应有 4 个番茄"
assert completes.count("pomodoro") == 4, "应有 4 次专注完成"
assert transitions == ["short_break", "short_break", "short_break", "long_break"], transitions

# set_mode 切到长休会清零 streak
t.set_mode("long_break")
assert t.streak == 0

# 长休中 skip → 回到专注
t.skip()
assert t.mode == "pomodoro", t.mode

# auto_pom=False：短休结束后不应自动开始专注
t.set_mode("short_break")
t._reset_current()
t.start()
t.tick(t.remaining + 0.5)
assert t.mode == "pomodoro", t.mode
assert t.running is False, "auto_pom 关闭时休息结束不应自动开始专注"

# auto_pom=True：短休结束应自动开始专注
t.auto_pom = True
t.set_mode("short_break")
t._reset_current()
t.start()
t.tick(t.remaining + 0.5)
assert t.mode == "pomodoro" and t.running is True, "auto_pom 开启时应自动开始专注"

print("\n✅ 全部断言通过：核心逻辑与桌面版一致")
shutil.rmtree("./_test_home", ignore_errors=True)
