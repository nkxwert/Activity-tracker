"""
내 활동 기록기 (Activity Tracker) - Modern UI
--------------------------------------------
활성 창(프로그램)을 자동으로 감지해 사용 시간을 기록합니다.
녹화 버튼 하나로 시작/종료, 결과는 요약 + 타임라인 탭으로 표시.

[사전 설치]
Windows : pip install customtkinter psutil pywin32
macOS   : pip install customtkinter psutil pyobjc

[실행]
python activity_tracker.py
"""

import sys
import time
import threading
import datetime
import platform
from collections import defaultdict

import customtkinter as ctk
from tkinter import filedialog, messagebox

OS_NAME = platform.system()

if OS_NAME == "Windows":
    try:
        import psutil
        import win32gui
        import win32process
    except ImportError:
        print("필요한 패키지가 없습니다. 아래 명령어로 설치하세요:\n\n    pip install customtkinter pywin32 psutil\n")
        sys.exit(1)
elif OS_NAME == "Darwin":
    try:
        import psutil
        from AppKit import NSWorkspace
    except ImportError:
        print("필요한 패키지가 없습니다. 아래 명령어로 설치하세요:\n\n    pip install customtkinter pyobjc psutil\n")
        sys.exit(1)
else:
    print("현재 Windows / macOS만 지원합니다.")
    sys.exit(1)

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

ACCENT = "#3B8ED0"
ACCENT_HOVER = "#2f6f9e"
RECORD = "#e74c3c"
RECORD_HOVER = "#c0392b"


def get_active_window_info():
    """현재 활성 창의 (프로그램 이름, 창 제목)을 반환한다."""
    try:
        if OS_NAME == "Windows":
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None, None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                app_name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "알 수 없음"
            title = win32gui.GetWindowText(hwnd) or ""
            return app_name, title
        else:  # macOS
            active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            app_name = active_app.localizedName() if active_app else "알 수 없음"
            return app_name, app_name
    except Exception:
        return None, None


class ActivityTracker:
    """poll_interval(초)마다 활성 창을 확인해 사용 구간을 기록."""

    def __init__(self, poll_interval=2.0):
        self.poll_interval = poll_interval
        self.recording = False
        self.thread = None
        self.log = []  # (app, title, start, end)
        self._cur_app = None
        self._cur_title = None
        self._cur_start = None

    def start(self):
        self.log = []
        self._cur_app = None
        self._cur_start = None
        self.recording = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.recording = False
        if self.thread:
            self.thread.join(timeout=self.poll_interval + 1)
        self._flush(datetime.datetime.now())

    def _flush(self, end_time):
        if self._cur_app is not None and self._cur_start is not None:
            self.log.append((self._cur_app, self._cur_title, self._cur_start, end_time))
        self._cur_app = None
        self._cur_title = None
        self._cur_start = None

    def _run(self):
        while self.recording:
            now = datetime.datetime.now()
            app_name, title = get_active_window_info()
            if app_name and app_name != self._cur_app:
                self._flush(now)
                self._cur_app, self._cur_title, self._cur_start = app_name, title, now
            time.sleep(self.poll_interval)

    def summary_by_app(self):
        totals = defaultdict(float)
        for app, _, start, end in self.log:
            totals[app] += (end - start).total_seconds()
        return dict(sorted(totals.items(), key=lambda x: -x[1]))

    def timeline_entries(self):
        return [(a, s, e) for a, _, s, e in self.log if (e - s).total_seconds() >= 1]


def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}시간 {m}분 {s}초"
    if m:
        return f"{m}분 {s}초"
    return f"{s}초"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("활동 기록기")
        self.geometry("360x420")
        self.resizable(False, False)

        self.tracker = ActivityTracker(poll_interval=2.0)
        self.start_time = None

        ctk.CTkLabel(self, text="활동 기록기", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 4))
        ctk.CTkLabel(
            self, text="사용한 프로그램을 자동으로 기록해요",
            font=ctk.CTkFont(size=12), text_color="gray"
        ).pack(pady=(0, 30))

        self.record_btn = ctk.CTkButton(
            self, text="●\n시작", width=140, height=140, corner_radius=70,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self.toggle_recording,
        )
        self.record_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="대기 중", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=(20, 2))

        self.timer_label = ctk.CTkLabel(self, text="00:00:00", font=ctk.CTkFont(size=24, weight="bold"))
        self.timer_label.pack()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick()

    def toggle_recording(self):
        if not self.tracker.recording:
            self.tracker.start()
            self.start_time = datetime.datetime.now()
            self.status_label.configure(text="🔴 기록 중...")
            self.record_btn.configure(text="■\n종료", fg_color=RECORD, hover_color=RECORD_HOVER)
        else:
            self.tracker.stop()
            self.status_label.configure(text="대기 중")
            self.record_btn.configure(text="●\n시작", fg_color=ACCENT, hover_color=ACCENT_HOVER)
            self.timer_label.configure(text="00:00:00")
            self.show_result()

    def _tick(self):
        if self.tracker.recording and self.start_time:
            total = int((datetime.datetime.now() - self.start_time).total_seconds())
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            self.timer_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        self.after(1000, self._tick)

    def on_close(self):
        if self.tracker.recording:
            self.tracker.stop()
        self.destroy()

    def show_result(self):
        win = ResultWindow(self, self.tracker)
        win.grab_set()


class ResultWindow(ctk.CTkToplevel):
    COLORS = ["#3B8ED0", "#36B37E", "#F2994A", "#9B51E0", "#EB5757", "#2D9CDB", "#27AE60", "#F2C94C"]

    def __init__(self, master, tracker):
        super().__init__(master)
        self.title("활동 기록 결과")
        self.geometry("420x560")
        self.tracker = tracker

        self.totals = tracker.summary_by_app()
        self.total_seconds = sum(self.totals.values())

        ctk.CTkLabel(self, text="오늘의 사용 기록", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(
            self,
            text=f"총 기록 시간 {fmt_duration(self.total_seconds)}" if self.total_seconds else "기록된 활동이 없어요",
            font=ctk.CTkFont(size=12), text_color="gray"
        ).pack(pady=(0, 16))

        tabs = ctk.CTkTabview(self, width=380, height=350)
        tabs.pack(padx=16, pady=(0, 12), fill="both", expand=True)
        self._build_summary_tab(tabs.add("요약"))
        self._build_timeline_tab(tabs.add("타임라인"))

        ctk.CTkButton(self, text="텍스트 파일로 저장", command=self.save_result).pack(pady=(4, 20))

    def _build_summary_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if not self.totals:
            ctk.CTkLabel(scroll, text="기록된 활동이 없습니다.", text_color="gray").pack(pady=20)
            return

        for i, (app, secs) in enumerate(self.totals.items()):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=6, padx=4)
            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=app, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            ctk.CTkLabel(top, text=fmt_duration(secs), font=ctk.CTkFont(size=12), text_color="gray").pack(side="right")

            ratio = secs / self.total_seconds if self.total_seconds else 0
            bar = ctk.CTkProgressBar(row, height=8, progress_color=self.COLORS[i % len(self.COLORS)])
            bar.pack(fill="x", pady=(6, 0))
            bar.set(ratio)

    def _build_timeline_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        entries = self.tracker.timeline_entries()
        if not entries:
            ctk.CTkLabel(scroll, text="기록된 활동이 없습니다.", text_color="gray").pack(pady=20)
            return

        for app, start, end in entries:
            dur = (end - start).total_seconds()
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(
                row, text=f"{start.strftime('%H:%M:%S')} ~ {end.strftime('%H:%M:%S')}",
                font=ctk.CTkFont(size=11), text_color="gray"
            ).pack(side="left")
            ctk.CTkLabel(row, text=f"{app}  ({fmt_duration(dur)})", font=ctk.CTkFont(size=12)).pack(side="right")

    def save_result(self):
        lines = ["[프로그램별 총 사용 시간]"]
        if self.totals:
            for app, secs in self.totals.items():
                lines.append(f"  {app} : {fmt_duration(secs)}")
        else:
            lines.append("  기록된 활동이 없습니다.")
        lines.append("")
        lines.append("[타임라인]")
        entries = self.tracker.timeline_entries()
        if entries:
            for app, start, end in entries:
                dur = (end - start).total_seconds()
                lines.append(f"{start.strftime('%H:%M:%S')} ~ {end.strftime('%H:%M:%S')}  ({fmt_duration(dur)})  -  {app}")
        else:
            lines.append("  (기록 없음)")
        text = "\n".join(lines)

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt")],
            initialfile=f"활동기록_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("저장 완료", f"저장되었습니다:\n{path}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
