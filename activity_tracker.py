"""
내 활동 기록기 (Activity Tracker) - Modern UI
--------------------------------------------
활성 창(프로그램)을 자동으로 감지해 사용 시간을 기록합니다.
- 녹화 중에는 실시간으로 프로그램별 사용 시간이 카드 리스트로 표시됨
- 종료 시 로딩 화면을 거쳐 결과 창(도넛 그래프 + 카드 리스트 + 타임라인) 표시
- 창 크기 자유 조절, 나눔스퀘어 폰트 자동 적용(없으면 맑은 고딕 대체)

[사전 설치]
Windows : pip install customtkinter psutil pywin32
macOS   : pip install customtkinter psutil pyobjc

[실행]
python activity_tracker.py
"""

import sys
import os
import time
import ctypes
import threading
import datetime
import platform
from collections import defaultdict

import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
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

COLORS = ["#3B8ED0", "#36B37E", "#F2994A", "#9B51E0", "#EB5757", "#2D9CDB", "#27AE60", "#F2C94C"]

CARD_BG_LIGHT = "#eef0f3"
CARD_BG_DARK = "#242424"

# 기본값: 나눔스퀘어 ttf가 없으면 맑은 고딕으로 대체 (한글 깨짐 방지)
FONT_FAMILY = "맑은 고딕"


def F(size, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def resource_path(*parts):
    """PyInstaller --onefile로 빌드된 exe 안에서도 동작하는 리소스 경로"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def load_custom_fonts():
    """fonts 폴더의 ttf/otf를 설치 없이 이 프로그램에서만 임시로 사용할 수 있게 등록"""
    if OS_NAME != "Windows":
        return
    font_dir = resource_path("fonts")
    if not os.path.isdir(font_dir):
        return
    FR_PRIVATE = 0x10
    for fname in os.listdir(font_dir):
        if fname.lower().endswith((".ttf", ".otf")):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(os.path.join(font_dir, fname), FR_PRIVATE, 0)
            except Exception:
                pass


def resolve_font_family(tk_root):
    """등록된 폰트 중 나눔스퀘어 계열이 있으면 그 이름을 사용, 없으면 기본값 유지"""
    try:
        for fam in tkfont.families(tk_root):
            if "nanumsquare" in fam.lower().replace(" ", ""):
                return fam
    except Exception:
        pass
    return "맑은 고딕"


def current_bg_color():
    return CARD_BG_LIGHT if ctk.get_appearance_mode() == "Light" else CARD_BG_DARK


def current_text_colors():
    if ctk.get_appearance_mode() == "Light":
        return "#2b2b2b", "#7a7a7a"
    return "#f2f2f2", "#9a9a9a"


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
            self.thread.join(timeout=1.5)
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
            # poll_interval을 잘게 쪼개 대기 -> 종료 버튼 눌렀을 때 빠르게 반응
            slept = 0.0
            while slept < self.poll_interval and self.recording:
                time.sleep(0.1)
                slept += 0.1

    def summary_by_app(self):
        totals = defaultdict(float)
        for app, _, start, end in self.log:
            totals[app] += (end - start).total_seconds()
        return dict(sorted(totals.items(), key=lambda x: -x[1]))

    def summary_by_app_live(self):
        """녹화 중 실시간 표시용: 현재 진행 중인 구간의 경과 시간도 포함"""
        totals = defaultdict(float)
        for app, _, start, end in self.log:
            totals[app] += (end - start).total_seconds()
        if self._cur_app is not None and self._cur_start is not None:
            totals[self._cur_app] += (datetime.datetime.now() - self._cur_start).total_seconds()
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


def render_card_rows(container, totals, empty_text="기록된 활동이 없습니다."):
    """카드형 사용 시간 리스트를 그린다 (container 내용을 지우고 다시 그림)"""
    for child in container.winfo_children():
        child.destroy()

    if not totals:
        ctk.CTkLabel(container, text=empty_text, font=F(12), text_color="gray").pack(pady=20)
        return

    total_seconds = sum(totals.values())
    for i, (app, secs) in enumerate(totals.items()):
        ratio = secs / total_seconds if total_seconds else 0
        color = COLORS[i % len(COLORS)]

        card = ctk.CTkFrame(container, corner_radius=16)
        card.pack(fill="x", pady=6, padx=4)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 8))
        dot = ctk.CTkFrame(top, width=10, height=10, corner_radius=5, fg_color=color)
        dot.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top, text=app, font=F(14)).pack(side="left")
        ctk.CTkLabel(top, text=fmt_duration(secs), font=F(14, "bold")).pack(side="right")
        bar = ctk.CTkProgressBar(card, height=16, progress_color=color)
        bar.pack(fill="x", padx=16, pady=(0, 16))
        bar.set(ratio)


def draw_donut_chart(canvas, totals, size=170, thickness_ratio=0.42):
    """한눈에 보는 도넛 그래프. canvas의 bg를 그대로 구멍 색으로 사용."""
    canvas.delete("all")
    cx = cy = size / 2
    radius = size / 2 - 4
    total = sum(totals.values())
    bg = canvas.cget("bg")
    primary, secondary = current_text_colors()

    if total <= 0:
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=secondary, width=3)
        canvas.create_text(cx, cy, text="기록 없음", fill=secondary, font=(FONT_FAMILY, 11))
        return

    start = 90.0
    for i, (app, secs) in enumerate(totals.items()):
        extent = -360.0 * (secs / total)
        color = COLORS[i % len(COLORS)]
        canvas.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=start, extent=extent, fill=color, outline=bg, width=2,
            style=tk.PIESLICE,
        )
        start += extent

    hole_r = radius * thickness_ratio
    canvas.create_oval(cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r, fill=bg, outline=bg)
    canvas.create_text(cx, cy - 9, text="총 사용", fill=secondary, font=(FONT_FAMILY, 10))
    canvas.create_text(cx, cy + 9, text=fmt_duration(total), fill=primary, font=(FONT_FAMILY, 13, "bold"))


class LoadingWindow(ctk.CTkToplevel):
    """종료 버튼을 누른 뒤 결과가 준비될 때까지 보여주는 로딩 창"""

    def __init__(self, master):
        super().__init__(master)
        self.title("")
        self.geometry("260x130")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(self, text="기록을 정리하고 있어요...", font=F(13)).pack(pady=(28, 14))
        bar = ctk.CTkProgressBar(self, width=180, mode="indeterminate")
        bar.pack()
        try:
            bar.start()
        except Exception:
            pass

        self.update_idletasks()
        self._center_on(master)
        try:
            self.grab_set()
        except Exception:
            pass

    def _center_on(self, master):
        try:
            mx, my = master.winfo_x(), master.winfo_y()
            mw, mh = master.winfo_width(), master.winfo_height()
            w, h = 260, 130
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        global FONT_FAMILY
        FONT_FAMILY = resolve_font_family(self)

        self.title("활동 기록기")
        self.geometry("380x520")
        self.minsize(320, 380)
        self.resizable(True, True)

        self.tracker = ActivityTracker(poll_interval=2.0)
        self.start_time = None
        self.loading_win = None

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(pady=(20, 6))

        ctk.CTkLabel(self.header, text="활동 기록기", font=F(20, "bold")).pack(pady=(0, 2))
        ctk.CTkLabel(
            self.header, text="사용한 프로그램을 자동으로 기록해요",
            font=F(11), text_color="gray"
        ).pack(pady=(0, 16))

        self.record_btn = ctk.CTkButton(
            self.header, text="●\n시작", width=110, height=110, corner_radius=55,
            font=F(14, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self.toggle_recording,
        )
        self.record_btn.pack(pady=6)

        self.status_label = ctk.CTkLabel(self.header, text="대기 중", font=F(13))
        self.status_label.pack(pady=(14, 2))

        self.timer_label = ctk.CTkLabel(self.header, text="00:00:00", font=F(20, "bold"))
        self.timer_label.pack(pady=(0, 4))

        # 녹화 중에만 나타나는 실시간 사용 현황
        self.live_label = ctk.CTkLabel(self, text="실시간 사용 현황", font=F(12, "bold"), text_color="gray")
        self.live_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick()

    def toggle_recording(self):
        if not self.tracker.recording:
            self.tracker.start()
            self.start_time = datetime.datetime.now()
            self.status_label.configure(text="🔴 기록 중...")
            self.record_btn.configure(text="■\n종료", fg_color=RECORD, hover_color=RECORD_HOVER)

            self.live_label.pack(pady=(4, 2))
            self.live_scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))
            render_card_rows(self.live_scroll, {}, empty_text="측정 준비 중...")
        else:
            self.record_btn.configure(state="disabled")
            self.status_label.configure(text="정리 중...")
            self.loading_win = LoadingWindow(self)
            threading.Thread(target=self._stop_worker, daemon=True).start()

    def _stop_worker(self):
        self.tracker.stop()
        self.after(0, self._on_stopped)

    def _on_stopped(self):
        if self.loading_win is not None:
            try:
                self.loading_win.destroy()
            except Exception:
                pass
            self.loading_win = None

        self.status_label.configure(text="대기 중")
        self.record_btn.configure(text="●\n시작", fg_color=ACCENT, hover_color=ACCENT_HOVER, state="normal")
        self.timer_label.configure(text="00:00:00")

        self.live_scroll.pack_forget()
        self.live_label.pack_forget()

        self.show_result()

    def _tick(self):
        if self.tracker.recording and self.start_time:
            total = int((datetime.datetime.now() - self.start_time).total_seconds())
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            self.timer_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
            render_card_rows(self.live_scroll, self.tracker.summary_by_app_live(), empty_text="측정 중...")
        self.after(1000, self._tick)

    def on_close(self):
        if self.tracker.recording:
            self.tracker.stop()
        self.destroy()

    def show_result(self):
        win = ResultWindow(self, self.tracker)
        win.grab_set()


class ResultWindow(ctk.CTkToplevel):
    def __init__(self, master, tracker):
        super().__init__(master)
        self.title("활동 기록 결과")
        self.geometry("420x680")
        self.minsize(340, 460)
        self.resizable(True, True)
        self.tracker = tracker

        self.totals = tracker.summary_by_app()
        self.total_seconds = sum(self.totals.values())

        ctk.CTkLabel(self, text="오늘의 사용 기록", font=F(18, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(
            self,
            text=f"총 기록 시간 {fmt_duration(self.total_seconds)}" if self.total_seconds else "기록된 활동이 없어요",
            font=F(12), text_color="gray"
        ).pack(pady=(0, 10))

        tabs = ctk.CTkTabview(self)
        tabs.pack(padx=16, pady=(0, 12), fill="both", expand=True)
        tab_summary = tabs.add("요약")
        tab_timeline = tabs.add("타임라인")
        try:  # 탭 버튼 글씨도 한글 폰트로 (비공식 내부 속성이라 실패해도 무시)
            tabs._segmented_button.configure(font=F(12))
        except Exception:
            pass

        self._build_summary_tab(tab_summary)
        self._build_timeline_tab(tab_timeline)

        ctk.CTkButton(self, text="텍스트 파일로 저장", font=F(13), command=self.save_result).pack(pady=(4, 20))

    def _build_summary_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 한눈에 보는 도넛 그래프
        chart_size = 170
        chart_frame = ctk.CTkFrame(scroll, fg_color=(CARD_BG_LIGHT, CARD_BG_DARK), corner_radius=20)
        chart_frame.pack(pady=(10, 16))
        canvas = tk.Canvas(chart_frame, width=chart_size, height=chart_size, bg=current_bg_color(), highlightthickness=0)
        canvas.pack(padx=18, pady=18)
        draw_donut_chart(canvas, self.totals, size=chart_size)

        # 카드형 리스트
        render_card_rows(scroll, self.totals)

    def _build_timeline_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        entries = self.tracker.timeline_entries()
        if not entries:
            ctk.CTkLabel(scroll, text="기록된 활동이 없습니다.", font=F(12), text_color="gray").pack(pady=20)
            return

        for app, start, end in entries:
            dur = (end - start).total_seconds()
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(
                row, text=f"{start.strftime('%H:%M:%S')} ~ {end.strftime('%H:%M:%S')}",
                font=F(11), text_color="gray"
            ).pack(side="left")
            ctk.CTkLabel(row, text=f"{app}  ({fmt_duration(dur)})", font=F(12)).pack(side="right")

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
    load_custom_fonts()
    app = App()
    app.mainloop()
