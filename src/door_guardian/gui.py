"""Tkinter desktop interface for Smart Door Guardian."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from .access import AccessCodeError, AccessCodeStore
from .audit import AuditLog
from .config import Settings
from .face import FaceService, FaceServiceError, RecognitionResult
from .notifier import EmailNotifier, NotificationError
from .speech import Speaker
from .weather import WeatherService


class DoorGuardianApp:
    def __init__(self, settings: Settings) -> None:
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        self.tk = tk
        self.messagebox = messagebox
        self.simpledialog = simpledialog
        self.settings = settings
        self.access = AccessCodeStore(
            settings.access_code_path, settings.initial_access_code
        )
        self.audit = AuditLog(settings.audit_log_path)
        self.face = FaceService(settings)
        self.notifier = EmailNotifier(settings)
        self.speaker = Speaker()
        self.weather = WeatherService(settings)

        self.root = tk.Tk()
        self.root.title("智能门神 · Smart Door Guardian")
        self.root.geometry("860x560")
        self.root.minsize(760, 500)
        self.root.configure(bg="#101827")

        self.status = tk.StringVar(value="系统就绪")
        self._buttons: list[Any] = []
        self._build_ui()

    def _build_ui(self) -> None:
        tk = self.tk
        header = tk.Frame(self.root, bg="#172238", padx=28, pady=24)
        header.pack(fill="x")
        tk.Label(
            header,
            text="智能门神",
            font=("Microsoft YaHei UI", 27, "bold"),
            fg="#f8fafc",
            bg="#172238",
        ).pack(anchor="w")
        subtitle = "演示模式" if self.settings.demo_mode else "生产模式"
        tk.Label(
            header,
            text=f"人脸门禁 · 访问码回退 · 离家天气 · 异常邮件  |  {subtitle}",
            font=("Microsoft YaHei UI", 11),
            fg="#93a4bd",
            bg="#172238",
        ).pack(anchor="w", pady=(8, 0))

        body = tk.Frame(self.root, bg="#101827", padx=28, pady=28)
        body.pack(fill="both", expand=True)
        actions = [
            ("回家 / 身份验证", self.handle_arrival, "#16a34a"),
            ("出门 / 天气提醒", self.handle_departure, "#2563eb"),
            ("添加人脸用户", self.handle_add_user, "#7c3aed"),
            ("修改访问码", self.handle_change_code, "#c2410c"),
            ("查看最近事件", self.handle_recent_events, "#334155"),
        ]
        for index, (label, command, color) in enumerate(actions):
            button = tk.Button(
                body,
                text=label,
                command=command,
                font=("Microsoft YaHei UI", 13, "bold"),
                fg="white",
                bg=color,
                activeforeground="white",
                activebackground=color,
                relief="flat",
                cursor="hand2",
                padx=18,
                pady=16,
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=8,
                pady=8,
            )
            self._buttons.append(button)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        footer = tk.Label(
            self.root,
            textvariable=self.status,
            anchor="w",
            font=("Microsoft YaHei UI", 10),
            fg="#cbd5e1",
            bg="#172238",
            padx=28,
            pady=14,
        )
        footer.pack(fill="x", side="bottom")

    def _set_busy(self, busy: bool, message: str) -> None:
        self.status.set(message)
        state = "disabled" if busy else "normal"
        for button in self._buttons:
            button.configure(state=state)

    def _run_task(
        self,
        message: str,
        task: Callable[[], Any],
        callback: Callable[[Any], None],
    ) -> None:
        self._set_busy(True, message)

        def runner() -> None:
            try:
                result: Any = task()
            except Exception as exc:  # UI boundary: report without crashing the app.
                result = exc
            self.root.after(0, lambda: self._finish_task(result, callback))

        threading.Thread(target=runner, daemon=True).start()

    def _finish_task(self, result: Any, callback: Callable[[Any], None]) -> None:
        self._set_busy(False, "系统就绪")
        callback(result)

    def _speak_async(self, text: str) -> None:
        threading.Thread(target=self.speaker.speak, args=(text,), daemon=True).start()

    def handle_arrival(self) -> None:
        if not self.face.ready:
            self._pin_fallback("尚未训练人脸模型，请使用访问码。")
            return
        self._run_task("正在打开摄像头识别身份……", self.face.recognize, self._arrival_done)

    def _arrival_done(self, result: Any) -> None:
        if isinstance(result, Exception):
            self._pin_fallback(str(result))
            return
        assert isinstance(result, RecognitionResult)
        if result.granted:
            name = result.name or "授权用户"
            self.audit.record("access_granted", method="face", user=name)
            self.messagebox.showinfo("欢迎回家", f"身份验证成功：{name}")
            self._speak_async(f"欢迎回家，{name}")
        else:
            self._pin_fallback(result.reason)

    def _pin_fallback(self, reason: str) -> None:
        code = self.simpledialog.askstring(
            "访问码验证", f"{reason}\n请输入访问码：", show="*", parent=self.root
        )
        if code is None:
            return
        if self.access.verify(code):
            self.audit.record("access_granted", method="code")
            self.messagebox.showinfo("欢迎回家", "访问码验证成功。")
            self._speak_async("欢迎回家")
            return
        self.audit.record("access_denied", reason=reason)
        self.messagebox.showerror("拒绝访问", "身份验证失败。")
        self._speak_async("抱歉，您没有访问权限")
        threading.Thread(target=self._notify_denied, args=(reason,), daemon=True).start()

    def _notify_denied(self, reason: str) -> None:
        try:
            self.notifier.send_intruder_alert(reason)
        except NotificationError as exc:
            error_message = str(exc)
            self.root.after(
                0,
                lambda: self.status.set(f"邮件告警失败：{error_message}"),
            )

    def handle_departure(self) -> None:
        self.audit.record("departure")
        self._run_task("正在获取天气……", self.weather.current, self._departure_done)

    def _departure_done(self, result: Any) -> None:
        if isinstance(result, Exception):
            message = f"已记录出门事件。天气获取失败：{result}"
        else:
            message = f"一路顺风！\n{result.sentence()}"
        self.messagebox.showinfo("出门提醒", message)
        self._speak_async(message)

    def handle_add_user(self) -> None:
        name = self.simpledialog.askstring(
            "添加用户", "请输入用户名称：", parent=self.root
        )
        if not name:
            return
        samples = self.simpledialog.askinteger(
            "采集数量",
            "采集多少张人脸样本？",
            initialvalue=80,
            minvalue=10,
            maxvalue=300,
            parent=self.root,
        )
        if not samples:
            return

        def collect_and_train() -> tuple[int, int, int]:
            collected = self.face.collect(name, samples)
            if collected == 0:
                raise FaceServiceError("未采集到人脸样本，已取消训练。")
            users, total = self.face.train()
            return collected, users, total

        self._run_task("正在采集人脸；按 Esc 或 Q 可提前结束……", collect_and_train, self._add_done)

    def _add_done(self, result: Any) -> None:
        if isinstance(result, Exception):
            self.messagebox.showerror("添加失败", str(result))
            return
        collected, users, total = result
        self.audit.record("face_user_added", samples=collected)
        self.messagebox.showinfo(
            "训练完成", f"本次采集 {collected} 张；模型包含 {users} 位用户、{total} 张样本。"
        )

    def handle_change_code(self) -> None:
        current = self.simpledialog.askstring(
            "修改访问码", "当前访问码：", show="*", parent=self.root
        )
        if current is None:
            return
        new = self.simpledialog.askstring(
            "修改访问码", "新访问码（至少 6 位）：", show="*", parent=self.root
        )
        if new is None:
            return
        try:
            self.access.change(current, new)
        except AccessCodeError as exc:
            self.messagebox.showerror("修改失败", str(exc))
            return
        self.audit.record("access_code_changed")
        self.messagebox.showinfo("修改成功", "访问码已安全更新。")

    def handle_recent_events(self) -> None:
        events = self.audit.recent(15)
        if not events:
            text = "暂无事件。"
        else:
            text = "\n".join(
                f"{item.get('timestamp', '')}  {item.get('event', '')}" for item in events
            )
        self.messagebox.showinfo("最近事件", text)

    def run(self) -> None:
        self.audit.record("application_started", demo_mode=self.settings.demo_mode)
        self.root.mainloop()


def run_gui(settings: Settings) -> None:
    try:
        DoorGuardianApp(settings).run()
    except FaceServiceError as exc:
        raise RuntimeError(str(exc)) from exc
