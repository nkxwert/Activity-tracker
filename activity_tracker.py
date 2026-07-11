"""
내 활동 기록기 (Activity Tracker)
--------------------------------
'녹화 시작'을 누르면 활성 창(프로그램)을 주기적으로 확인해서
언제 어떤 프로그램을 사용했는지 기록하고, '종료'를 누르면
프로그램별 사용 시간 + 타임라인을 보여줍니다.

[사전 설치]
Windows : pip install pywin32 psutil
macOS   : pip install pyobjc psutil

[실행]
python activity_tracker.py
"""

import sys
import time
import threading
import datetime
import platform
from collections import defaultdict

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

OS_NAME = platform.system()

if OS_NAME == "Windows":
    try:
        import psutil
        import win32gui
        import win32process
    except ImportError:
        print("필요한 패키지가 없습니다. 아래 명령어로 설치하세요:\n\n    pip install pywin32 psutil\n")
        sys.exit(1)
elif OS_NAME == "Darwin":
    try:
        import psutil
        from AppKit import NSWorkspace
    except ImportError:
        print("필요한 패키지가 없습니다. 아래 명령어로 설치하세요:\n\n    pip install pyobjc psutil\n")
        sys.exit(1)
else:
    print("현재 Windows / macOS만 지원합니다.")
    sys.exit(1)


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

    def timeline_text(self):
        lines = []
        for app, title, start, end in self.log:
            dur = (end - start).total_seconds()
            if dur < 1:
                continue
            lines.append(f"{start.strftime('%H:%M:%S')} ~ {end.strftime('%H:%M:%S')}  ({fmt_duration(dur)})  -  {app}")
        return "\n".join(lines)


def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}시간 {m}분 {s}초"
    if m:
        return f"{m}분 {s}초"
    return f"{s}초"


class App:
    def __init__(self, root):
        self.root = root
        root.title("내 활동 기록기")
        root.geometry("360x150")
        root.resizable(False, False)

        self.tracker = ActivityTracker(poll_interval=2.0)
        self.start_time = None

        self.status_label = tk.Label(root, text="대기 중", font=("맑은 고딕", 12))
        self.status_label.pack(pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        self.start_btn = tk.Button(btn_frame, text="● 녹화 시작", width=14, command=self.start_recording)
        self.start_btn.grid(row=0, column=0, padx=5)
        self.stop_btn = tk.Button(btn_frame, text="■ 종료", width=14, command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.timer_label = tk.Label(root, text="", font=("맑은 고딕", 10), fg="#555")
        self.timer_label.pack(pady=5)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick()

    def start_recording(self):
        self.tracker.start()
        self.start_time = datetime.datetime.now()
        self.status_label.config(text="🔴 녹화 중...")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_recording(self):
        self.tracker.stop()
        self.status_label.config(text="대기 중")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.show_result()

    def _tick(self):
        if self.tracker.recording and self.start_time:
            elapsed = str(datetime.datetime.now() - self.start_time).split(".")[0]
            self.timer_label.config(text=f"경과 시간: {elapsed}")
        self.root.after(1000, self._tick)

    def on_close(self):
        if self.tracker.recording:
            self.tracker.stop()
        self.root.destroy()

    def show_result(self):
        win = tk.Toplevel(self.root)
        win.title("활동 기록 결과")
        win.geometry("480x420")

        totals = self.tracker.summary_by_app()
        lines = ["[프로그램별 총 사용 시간]"]
        if totals:
            for app, secs in totals.items():
                lines.append(f"  {app} : {fmt_duration(secs)}")
        else:
            lines.append("  기록된 활동이 없습니다.")
        lines.append("")
        lines.append("[타임라인]")
        timeline = self.tracker.timeline_text() or "  (기록 없음)"
        full_text = "\n".join(lines) + "\n" + timeline

        text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("맑은 고딕", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        text_area.insert(tk.END, full_text)
        text_area.config(state=tk.DISABLED)

        save_btn = tk.Button(win, text="텍스트 파일로 저장", command=lambda: self.save_result(full_text))
        save_btn.pack(pady=10)

    def save_result(self, text):
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
    root = tk.Tk()
    App(root)
    root.mainloop()
