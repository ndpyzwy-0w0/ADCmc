"""ADCmc — controllable mouse auto-clicker for Windows."""

from __future__ import annotations

import ctypes
import json
import math
import random
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from pynput import keyboard, mouse
from pynput.mouse import Button, Controller as MouseController

APP_TITLE = "ADCmc 连点器"
VERSION = "1.8.2"
SETTINGS_FILE = "ADCmc_settings.txt"

# Set by enable_dpi_awareness() — Windows display scale vs 100%
UI_SCALE = 1.0


def enable_dpi_awareness() -> float:
    """Make the process DPI-aware so UI isn't blurry on scaled displays."""
    global UI_SCALE
    scale = 1.0
    if sys.platform == "win32":
        try:
            # 2 = PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        try:
            dpi = int(ctypes.windll.user32.GetDpiForSystem())
            scale = max(1.0, dpi / 96.0)
        except Exception:
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, 88))  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                scale = max(1.0, dpi / 96.0)
            except Exception:
                scale = 1.0
    UI_SCALE = scale
    return scale


def S(px: int | float) -> int:
    """Scale a design pixel size by display DPI."""
    return max(1, int(round(float(px) * UI_SCALE)))


def apply_tk_scaling(root: tk.Tk) -> None:
    """Map 1 typographic point to the real screen DPI (fixes fuzzy / wrong size)."""
    # points are 1/72"; pixels_per_point = DPI/72
    try:
        dpi = 96.0 * UI_SCALE
        if sys.platform == "win32":
            try:
                root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                if hwnd:
                    dpi = float(ctypes.windll.user32.GetDpiForWindow(hwnd))
            except Exception:
                pass
        root.tk.call("tk", "scaling", max(1.0, dpi / 72.0))
    except tk.TclError:
        pass


# Visual system — graphite console with teal / amber accents (not purple)
class C:
    BG = "#0e1318"
    CARD = "#171e26"
    CARD_ALT = "#1c2530"
    LINE = "#2a3542"
    TEXT = "#e8eef5"
    MUTED = "#8090a0"
    DIM = "#5a6a7a"
    INPUT = "#0b1014"
    TEAL = "#2ec4b6"
    TEAL_DIM = "#1a8f84"
    AMBER = "#e9a825"
    AMBER_DIM = "#b07d14"
    DANGER = "#e85d4c"
    DANGER_DIM = "#a33d32"
    OK = "#6bcf7f"
    # Point sizes (tk scaling converts to crisp device pixels)
    FONT = ("Microsoft YaHei UI", 10)
    FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
    FONT_TITLE = ("Microsoft YaHei UI", 15, "bold")
    FONT_SMALL = ("Microsoft YaHei UI", 9)
    FONT_MONO = ("Cascadia Mono", 10)
    FONT_BRAND = ("Microsoft YaHei UI", 18, "bold")
    FONT_PANEL = ("Microsoft YaHei UI", 11, "bold")


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=C.BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=C.BG, foreground=C.TEXT, font=C.FONT)
    style.configure("TFrame", background=C.BG)
    style.configure("Card.TFrame", background=C.CARD)
    style.configure("Inner.TFrame", background=C.CARD)
    style.configure("TLabel", background=C.CARD, foreground=C.TEXT, font=C.FONT)
    style.configure("Muted.TLabel", background=C.CARD, foreground=C.MUTED, font=C.FONT_SMALL)
    style.configure("Title.TLabel", background=C.CARD, foreground=C.TEXT, font=C.FONT_BOLD)
    style.configure("Head.TLabel", background=C.BG, foreground=C.TEXT, font=C.FONT_TITLE)
    style.configure("Sub.TLabel", background=C.BG, foreground=C.MUTED, font=C.FONT_SMALL)
    style.configure("Foot.TLabel", background=C.BG, foreground=C.DIM, font=C.FONT_SMALL)
    style.configure("Foot.TCheckbutton", background=C.BG, foreground=C.MUTED, font=C.FONT_SMALL)
    style.map("Foot.TCheckbutton", background=[("active", C.BG)])

    style.configure(
        "TEntry",
        fieldbackground=C.INPUT,
        foreground=C.TEXT,
        insertcolor=C.TEXT,
        bordercolor=C.LINE,
        lightcolor=C.LINE,
        darkcolor=C.LINE,
        padding=4,
    )
    style.map("TEntry", fieldbackground=[("disabled", "#151b22")], foreground=[("disabled", C.DIM)])

    style.configure(
        "TCombobox",
        fieldbackground=C.INPUT,
        background=C.CARD_ALT,
        foreground=C.TEXT,
        arrowcolor=C.TEXT,
        bordercolor=C.LINE,
        padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", C.INPUT), ("disabled", "#151b22")],
        foreground=[("readonly", C.TEXT), ("disabled", C.DIM)],
    )

    style.configure(
        "TCheckbutton",
        background=C.CARD,
        foreground=C.TEXT,
        font=C.FONT,
        indicatormargin=4,
    )
    style.map(
        "TCheckbutton",
        background=[("active", C.CARD)],
        foreground=[("disabled", C.DIM)],
    )

    style.configure("TSeparator", background=C.LINE)
    style.configure(
        "Vertical.TScrollbar",
        background=C.CARD_ALT,
        troughcolor=C.BG,
        bordercolor=C.LINE,
        arrowcolor=C.MUTED,
    )
    return style


def pill_button(
    parent: tk.Misc,
    text: str,
    command,
    *,
    accent: str,
    accent_hover: str,
    fg: str = "#0e1318",
) -> tk.Button:
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=accent,
        fg=fg,
        activebackground=accent_hover,
        activeforeground=fg,
        disabledforeground="#5a6a7a",
        relief="flat",
        borderwidth=0,
        font=C.FONT_BOLD,
        cursor="hand2",
        padx=S(14),
        pady=S(8),
    )
    btn.bind("<Enter>", lambda _e: btn.configure(bg=accent_hover) if str(btn["state"]) == "normal" else None)
    btn.bind("<Leave>", lambda _e: btn.configure(bg=accent) if str(btn["state"]) == "normal" else None)
    return btn


def ghost_button(parent: tk.Misc, text: str, command) -> tk.Button:
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=C.CARD_ALT,
        fg=C.TEXT,
        activebackground=C.LINE,
        activeforeground=C.TEXT,
        disabledforeground=C.DIM,
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=C.LINE,
        highlightcolor=C.LINE,
        font=C.FONT,
        cursor="hand2",
        padx=S(12),
        pady=S(6),
    )
    return btn

TRIGGER_BIND = "绑定键触发"
TRIGGER_DOUBLE = "双击触发"

MOUSE_BUTTON_LABELS = {
    Button.left: "鼠标左键",
    Button.right: "鼠标右键",
    Button.middle: "鼠标中键",
    Button.x1: "鼠标侧键1 (后退)",
    Button.x2: "鼠标侧键2 (前进)",
}

CURVE_MODES = (
    "恒定",
    "加速 (慢→快)",
    "减速 (快→慢)",
    "正弦波动",
    "缓入缓出",
    "自定义",
)

BindTarget = keyboard.Key | keyboard.KeyCode | Button
Point = tuple[float, float]


def app_dir() -> Path:
    """Directory of the exe (frozen) or this script — settings live here."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    return app_dir() / SETTINGS_FILE


def serialize_bind(target: BindTarget | None) -> dict | None:
    if target is None:
        return None
    if isinstance(target, Button):
        return {"kind": "button", "name": target.name}
    if isinstance(target, keyboard.Key):
        return {"kind": "key", "name": target.name}
    if isinstance(target, keyboard.KeyCode):
        return {"kind": "keycode", "vk": target.vk, "char": target.char}
    return None


def deserialize_bind(data: dict | None) -> BindTarget | None:
    if not data or not isinstance(data, dict):
        return None
    try:
        kind = data.get("kind")
        if kind == "button":
            return Button[data["name"]]
        if kind == "key":
            return keyboard.Key[data["name"]]
        if kind == "keycode":
            vk = data.get("vk")
            char = data.get("char")
            if vk is not None:
                return keyboard.KeyCode.from_vk(int(vk))
            if char:
                return keyboard.KeyCode.from_char(str(char))
    except Exception:
        return None
    return None


def format_bind(target: BindTarget) -> str:
    if isinstance(target, Button):
        return MOUSE_BUTTON_LABELS.get(target, str(target))
    if isinstance(target, keyboard.KeyCode):
        if target.char:
            return target.char.upper()
        if target.vk is not None:
            return f"VK_{target.vk}"
        return str(target)
    name = str(target)
    if name.startswith("Key."):
        name = name[4:]
    return name.upper().replace("_", " ")


def binds_match(a: BindTarget | None, b: BindTarget | None) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, Button) or isinstance(b, Button):
        return a == b
    if a == b:
        return True
    if isinstance(a, keyboard.KeyCode) and isinstance(b, keyboard.KeyCode):
        if a.vk is not None and b.vk is not None and a.vk == b.vk:
            return True
        if a.char and b.char and a.char.lower() == b.char.lower():
            return True
    return False


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def interpolate_points(points: list[Point], t: float) -> float:
    if not points:
        return 0.5
    t = t % 1.0
    pts = sorted(points, key=lambda p: p[0])
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= t <= x1:
            if x1 == x0:
                return y0
            u = (t - x0) / (x1 - x0)
            return lerp(y0, y1, u)
    return pts[-1][1]


def preset_points(mode: str) -> list[Point]:
    if mode == "恒定":
        return [(0.0, 0.5), (1.0, 0.5)]
    if mode == "加速 (慢→快)":
        return [(0.0, 1.0), (0.5, 0.45), (1.0, 0.0)]
    if mode == "减速 (快→慢)":
        return [(0.0, 0.0), (0.5, 0.55), (1.0, 1.0)]
    if mode == "正弦波动":
        return [
            (i / 8.0, 0.5 + 0.5 * math.sin(2 * math.pi * i / 8.0)) for i in range(9)
        ]
    if mode == "缓入缓出":
        return [(i / 8.0, 1.0 - math.sin(math.pi * i / 8.0)) for i in range(9)]
    return [(0.0, 0.8), (0.25, 0.2), (0.5, 0.7), (0.75, 0.15), (1.0, 0.6)]


def curve_formula(mode: str, t: float, points: list[Point]) -> float:
    t = t % 1.0
    if mode == "恒定":
        return 0.5
    if mode == "加速 (慢→快)":
        return 1.0 - smoothstep(t)
    if mode == "减速 (快→慢)":
        return smoothstep(t)
    if mode == "正弦波动":
        return 0.5 + 0.5 * math.sin(2 * math.pi * t)
    if mode == "缓入缓出":
        return 1.0 - math.sin(math.pi * t)
    return interpolate_points(points, t)


class ClickPanel:
    """One independent clicker column (left or right mouse)."""

    def __init__(
        self,
        app: "AutoClickerApp",
        parent: tk.Misc,
        *,
        title: str,
        click_button: Button,
        has_bind: bool,
        has_double_trigger: bool,
        panel_enable_toggle: bool = False,
    ) -> None:
        self.app = app
        self.click_button = click_button
        self.has_bind = has_bind
        self.has_double_trigger = has_double_trigger
        self.panel_enable_toggle = panel_enable_toggle
        self.button_name = "左键" if click_button == Button.left else "右键"

        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._click_count = 0
        self._fixed_pos: tuple[int, int] | None = None
        self._curve_points: list[Point] = preset_points("正弦波动")
        self._drag_idx: int | None = None
        self._curve_progress = 0.0
        self._lock = threading.Lock()

        self._bind: BindTarget | None = None
        self._bind_held = False
        self._recording = False
        self._last_trigger_press = 0.0

        self.accent = C.TEAL if click_button == Button.left else C.AMBER
        self.accent_dim = C.TEAL_DIM if click_button == Button.left else C.AMBER_DIM
        self.curve_color = self.accent

        # Card shell: accent strip + body
        self.frame = tk.Frame(parent, bg=C.CARD, highlightthickness=1, highlightbackground=C.LINE)
        strip = tk.Frame(self.frame, bg=self.accent, height=S(3))
        strip.pack(fill="x")
        head = tk.Frame(self.frame, bg=C.CARD)
        head.pack(fill="x", padx=S(14), pady=(S(12), S(4)))
        tk.Label(
            head,
            text=title,
            bg=C.CARD,
            fg=C.TEXT,
            font=C.FONT_PANEL,
        ).pack(side="left")
        tk.Label(
            head,
            text="LEFT" if click_button == Button.left else "RIGHT",
            bg=C.CARD,
            fg=self.accent,
            font=("Cascadia Mono", 9, "bold"),
        ).pack(side="right")
        pad = S(12)
        self.body = ttk.Frame(
            self.frame, style="Card.TFrame", padding=(pad, S(6), pad, pad)
        )
        self.body.pack(fill="both", expand=True)
        self._build_ui()

    def _bind_mode_active(self) -> bool:
        if not self.has_bind:
            return False
        if self.has_double_trigger and hasattr(self, "trigger_mode_var"):
            return self.trigger_mode_var.get() == TRIGGER_BIND
        return True

    def _double_mode_active(self) -> bool:
        if not self.has_double_trigger:
            return False
        if self.panel_enable_toggle and not self.enabled_var.get():
            return False
        if self.has_bind and hasattr(self, "trigger_mode_var"):
            return self.trigger_mode_var.get() == TRIGGER_DOUBLE
        return True

    def _section(self, frm: ttk.Frame, row: int, title: str) -> int:
        wrap = tk.Frame(frm, bg=C.CARD)
        wrap.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(S(10), S(4)))
        tk.Frame(wrap, bg=self.accent, width=S(3), height=S(14)).pack(
            side="left", padx=(0, S(8))
        )
        tk.Label(wrap, text=title, bg=C.CARD, fg=C.TEXT, font=C.FONT_BOLD).pack(
            side="left"
        )
        return row + 1

    def _build_ui(self) -> None:
        pad = {"padx": S(4), "pady": S(4)}
        frm = self.body
        frm.columnconfigure(1, weight=1)

        row = 0
        self.enabled_var = tk.BooleanVar(value=not self.panel_enable_toggle)
        if self.panel_enable_toggle:
            ttk.Checkbutton(
                frm,
                text=f"启用{self.button_name}连点板块",
                variable=self.enabled_var,
                command=self._toggle_enabled_ui,
            ).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1

        if self.has_bind and self.has_double_trigger:
            ttk.Label(frm, text="触发方式").grid(row=row, column=0, sticky="w", **pad)
            self.trigger_mode_var = tk.StringVar(value=TRIGGER_BIND)
            self.trigger_mode_box = ttk.Combobox(
                frm,
                textvariable=self.trigger_mode_var,
                values=(TRIGGER_BIND, TRIGGER_DOUBLE),
                state="readonly",
                width=14,
            )
            self.trigger_mode_box.grid(row=row, column=1, sticky="ew", **pad)
            self.trigger_mode_box.bind(
                "<<ComboboxSelected>>", lambda _e: self._on_trigger_mode_change()
            )
            row += 1

        trigger_row = row
        self.dbl_frame = ttk.Frame(frm, style="Inner.TFrame")
        self.bind_frame = ttk.Frame(frm, style="Inner.TFrame")

        if self.has_double_trigger:
            ttk.Label(self.dbl_frame, text="双击间隔阈值 (ms)").grid(
                row=0, column=0, sticky="w", **pad
            )
            self.dbl_threshold_var = tk.StringVar(value="300")
            self.dbl_entry = ttk.Entry(
                self.dbl_frame, textvariable=self.dbl_threshold_var, width=10
            )
            self.dbl_entry.grid(row=0, column=1, sticky="ew", **pad)
            ttk.Label(
                self.dbl_frame,
                text=(
                    f"两次{self.button_name}间隔<阈值→开始；"
                    f"之后需在阈值内持续{self.button_name}输入，否则停止"
                ),
                style="Muted.TLabel",
                wraplength=S(320),
            ).grid(row=1, column=0, columnspan=2, sticky="w", padx=S(4), pady=(0, S(2)))

        if self.has_bind:
            ttk.Label(self.bind_frame, text="绑定键位").grid(
                row=0, column=0, sticky="w", **pad
            )
            self.bind_label_var = tk.StringVar(value="未绑定")
            ttk.Label(
                self.bind_frame,
                textvariable=self.bind_label_var,
                style="Title.TLabel",
            ).grid(row=0, column=1, sticky="w", **pad)
            self.record_btn = ghost_button(
                self.bind_frame, "录制绑定键", self._start_recording
            )
            self.record_btn.grid(
                row=1, column=0, columnspan=2, sticky="ew", pady=S(4)
            )
            ttk.Label(
                self.bind_frame,
                text="支持键盘 / 鼠标侧键；按住开始，松开停止",
                style="Muted.TLabel",
                wraplength=S(320),
            ).grid(row=2, column=0, columnspan=2, sticky="w", padx=S(4))

        self._trigger_row = trigger_row
        if self.has_bind and self.has_double_trigger:
            self.bind_frame.grid(row=trigger_row, column=0, columnspan=2, sticky="ew")
            row += 1
        elif self.has_bind:
            self.bind_frame.grid(row=trigger_row, column=0, columnspan=2, sticky="ew")
            row += 1
        elif self.has_double_trigger:
            self.dbl_frame.grid(row=trigger_row, column=0, columnspan=2, sticky="ew")
            row += 1

        row = self._section(frm, row, "基础")

        ttk.Label(frm, text="最短间隔 (ms)").grid(row=row, column=0, sticky="w", **pad)
        self.min_var = tk.StringVar(value="30")
        self.min_entry = ttk.Entry(frm, textvariable=self.min_var, width=12)
        self.min_entry.grid(row=row, column=1, sticky="ew", **pad)
        self.min_entry.bind("<KeyRelease>", lambda _e: self._redraw_curve())
        row += 1

        ttk.Label(frm, text="最长间隔 (ms)").grid(row=row, column=0, sticky="w", **pad)
        self.max_var = tk.StringVar(value="120")
        self.max_entry = ttk.Entry(frm, textvariable=self.max_var, width=12)
        self.max_entry.grid(row=row, column=1, sticky="ew", **pad)
        self.max_entry.bind("<KeyRelease>", lambda _e: self._redraw_curve())
        row += 1

        ttk.Label(frm, text="点击位置").grid(row=row, column=0, sticky="w", **pad)
        self.pos_mode = tk.StringVar(value="跟随光标")
        self.pos_box = ttk.Combobox(
            frm,
            textvariable=self.pos_mode,
            values=["跟随光标", "固定坐标"],
            state="readonly",
            width=12,
        )
        self.pos_box.grid(row=row, column=1, sticky="ew", **pad)
        self.pos_box.bind("<<ComboboxSelected>>", lambda _e: self._update_pos_hint())
        row += 1

        self.pos_hint = ttk.Label(frm, text="跟随当前光标", style="Muted.TLabel")
        self.pos_hint.grid(row=row, column=0, columnspan=2, sticky="w", padx=4)
        row += 1

        self.lock_btn = ghost_button(frm, "锁定当前光标位置", self._capture_position)
        self.lock_btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=S(4))
        row += 1

        ttk.Label(frm, text="最大次数 (0=无限)").grid(
            row=row, column=0, sticky="w", **pad
        )
        self.max_clicks_var = tk.StringVar(value="0")
        self.max_clicks_entry = ttk.Entry(
            frm, textvariable=self.max_clicks_var, width=12
        )
        self.max_clicks_entry.grid(row=row, column=1, sticky="ew", **pad)
        row += 1

        row = self._section(frm, row, "速度曲线")

        ttk.Label(frm, text="曲线类型").grid(row=row, column=0, sticky="w", **pad)
        self.curve_var = tk.StringVar(value="正弦波动")
        self.curve_box = ttk.Combobox(
            frm,
            textvariable=self.curve_var,
            values=CURVE_MODES,
            state="readonly",
            width=14,
        )
        self.curve_box.grid(row=row, column=1, sticky="ew", **pad)
        self.curve_box.bind("<<ComboboxSelected>>", self._on_curve_mode_change)
        row += 1

        ttk.Label(frm, text="周期 (点击数)").grid(row=row, column=0, sticky="w", **pad)
        self.cycle_var = tk.StringVar(value="20")
        self.cycle_entry = ttk.Entry(frm, textvariable=self.cycle_var, width=12)
        self.cycle_entry.grid(row=row, column=1, sticky="ew", **pad)
        self.cycle_entry.bind("<KeyRelease>", lambda _e: self._redraw_curve())
        row += 1

        ttk.Label(
            frm,
            text="X=周期 · Y=间隔(上慢下快) · 点图可自定义",
            style="Muted.TLabel",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=4)
        row += 1

        canvas_wrap = tk.Frame(frm, bg=C.LINE, padx=S(1), pady=S(1))
        canvas_wrap.grid(row=row, column=0, columnspan=2, sticky="ew", pady=S(6))
        self.canvas = tk.Canvas(
            canvas_wrap,
            width=S(320),
            height=S(140),
            bg=C.INPUT,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        row += 1

        self.interval_now_var = tk.StringVar(value="当前间隔: —")
        ttk.Label(frm, textvariable=self.interval_now_var, style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", **pad
        )
        row += 1

        row = self._section(frm, row, "随机偏移")

        self.jitter_enabled = tk.BooleanVar(value=False)
        self.jitter_chk = ttk.Checkbutton(
            frm,
            text="启用随机时间偏移",
            variable=self.jitter_enabled,
            command=self._toggle_jitter_ui,
        )
        self.jitter_chk.grid(row=row, column=0, columnspan=2, sticky="w", **pad)
        row += 1

        ttk.Label(frm, text="偏移上限 (ms)").grid(row=row, column=0, sticky="w", **pad)
        self.jitter_var = tk.StringVar(value="20")
        self.jitter_entry = ttk.Entry(frm, textvariable=self.jitter_var, width=12)
        self.jitter_entry.grid(row=row, column=1, sticky="ew", **pad)
        row += 1

        ttk.Label(
            frm,
            text="开启后：间隔额外加 0～上限 随机毫秒",
            style="Muted.TLabel",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=S(4))
        row += 1

        btn_row = tk.Frame(frm, bg=C.CARD)
        btn_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(S(12), S(6)))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        self.start_btn = pill_button(
            btn_row,
            "开始",
            self.start_clicking,
            accent=self.accent,
            accent_hover=self.accent_dim,
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, S(4)))
        self.stop_btn = pill_button(
            btn_row,
            "停止",
            self.stop_clicking,
            accent=C.DANGER,
            accent_hover=C.DANGER_DIM,
            fg=C.TEXT,
        )
        self.stop_btn.configure(state="disabled", bg="#3a3030")
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(S(4), 0))
        row += 1

        self.status_var = tk.StringVar(value=self._idle_status())
        ttk.Label(
            frm, textvariable=self.status_var, style="Muted.TLabel", wraplength=S(320)
        ).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
        row += 1

        self.count_var = tk.StringVar(value="已点击: 0")
        ttk.Label(frm, textvariable=self.count_var).grid(
            row=row, column=0, columnspan=2, sticky="w", **pad
        )

        self._toggle_jitter_ui()
        if self.panel_enable_toggle:
            self._toggle_enabled_ui()
        elif self.has_bind and self.has_double_trigger:
            self._on_trigger_mode_change()

    def _on_trigger_mode_change(self) -> None:
        if self._running:
            self.stop_clicking()
        if self._recording:
            self._finish_recording(None)
        tr = self._trigger_row
        if self.trigger_mode_var.get() == TRIGGER_BIND:
            self.dbl_frame.grid_remove()
            self.bind_frame.grid(row=tr, column=0, columnspan=2, sticky="ew")
        else:
            self.bind_frame.grid_remove()
            self.dbl_frame.grid(row=tr, column=0, columnspan=2, sticky="ew")
        if not self._running:
            self.status_var.set(self._idle_status())

    def _idle_status(self) -> str:
        if self.panel_enable_toggle and not self.enabled_var.get():
            return "已关闭 — 勾选启用后可用"
        if self._bind_mode_active():
            return "就绪 — 录制绑定键，或点「开始」"
        if self.has_double_trigger:
            return (
                f"就绪 — 快速双击{self.button_name}启动"
                f"（需持续{self.button_name}输入），或点「开始」"
            )
        return "就绪"

    def _toggle_enabled_ui(self) -> None:
        on = self.enabled_var.get()
        state = "normal" if on else "disabled"
        widgets = [
            self.min_entry,
            self.max_entry,
            self.pos_box,
            self.lock_btn,
            self.max_clicks_entry,
            self.curve_box,
            self.cycle_entry,
            self.jitter_chk,
        ]
        if hasattr(self, "dbl_entry"):
            widgets.append(self.dbl_entry)
        if hasattr(self, "trigger_mode_box"):
            widgets.append(self.trigger_mode_box)
        for w in widgets:
            try:
                if w is self.pos_box or w is self.curve_box:
                    w.config(state="readonly" if on else "disabled")
                elif w is getattr(self, "trigger_mode_box", None):
                    w.config(state="readonly" if on else "disabled")
                else:
                    w.config(state=state)
            except tk.TclError:
                pass
        if on:
            self._toggle_jitter_ui()
            if not self._running:
                self._set_action_buttons(running=False)
        else:
            self.jitter_entry.config(state="disabled")
            if self._running:
                self.stop_clicking()
            else:
                self._set_action_buttons(running=False)
        if not self._running:
            self.status_var.set(self._idle_status())

    def _toggle_jitter_ui(self) -> None:
        if self.panel_enable_toggle and not self.enabled_var.get():
            self.jitter_entry.config(state="disabled")
            return
        self.jitter_entry.config(
            state="normal" if self.jitter_enabled.get() else "disabled"
        )

    def _update_pos_hint(self) -> None:
        if self.pos_mode.get() == "固定坐标":
            if self._fixed_pos:
                x, y = self._fixed_pos
                self.pos_hint.config(text=f"固定: ({x}, {y})")
            else:
                self.pos_hint.config(text="请先锁定当前光标位置")
        else:
            self.pos_hint.config(text="跟随当前光标")

    def _capture_position(self) -> None:
        x, y = self.app.mouse.position
        self._fixed_pos = (int(x), int(y))
        self.pos_mode.set("固定坐标")
        self._update_pos_hint()
        self.status_var.set(f"已锁定坐标 ({x}, {y})")

    def _on_curve_mode_change(self, _event=None) -> None:
        mode = self.curve_var.get()
        if mode != "自定义":
            self._curve_points = preset_points(mode)
        elif not self._curve_points:
            self._curve_points = preset_points("自定义")
        self._redraw_curve()

    def _parse_range(self) -> tuple[float, float] | None:
        try:
            lo = float(self.min_var.get().strip())
            hi = float(self.max_var.get().strip())
            if lo < 1 or hi < 1:
                return None
            if lo > hi:
                lo, hi = hi, lo
            return lo, hi
        except ValueError:
            return None

    def _parse_cycle(self) -> int:
        try:
            return max(1, int(self.cycle_var.get().strip()))
        except ValueError:
            return 20

    def _norm_at(self, t: float) -> float:
        return clamp(curve_formula(self.curve_var.get(), t, self._curve_points), 0.0, 1.0)

    def _canvas_pad(self) -> int:
        return S(18)

    def _canvas_to_point(self, x: float, y: float) -> Point:
        w, h, pad = int(self.canvas["width"]), int(self.canvas["height"]), self._canvas_pad()
        t = clamp((x - pad) / max(1, w - 2 * pad), 0.0, 1.0)
        n = clamp(1.0 - (y - pad) / max(1, h - 2 * pad), 0.0, 1.0)
        return t, n

    def _point_to_canvas(self, t: float, n: float) -> tuple[float, float]:
        w, h, pad = int(self.canvas["width"]), int(self.canvas["height"]), self._canvas_pad()
        return pad + t * (w - 2 * pad), pad + (1.0 - n) * (h - 2 * pad)

    def _redraw_curve(self) -> None:
        c = self.canvas
        c.delete("all")
        w, h, pad = int(c["width"]), int(c["height"]), self._canvas_pad()
        rng = self._parse_range()
        lo, hi = rng if rng else (30.0, 120.0)
        # subtle fill
        c.create_rectangle(pad, pad, w - pad, h - pad, outline=C.LINE, fill="#10161c")
        for i in range(1, 4):
            yy = pad + (h - 2 * pad) * i / 4
            xx = pad + (w - 2 * pad) * i / 4
            c.create_line(pad, yy, w - pad, yy, fill="#1c2630")
            c.create_line(xx, pad, xx, h - pad, fill="#1c2630")
        c.create_text(
            pad + S(2),
            S(10),
            text=f"{hi:.0f}ms",
            fill=C.DIM,
            anchor="w",
            font=C.FONT_SMALL,
        )
        c.create_text(
            pad + S(2),
            h - S(10),
            text=f"{lo:.0f}ms",
            fill=C.DIM,
            anchor="w",
            font=C.FONT_SMALL,
        )

        mode = self.curve_var.get()
        coords: list[float] = []
        for i in range(65):
            t = i / 64
            n = 0.5 if mode == "恒定" else self._norm_at(t)
            x, y = self._point_to_canvas(t, n)
            coords.extend([x, y])
        if len(coords) >= 4:
            c.create_line(*coords, fill=self.curve_color, width=2, smooth=True)

        show_pts = self._curve_points if mode == "自定义" else preset_points(mode)
        for t, n in show_pts:
            x, y = self._point_to_canvas(t, n)
            r = S(6) if mode == "自定义" else S(4)
            color = C.AMBER if mode == "自定义" else C.DIM
            c.create_oval(
                x - r, y - r, x + r, y + r, fill=color, outline=C.TEXT, width=1
            )

        pn = 0.5 if mode == "恒定" else self._norm_at(self._curve_progress)
        mx, my = self._point_to_canvas(self._curve_progress, pn)
        pr = S(5)
        c.create_oval(mx - pr, my - pr, mx + pr, my + pr, fill=C.DANGER, outline="")
        c.create_line(mx, pad, mx, h - pad, fill=C.DANGER, dash=(2, 2))

        if mode == "恒定":
            cur = (lo + hi) / 2.0
        else:
            cur = lerp(lo, hi, pn)
        self.interval_now_var.set(f"当前间隔: {cur:.1f} ms")

    def _nearest_point(self, x: float, y: float) -> int | None:
        if self.curve_var.get() != "自定义":
            return None
        best_i, best_d = None, float(S(14))
        for i, (t, n) in enumerate(self._curve_points):
            px, py = self._point_to_canvas(t, n)
            d = math.hypot(px - x, py - y)
            if d < best_d:
                best_d, best_i = d, i
        return best_i

    def _on_canvas_press(self, event: tk.Event) -> None:
        if self.panel_enable_toggle and not self.enabled_var.get():
            return
        if self.curve_var.get() != "自定义":
            self._curve_points = preset_points(self.curve_var.get())
            self.curve_var.set("自定义")
            self._redraw_curve()
            return
        idx = self._nearest_point(event.x, event.y)
        if idx is not None:
            self._drag_idx = idx
            return
        t, n = self._canvas_to_point(event.x, event.y)
        self._curve_points.append((t, n))
        self._curve_points.sort(key=lambda p: p[0])
        self._drag_idx = min(
            range(len(self._curve_points)),
            key=lambda i: abs(self._curve_points[i][0] - t),
        )
        self._redraw_curve()

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if self._drag_idx is None or self.curve_var.get() != "自定义":
            return
        t, n = self._canvas_to_point(event.x, event.y)
        pts = list(self._curve_points)
        if self._drag_idx == 0:
            t = 0.0
        elif self._drag_idx == len(pts) - 1:
            t = 1.0
        if self._drag_idx > 0:
            t = max(t, pts[self._drag_idx - 1][0] + 0.01)
        if self._drag_idx < len(pts) - 1:
            t = min(t, pts[self._drag_idx + 1][0] - 0.01)
        pts[self._drag_idx] = (clamp(t, 0.0, 1.0), n)
        self._curve_points = pts
        self._redraw_curve()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        self._drag_idx = None

    def _start_recording(self) -> None:
        if self._running:
            self.stop_clicking()
        self.app._cancel_other_recording(self)
        self._recording = True
        self.record_btn.config(state="disabled", text="请按键盘或鼠标侧键…")
        self.status_var.set("录制中：按键盘键或鼠标侧键（Esc 取消）")

    def _finish_recording(self, target: BindTarget | None) -> None:
        self._recording = False
        self.app.root.after(
            0, lambda: self.record_btn.config(state="normal", text="录制绑定键")
        )
        if target is None:
            self.app.root.after(0, lambda: self.status_var.set("已取消录制"))
            return
        # avoid binding the output button itself
        if isinstance(target, Button) and target == self.click_button:
            self.app.root.after(
                0,
                lambda: self.status_var.set("不能绑定与输出相同的鼠标键，请重录"),
            )
            return
        self._bind = target
        label = format_bind(target)
        self.app.root.after(0, lambda: self.bind_label_var.set(label))
        self.app.root.after(
            0, lambda: self.status_var.set(f"已绑定 [{label}] — 按住开始连点")
        )

    def _parse_settings(
        self,
    ) -> tuple[float, float, int, int, bool, float] | None:
        if self.panel_enable_toggle and not self.enabled_var.get():
            messagebox.showinfo("未启用", f"请先勾选「启用{self.button_name}连点板块」")
            return None

        rng = self._parse_range()
        if rng is None:
            messagebox.showerror("参数错误", "最短/最长间隔必须是 ≥ 1 的数字（毫秒）")
            return None
        lo, hi = rng

        try:
            max_clicks = int(self.max_clicks_var.get().strip())
            if max_clicks < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "最大次数必须是 ≥ 0 的整数")
            return None

        cycle = self._parse_cycle()
        jitter_on = bool(self.jitter_enabled.get())
        jitter_max = 0.0
        if jitter_on:
            try:
                jitter_max = float(self.jitter_var.get().strip())
                if jitter_max < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("参数错误", "偏移上限必须是 ≥ 0 的数字（毫秒）")
                return None

        if self.pos_mode.get() == "固定坐标" and self._fixed_pos is None:
            messagebox.showwarning("未锁定坐标", "请先点击「锁定当前光标位置」")
            return None

        return lo, hi, max_clicks, cycle, jitter_on, jitter_max

    def start_clicking(self, *, from_trigger: bool = False) -> None:
        with self._lock:
            if self._running:
                return
            settings = self._parse_settings()
            if settings is None:
                self._bind_held = False
                return
            lo, hi, max_clicks, cycle, jitter_on, jitter_max = settings
            self._stop_event.clear()
            self._running = True
            self._click_count = 0
            self._curve_progress = 0.0

        root = self.app.root
        root.after(0, lambda: self.count_var.set("已点击: 0"))
        root.after(0, lambda: self._set_action_buttons(running=True))
        root.after(0, self._redraw_curve)

        if from_trigger and self._bind_mode_active() and self._bind is not None:
            label = format_bind(self._bind)
            root.after(0, lambda: self.status_var.set(f"连点中… 松开 [{label}] 停止"))
        elif self._double_mode_active():
            name = self.button_name
            root.after(
                0,
                lambda: self.status_var.set(
                    f"连点中… 请在阈值内持续{name}输入，否则自动停止"
                ),
            )
        else:
            root.after(0, lambda: self.status_var.set("连点中… 点「停止」或 Esc"))

        use_keepalive = self._double_mode_active()
        if use_keepalive:
            self._last_trigger_press = time.perf_counter()

        mode = self.curve_var.get()
        points = list(self._curve_points)
        keepalive_ms = self._double_threshold_ms() if use_keepalive else 0.0
        self._worker = threading.Thread(
            target=self._click_loop,
            args=(
                lo,
                hi,
                max_clicks,
                cycle,
                mode,
                points,
                jitter_on,
                jitter_max,
                keepalive_ms,
            ),
            daemon=True,
        )
        self._worker.start()

    def stop_clicking(self) -> None:
        with self._lock:
            if not self._running:
                self.app.root.after(0, self._on_stopped_ui)
                return
            self._stop_event.set()
            self._running = False
        self.app.root.after(0, self._on_stopped_ui)

    def _set_action_buttons(self, *, running: bool) -> None:
        can_start = not (self.panel_enable_toggle and not self.enabled_var.get())
        if running:
            self.start_btn.config(state="disabled", bg="#2a3538", disabledforeground=C.DIM)
            self.stop_btn.config(state="normal", bg=C.DANGER)
        else:
            if can_start:
                self.start_btn.config(state="normal", bg=self.accent)
            else:
                self.start_btn.config(
                    state="disabled", bg="#2a3538", disabledforeground=C.DIM
                )
            self.stop_btn.config(state="disabled", bg="#3a3030", disabledforeground=C.DIM)

    def _on_stopped_ui(self) -> None:
        self._set_action_buttons(running=False)
        self.status_var.set(self._idle_status())

    def _double_threshold_ms(self) -> float:
        try:
            v = float(self.dbl_threshold_var.get().strip())
            return v if v >= 1 else 300.0
        except (ValueError, AttributeError):
            return 300.0

    def _keepalive_expired(self, keepalive_ms: float) -> bool:
        if keepalive_ms <= 0:
            return False
        elapsed_ms = (time.perf_counter() - self._last_trigger_press) * 1000.0
        return elapsed_ms > keepalive_ms

    def _click_loop(
        self,
        lo: float,
        hi: float,
        max_clicks: int,
        cycle: int,
        mode: str,
        points: list[Point],
        jitter_on: bool,
        jitter_max: float,
        keepalive_ms: float,
    ) -> None:
        root = self.app.root
        while not self._stop_event.is_set():
            if self._keepalive_expired(keepalive_ms):
                with self._lock:
                    self._running = False
                    self._stop_event.set()
                root.after(0, self._on_stopped_ui)
                root.after(
                    0,
                    lambda: self.status_var.set(
                        f"已停止 — 阈值内无{self.button_name}输入"
                    ),
                )
                break

            idx = self._click_count
            t = (idx % cycle) / cycle
            if mode == "恒定":
                base_ms = (lo + hi) / 2.0
            else:
                n = clamp(curve_formula(mode, t, points), 0.0, 1.0)
                base_ms = lerp(lo, hi, n)

            jitter_ms = (
                random.uniform(0.0, jitter_max) if jitter_on and jitter_max > 0 else 0.0
            )
            interval_ms = base_ms + jitter_ms

            self._curve_progress = t
            root.after(0, self._redraw_curve)
            if jitter_on and jitter_ms > 0:
                root.after(
                    0,
                    lambda b=base_ms, j=jitter_ms, tot=interval_ms: self.interval_now_var.set(
                        f"当前间隔: {tot:.1f} ms (曲线 {b:.1f} + 偏移 {j:.1f})"
                    ),
                )
            else:
                root.after(
                    0,
                    lambda ms=interval_ms: self.interval_now_var.set(
                        f"当前间隔: {ms:.1f} ms"
                    ),
                )

            if self.pos_mode.get() == "固定坐标" and self._fixed_pos:
                self.app.mouse.position = self._fixed_pos

            self.app._emitting_button = self.click_button
            try:
                self.app.mouse.click(self.click_button, 1)
            finally:
                self.app._emitting_button = None

            self._click_count += 1
            count = self._click_count
            root.after(0, lambda c=count: self.count_var.set(f"已点击: {c}"))

            if max_clicks > 0 and self._click_count >= max_clicks:
                with self._lock:
                    self._running = False
                    self._stop_event.set()
                self._bind_held = False
                root.after(0, self._on_stopped_ui)
                root.after(
                    0,
                    lambda: self.status_var.set(f"已达最大次数 {max_clicks}，已停止"),
                )
                break

            # Sleep in small slices so keepalive can stop promptly
            remaining = interval_ms / 1000.0
            while remaining > 0 and not self._stop_event.is_set():
                if self._keepalive_expired(keepalive_ms):
                    with self._lock:
                        self._running = False
                        self._stop_event.set()
                    root.after(0, self._on_stopped_ui)
                    root.after(
                        0,
                        lambda: self.status_var.set(
                            f"已停止 — 阈值内无{self.button_name}输入"
                        ),
                    )
                    remaining = 0
                    break
                slice_s = min(0.02, remaining)
                if self._stop_event.wait(slice_s):
                    remaining = 0
                    break
                remaining -= slice_s

        with self._lock:
            self._running = False

    def export_settings(self) -> dict:
        data: dict = {
            "enabled": bool(self.enabled_var.get()),
            "min_ms": self.min_var.get(),
            "max_ms": self.max_var.get(),
            "pos_mode": self.pos_mode.get(),
            "fixed_pos": list(self._fixed_pos) if self._fixed_pos else None,
            "max_clicks": self.max_clicks_var.get(),
            "curve_mode": self.curve_var.get(),
            "curve_points": [list(p) for p in self._curve_points],
            "cycle": self.cycle_var.get(),
            "jitter_enabled": bool(self.jitter_enabled.get()),
            "jitter_max": self.jitter_var.get(),
        }
        if hasattr(self, "trigger_mode_var"):
            data["trigger_mode"] = self.trigger_mode_var.get()
        if hasattr(self, "dbl_threshold_var"):
            data["dbl_threshold"] = self.dbl_threshold_var.get()
        if self.has_bind:
            data["bind"] = serialize_bind(self._bind)
        return data

    def apply_settings(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return

        def _set(var: tk.Variable, key: str) -> None:
            if key in data and data[key] is not None:
                var.set(data[key])

        if self.panel_enable_toggle and "enabled" in data:
            self.enabled_var.set(bool(data["enabled"]))
        _set(self.min_var, "min_ms")
        _set(self.max_var, "max_ms")
        _set(self.pos_mode, "pos_mode")
        _set(self.max_clicks_var, "max_clicks")
        _set(self.curve_var, "curve_mode")
        _set(self.cycle_var, "cycle")
        if "jitter_enabled" in data:
            self.jitter_enabled.set(bool(data["jitter_enabled"]))
        _set(self.jitter_var, "jitter_max")

        if hasattr(self, "dbl_threshold_var"):
            _set(self.dbl_threshold_var, "dbl_threshold")

        fp = data.get("fixed_pos")
        if isinstance(fp, (list, tuple)) and len(fp) == 2:
            try:
                self._fixed_pos = (int(fp[0]), int(fp[1]))
            except (TypeError, ValueError):
                self._fixed_pos = None
        elif fp is None and "fixed_pos" in data:
            self._fixed_pos = None

        pts = data.get("curve_points")
        if isinstance(pts, list) and pts:
            parsed: list[Point] = []
            for item in pts:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    try:
                        parsed.append((float(item[0]), float(item[1])))
                    except (TypeError, ValueError):
                        continue
            if parsed:
                self._curve_points = parsed

        if hasattr(self, "trigger_mode_var") and "trigger_mode" in data:
            mode = data["trigger_mode"]
            if mode in (TRIGGER_BIND, TRIGGER_DOUBLE):
                self.trigger_mode_var.set(mode)

        if self.has_bind and "bind" in data:
            bind = deserialize_bind(data.get("bind"))
            self._bind = bind
            if bind is not None:
                self.bind_label_var.set(format_bind(bind))
            else:
                self.bind_label_var.set("未绑定")

        # Refresh dependent UI
        if hasattr(self, "trigger_mode_var"):
            self._on_trigger_mode_change()
        if self.panel_enable_toggle:
            self._toggle_enabled_ui()
        self._update_pos_hint()
        self._toggle_jitter_ui()
        # Ensure curve points match mode unless custom
        if self.curve_var.get() != "自定义":
            self._curve_points = preset_points(self.curve_var.get())
        self._redraw_curve()
        if not self._running:
            self.status_var.set(self._idle_status())

    def handle_bind_press(self, key: BindTarget) -> bool:
        """Return True if event consumed."""
        if not self._bind_mode_active() and not self._recording:
            return False
        if self._recording:
            if key == keyboard.Key.esc:
                self._finish_recording(None)
            else:
                self._finish_recording(key)
            return True
        if not self._bind_mode_active():
            return False
        if binds_match(key, self._bind):
            if self._bind_held:
                return True
            self._bind_held = True
            self.app.root.after(0, lambda: self.start_clicking(from_trigger=True))
            return True
        return False

    def handle_bind_release(self, key: BindTarget) -> bool:
        if not self._bind_mode_active():
            return False
        if binds_match(key, self._bind):
            self._bind_held = False
            if self._running:
                self.stop_clicking()
            return True
        return False

    def handle_mouse_press(self, button: Button) -> None:
        if self.has_bind and self._recording:
            self._finish_recording(button)
            return

        if self._bind_mode_active() and binds_match(button, self._bind):
            if not self._bind_held:
                self._bind_held = True
                self.app.root.after(0, lambda: self.start_clicking(from_trigger=True))
            return

        if self._double_mode_active() and button == self.click_button:
            now = time.perf_counter()
            threshold_ms = self._double_threshold_ms()
            dt = (now - self._last_trigger_press) * 1000.0
            self._last_trigger_press = now
            if self._running:
                return
            if dt <= threshold_ms:
                self.app.root.after(
                    0, lambda: self.start_clicking(from_trigger=True)
                )

    def handle_mouse_release(self, button: Button) -> None:
        if self._bind_mode_active() and binds_match(button, self._bind):
            self._bind_held = False
            if self._running:
                self.stop_clicking()


class AutoClickerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_TITLE} v{VERSION}")
        self.root.resizable(True, True)
        self.root.minsize(S(720), S(480))
        self.root.attributes("-topmost", True)
        apply_tk_scaling(root)
        apply_theme(root)

        self.mouse = MouseController()
        self._key_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._emitting_button: Button | None = None

        outer = tk.Frame(root, bg=C.BG)
        outer.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # Brand header (fixed)
        header = tk.Frame(outer, bg=C.BG)
        header.pack(fill="x", padx=S(18), pady=(S(14), S(8)))
        brand = tk.Frame(header, bg=C.BG)
        brand.pack(side="left")
        tk.Label(
            brand,
            text="ADCmc",
            bg=C.BG,
            fg=C.TEXT,
            font=C.FONT_BRAND,
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="可控连点 · 双通道精密控制  ·  可拖拽边框调整窗口大小",
            bg=C.BG,
            fg=C.MUTED,
            font=C.FONT_SMALL,
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"v{VERSION}",
            bg=C.BG,
            fg=C.DIM,
            font=C.FONT_MONO,
        ).pack(side="right", anchor="n", pady=S(6))

        # Scrollable content (fits small / secondary monitors)
        mid = tk.Frame(outer, bg=C.BG)
        mid.pack(fill="both", expand=True, padx=S(10))
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)

        self._scroll = tk.Canvas(mid, bg=C.BG, highlightthickness=0)
        self._vbar = ttk.Scrollbar(mid, orient="vertical", command=self._scroll.yview)
        self._hbar = ttk.Scrollbar(mid, orient="horizontal", command=self._scroll.xview)
        self._scroll.configure(
            yscrollcommand=self._vbar.set, xscrollcommand=self._hbar.set
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._vbar.grid(row=0, column=1, sticky="ns")
        self._hbar.grid(row=1, column=0, sticky="ew")

        self._content = tk.Frame(self._scroll, bg=C.BG)
        self._content_id = self._scroll.create_window(
            (0, 0), window=self._content, anchor="nw"
        )
        self._content.bind("<Configure>", self._on_content_configure)
        self._scroll.bind("<Configure>", self._on_scroll_configure)
        self._scroll.bind("<Enter>", self._bind_wheel)
        self._scroll.bind("<Leave>", self._unbind_wheel)
        self._geometry_restored = False

        cols = tk.Frame(self._content, bg=C.BG)
        cols.pack(fill="both", expand=True, padx=S(8), pady=(0, S(4)))

        self.left = ClickPanel(
            self,
            cols,
            title="左键连点",
            click_button=Button.left,
            has_bind=True,
            has_double_trigger=True,
            panel_enable_toggle=False,
        )
        self.right = ClickPanel(
            self,
            cols,
            title="右键连点",
            click_button=Button.right,
            has_bind=False,
            has_double_trigger=True,
            panel_enable_toggle=True,
        )
        self.left.frame.pack(side="left", fill="both", expand=True, padx=(0, S(8)))
        self.right.frame.pack(side="left", fill="both", expand=True, padx=(S(8), 0))

        foot = tk.Frame(outer, bg=C.BG)
        foot.pack(fill="x", padx=S(18), pady=(S(8), S(12)))

        self.topmost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            foot,
            text="窗口置顶",
            variable=self.topmost_var,
            command=self._toggle_topmost,
            style="Foot.TCheckbutton",
        ).pack(side="left")

        ttk.Label(
            foot,
            text="Esc 紧急停止  ·  拖拽边框改大小  ·  内容可滚动",
            style="Foot.TLabel",
        ).pack(side="right")

        self.panels = (self.left, self.right)
        self._load_or_create_settings()
        self.root.update_idletasks()
        if self._geometry_restored:
            self._clamp_to_screen()
        else:
            self._fit_to_screen()
        self._start_listeners()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._redraw_all)
        self.root.after(100, self._sync_scrollregion)

    def _bind_wheel(self, _event=None) -> None:
        self._scroll.bind_all("<MouseWheel>", self._on_mousewheel)
        self._scroll.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _unbind_wheel(self, _event=None) -> None:
        try:
            self._scroll.unbind_all("<MouseWheel>")
            self._scroll.unbind_all("<Shift-MouseWheel>")
        except tk.TclError:
            pass

    def _on_content_configure(self, _event=None) -> None:
        self._sync_scrollregion()

    def _on_scroll_configure(self, event: tk.Event) -> None:
        # Keep content at least as wide as viewport when window grows
        try:
            need = max(event.width, self._content.winfo_reqwidth())
            self._scroll.itemconfigure(self._content_id, width=need)
        except tk.TclError:
            pass
        self._sync_scrollregion()

    def _sync_scrollregion(self) -> None:
        self._scroll.configure(scrollregion=self._scroll.bbox("all"))

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self._scroll.yview_scroll(int(-event.delta / 120), "units")

    def _on_shift_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self._scroll.xview_scroll(int(-event.delta / 120), "units")

    def _screen_limits(self) -> tuple[int, int]:
        try:
            sw = self.root.winfo_vrootwidth() or self.root.winfo_screenwidth()
            sh = self.root.winfo_vrootheight() or self.root.winfo_screenheight()
        except tk.TclError:
            sw, sh = 1280, 720
        return max(S(720), sw - S(40)), max(S(480), sh - S(60))

    def _fit_to_screen(self) -> None:
        """Size window to content, but never larger than the monitor."""
        self.root.update_idletasks()
        max_w, max_h = self._screen_limits()
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
        except tk.TclError:
            sw, sh = max_w, max_h
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        w = min(max(req_w, S(720)), max_w)
        h = min(max(req_h, S(480)), max_h)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        try:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            self.root.geometry(f"{w}x{h}")

    def _clamp_to_screen(self) -> None:
        """If restored geometry exceeds monitor, shrink it."""
        self.root.update_idletasks()
        max_w, max_h = self._screen_limits()
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
        except tk.TclError:
            return
        nw, nh = min(w, max_w), min(h, max_h)
        if nw != w or nh != h or x < 0 or y < 0:
            self.root.geometry(f"{nw}x{nh}+{max(0, x)}+{max(0, y)}")

    def _collect_settings(self) -> dict:
        return {
            "version": VERSION,
            "topmost": bool(self.topmost_var.get()),
            "geometry": self.root.geometry(),
            "left": self.left.export_settings(),
            "right": self.right.export_settings(),
        }

    def _save_settings(self) -> None:
        path = settings_path()
        try:
            path.write_text(
                json.dumps(self._collect_settings(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _load_or_create_settings(self) -> None:
        path = settings_path()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if "topmost" in data:
                        self.topmost_var.set(bool(data["topmost"]))
                        self._toggle_topmost()
                    self.left.apply_settings(data.get("left"))
                    self.right.apply_settings(data.get("right"))
                    geo = data.get("geometry")
                    if isinstance(geo, str) and "x" in geo:
                        try:
                            self.root.geometry(geo)
                            self._geometry_restored = True
                        except tk.TclError:
                            pass
                    return
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        # Missing or broken → defaults already on widgets; write a fresh file
        self._save_settings()

    def _cancel_other_recording(self, current: ClickPanel) -> None:
        for p in self.panels:
            if p is not current and p.has_bind and p._recording:
                p._finish_recording(None)

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost_var.get())

    def _redraw_all(self) -> None:
        for p in self.panels:
            p._redraw_curve()

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        try:
            if key == keyboard.Key.esc:
                for p in self.panels:
                    if p._recording:
                        p._finish_recording(None)
                        return
                    if p._running:
                        p._bind_held = False
                        p.stop_clicking()
                return
            for p in self.panels:
                if p.handle_bind_press(key):
                    return
        except Exception:
            pass

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        try:
            for p in self.panels:
                if p.handle_bind_release(key):
                    return
        except Exception:
            pass

    def _on_mouse_click(
        self, _x: int, _y: int, button: Button, pressed: bool
    ) -> None:
        try:
            if self._emitting_button is not None:
                return
            # Recording takes priority so double-right won't fire mid-record
            for p in self.panels:
                if p.has_bind and p._recording:
                    if pressed:
                        p.handle_mouse_press(button)
                    return
            for p in self.panels:
                if pressed:
                    p.handle_mouse_press(button)
                else:
                    p.handle_mouse_release(button)
        except Exception:
            pass

    def _start_listeners(self) -> None:
        self._key_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._key_listener.daemon = True
        self._key_listener.start()

        self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def _on_close(self) -> None:
        for p in self.panels:
            p.stop_clicking()
        try:
            self.root.unbind_all("<MouseWheel>")
            self.root.unbind_all("<Shift-MouseWheel>")
        except tk.TclError:
            pass
        self._save_settings()
        if self._key_listener is not None:
            self._key_listener.stop()
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
        self.root.destroy()


def main() -> None:
    # Must run before creating any HWND / Tk window
    enable_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    apply_tk_scaling(root)
    # Allow layout to settle at correct DPI before showing
    root.update_idletasks()
    AutoClickerApp(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
