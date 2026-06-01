"""Siri-style overlay shown when Jarvis wakes up and listens."""

from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont

import config


class JarvisUI:
    """Always-on-top overlay with animated orb; thread-safe updates via a queue."""

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._visible = False
        self._state = "idle"
        self._pulse_phase = 0.0
        self._anim_job: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_ui_loop, daemon=True)
        self._thread.start()

    def show(self, state: str = "listening", subtitle: str = "") -> None:
        self._queue.put(("show", state, subtitle))

    def hide(self) -> None:
        self._queue.put(("hide",))

    def set_status(self, title: str, subtitle: str = "") -> None:
        self._queue.put(("status", title, subtitle))

    def shutdown(self) -> None:
        self._queue.put(("quit",))

    def _run_ui_loop(self) -> None:
        self._root = tk.Tk()
        root = self._root
        root.withdraw()
        root.title("Jarvis")
        root.configure(bg=config.UI_BG_COLOR)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", config.UI_WINDOW_ALPHA)

        width, height = config.UI_WIDTH, config.UI_HEIGHT
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = screen_h - height - config.UI_BOTTOM_MARGIN
        root.geometry(f"{width}x{height}+{x}+{y}")

        self._canvas = tk.Canvas(
            root,
            width=width,
            height=height,
            bg=config.UI_BG_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._title_font = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self._sub_font = tkfont.Font(family="Segoe UI", size=11)

        pad = 20
        self._title_id = self._canvas.create_text(
            width // 2,
            height - pad - 28,
            text="",
            fill=config.UI_TEXT_COLOR,
            font=self._title_font,
        )
        self._subtitle_id = self._canvas.create_text(
            width // 2,
            height - pad - 8,
            text="",
            fill=config.UI_SUBTEXT_COLOR,
            font=self._sub_font,
        )

        self._orb_center = (width // 2, height // 2 - 18)
        self._ring_ids: list[int] = []
        self._core_id: int | None = None

        root.bind("<Escape>", lambda _e: self.hide())
        self._poll_queue()
        root.mainloop()

    def _poll_queue(self) -> None:
        if not self._root:
            return
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self._root.after(40, self._poll_queue)

    def _handle_message(self, msg: tuple) -> None:
        if not self._root:
            return
        kind = msg[0]
        if kind == "quit":
            self._stop_animation()
            self._root.quit()
            return
        if kind == "hide":
            self._visible = False
            self._state = "idle"
            self._stop_animation()
            self._root.withdraw()
            return
        if kind == "show":
            _, state, subtitle = msg
            self._visible = True
            self._state = state
            self._root.deiconify()
            self._root.lift()
            self._apply_state_labels(state, subtitle)
            self._start_animation()
            return
        if kind == "status":
            _, title, subtitle = msg
            self._canvas.itemconfigure(self._title_id, text=title)
            self._canvas.itemconfigure(self._subtitle_id, text=subtitle)

    def _apply_state_labels(self, state: str, subtitle: str) -> None:
        labels = {
            "listening": ("Listening…", subtitle or f'Say a command after "{config.WAKE_WORD}"'),
            "processing": ("Thinking…", subtitle),
            "speaking": ("Jarvis", subtitle),
            "error": ("Didn't catch that", subtitle or "Try again"),
        }
        title, sub = labels.get(state, ("Jarvis", subtitle))
        self._canvas.itemconfigure(self._title_id, text=title)
        self._canvas.itemconfigure(self._subtitle_id, text=sub or "")

    def _start_animation(self) -> None:
        self._stop_animation()
        self._pulse_phase = 0.0
        self._animate()

    def _stop_animation(self) -> None:
        if self._root and self._anim_job:
            self._root.after_cancel(self._anim_job)
            self._anim_job = None
        for ring_id in self._ring_ids:
            self._canvas.delete(ring_id)
        self._ring_ids.clear()
        if self._core_id is not None:
            self._canvas.delete(self._core_id)
            self._core_id = None

    def _animate(self) -> None:
        if not self._root or not self._visible:
            return

        cx, cy = self._orb_center
        self._pulse_phase += 0.12
        speed = 1.0 if self._state == "listening" else 0.55

        for ring_id in self._ring_ids:
            self._canvas.delete(ring_id)
        self._ring_ids.clear()
        if self._core_id is not None:
            self._canvas.delete(self._core_id)

        for i in range(3):
            phase = self._pulse_phase * speed + i * (2 * math.pi / 3)
            radius = 28 + 10 * math.sin(phase) + i * 14
            alpha_ring = max(0.15, 0.55 - i * 0.15)
            color = self._blend_toward_bg(config.UI_ACCENT_COLOR, alpha_ring)
            ring = self._canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=color,
                width=2,
            )
            self._ring_ids.append(ring)

        core_r = 16 + 3 * math.sin(self._pulse_phase * speed * 1.4)
        self._core_id = self._canvas.create_oval(
            cx - core_r,
            cy - core_r,
            cx + core_r,
            cy + core_r,
            fill=config.UI_ACCENT_COLOR,
            outline=config.UI_GLOW_COLOR,
            width=2,
        )

        self._anim_job = self._root.after(50, self._animate)

    @staticmethod
    def _blend_toward_bg(hex_color: str, strength: float) -> str:
        """Approximate a dimmer accent on the dark background."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        bg = config.UI_BG_COLOR
        br = int(bg[1:3], 16)
        bg_g = int(bg[3:5], 16)
        bb = int(bg[5:7], 16)
        t = max(0.0, min(1.0, strength))
        return f"#{int(r * t + br * (1 - t)):02x}{int(g * t + bg_g * (1 - t)):02x}{int(b * t + bb * (1 - t)):02x}"


class NullUI:
    """No-op UI when the overlay is disabled."""

    def start(self) -> None:
        pass

    def show(self, state: str = "listening", subtitle: str = "") -> None:
        pass

    def hide(self) -> None:
        pass

    def set_status(self, title: str, subtitle: str = "") -> None:
        pass

    def shutdown(self) -> None:
        pass


def create_ui() -> JarvisUI | NullUI:
    if config.ENABLE_WAKE_UI:
        return JarvisUI()
    return NullUI()
