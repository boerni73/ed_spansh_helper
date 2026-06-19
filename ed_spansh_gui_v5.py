##########################################################################
# DATE              13.06.2026                                           #
#                                                                        #
# AUTHOR            Bernard Härri / Chat AI                              #
#                                                                        #
# COMPILE: pyinstaller --noconsole --onefile ed_spansh_gui.py            #
#                                                                        #
##########################################################################

import os
import json
import time
import glob
import threading
import locale
import math
import webbrowser
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk

import tkinterdnd2
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass


# ----------------------------------------------------------------------
# Default configuration
# ----------------------------------------------------------------------
DEFAULT_JOURNAL_DIR = os.path.expanduser(r"~/Saved Games/Frontier Developments/Elite Dangerous")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "ed_spansh_settings.json")
DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE = os.path.join(os.path.expanduser("~"), "vr_navigation.png")

# ----------------------------------------------------------------------
# Button color constants
# ----------------------------------------------------------------------
BTN_BG          = "#000000"
BTN_BG_ACTIVE   = "#1a1a1a"
BTN_FG_START    = "#00d26a"   # green
BTN_FG_PAUSE    = "#ffd700"   # yellow
BTN_FG_STOP     = "#ff3b30"   # red
BTN_FG_DISABLED = "#3a3a3a"   # grey (for visual hint on disabled)

# ----------------------------------------------------------------------
# Theme definitions
# ----------------------------------------------------------------------
THEMES = {
    "ed_orange": {
        "bg": "#0a0c12",
        "fg": "#f0f0f5",
        "input_bg": "#11141b",
        "input_fg": "#f0f0f5",
        "log_bg": "#06080d",
        "log_fg": "#ff7300",
        "btn_start_bg": "#ff7300",
        "btn_pause_bg": "#cc5c00",
        "btn_stop_bg": "#8c2f00",
        "btn_disabled_bg": "#3a3a3a",
        "btn_fg": "#ffffff",
        "label_fg": "#ff8c2a",
        "value_fg": "#ffd6b3",
        "accent_fg": "#ff7300",
        "panel_bg": "#11141b",
        "panel_border": "#ff7300",
        "lamp_true": "#00d26a",
        "lamp_false": "#ff3b30",
        "lamp_unknown": "#808080",
        "success_fg": "#00d26a",
    }
}


class EdSpanshApp:
    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("Elite Dangerous - Spansh VR Navigator")
        self.root.geometry("750x850")
        self.root.minsize(650, 650)

        self.my_route = []
        self.route_index = 0
        self.monitoring_active = False
        self.is_paused = False
        self.stop_requested = False
        self.total_distance_traveled = 0.0

        (
            self.current_theme_name,
            self.journal_dir,
            self.last_route_file,
            self.kneeboard_output_img_file,
            self.ship_builds_raw,
        ) = self.load_settings()

        self.ship_builds = []

        self.create_menu()
        self.create_widgets()
        self.setup_table_style()
        self.setup_combobox_style()
        self.apply_theme(self.current_theme_name)
        self.setup_drag_and_drop()
        self.load_last_route_on_startup()

    def load_last_route_on_startup(self):
        if not self.last_route_file:
            return

        if not os.path.exists(self.last_route_file):
            self.log(f"Last route file not found: {self.last_route_file}")
            self.last_route_file = ""
            self.save_settings()
            return

        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, self.last_route_file)

        if self.read_route_file():
            self.log(f"Auto-loaded last route file: {self.last_route_file}")

    # ------------------------------------------------------------------
    # Thread / UI helpers
    # ------------------------------------------------------------------
    def ui_call(self, func, *args, **kwargs):
        self.root.after(0, lambda: func(*args, **kwargs))

    def log(self, message):
        self.log_output.insert(tk.END, f"{message}\n")
        self.log_output.see(tk.END)

    def thread_safe_log(self, message):
        self.ui_call(self.log, message)

    # ------------------------------------------------------------------
    # Settings and persistence
    # ------------------------------------------------------------------
    def load_settings(self):
        theme = "ed_orange"
        journal_dir = DEFAULT_JOURNAL_DIR
        route_file = ""
        kneeboard_img_file = DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE
        ship_builds = []

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    theme = settings.get("theme", "ed_orange")
                    journal_dir = settings.get("journal_dir", DEFAULT_JOURNAL_DIR)
                    route_file = settings.get("last_route_file", "")
                    ship_builds = settings.get("ship_builds", [])
                    kneeboard_img_file = settings.get(
                        "kneeboard_output_img_file",
                        DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE
                    )
            except Exception:
                pass

        if theme not in THEMES:
            theme = "ed_orange"

        return theme, journal_dir, route_file, kneeboard_img_file, ship_builds

    def save_settings(self):
        try:
            settings_dir = os.path.dirname(SETTINGS_FILE)
            if settings_dir:
                os.makedirs(settings_dir, exist_ok=True)

            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "theme": self.current_theme_name,
                        "journal_dir": self.journal_dir,
                        "last_route_file": self.last_route_file,
                        "kneeboard_output_img_file": self.kneeboard_output_img_file,
                        "ship_builds": self.ship_builds_raw,
                    },
                    f,
                    indent=2
                )
        except Exception as e:
            self.log(f"Warning: Could not save settings: {e}")

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------
    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            return True
        except Exception as e:
            self.log(f"Clipboard error: {e}")
            return False

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def create_menu(self):
        t = THEMES[self.current_theme_name]

        self.menu_bar = tk.Menu(
            self.root,
            tearoff=0,
            bg=t["panel_bg"],
            fg=t["label_fg"],
            activebackground=t["accent_fg"],
            activeforeground=t["fg"],
        )

        self.settings_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            bg=t["panel_bg"],
            fg=t["fg"],
            activebackground=t["accent_fg"],
            activeforeground=t["fg"],
        )

        self.settings_menu.add_command(
            label="Select ED Journal Directory...",
            command=self.browse_journal_directory,
        )
        self.settings_menu.add_command(
            label="Select Kneeboard Image Output File...",
            command=self.browse_kneeboard_image_file,
        )
        self.settings_menu.add_separator()
        self.settings_menu.add_command(label="Exit", command=self.root.quit)

        self.menu_bar.add_cascade(label="Settings", menu=self.settings_menu)
        self.root.config(menu=self.menu_bar)

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------
    def create_widgets(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # ── Horizontaler Split: links Controls | rechts Log ────────────
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.columnconfigure(0, weight=3)
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.left_frame = tk.Frame(self.content_frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew")

        self.right_frame = tk.Frame(self.content_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        # ── CONTROL BUTTONS (ganz oben, links) ────────────────────────
        self.btn_frame = tk.Frame(self.left_frame)
        self.btn_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.start_btn = tk.Button(
            self.btn_frame,
            text="▶",
            command=self.start_monitoring,
            bg=BTN_BG,
            fg=BTN_FG_START,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_START,
            font=("Arial", 18, "bold"),
            pady=5,
            relief="raised",
            bd=3,
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.pause_btn = tk.Button(
            self.btn_frame,
            text="⏸",
            command=self.toggle_pause,
            bg=BTN_BG,
            fg=BTN_FG_PAUSE,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_PAUSE,
            font=("Arial", 18, "bold"),
            pady=5,
            state="disabled",
            relief="raised",
            bd=3,
        )
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.stop_btn = tk.Button(
            self.btn_frame,
            text="⏹",
            command=self.stop_monitoring,
            bg=BTN_BG,
            fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_STOP,
            font=("Arial", 18, "bold"),
            pady=5,
            state="disabled",
            relief="raised",
            bd=3,
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # ── Spansh tools / ship builds (links) ────────────────────────
        self.ship_build_frame = tk.LabelFrame(
            self.left_frame,
            text=" Spansh Tools ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10,
        )
        self.ship_build_frame.pack(fill="x", expand=False, padx=10, pady=5)

        self.ship_build_top_row = tk.Frame(self.ship_build_frame)
        self.ship_build_top_row.pack(fill="x")

        self.open_spansh_btn = tk.Button(
            self.ship_build_top_row,
            text="Open Spansh",
            command=self.open_spansh_website,
            padx=10
        )
        self.open_spansh_btn.pack(side="left")

        self.ship_build_label = tk.Label(
            self.ship_build_top_row,
            text="Stored Ship Builds:",
            font=("Arial", 9, "bold")
        )
        self.ship_build_label.pack(side="left", padx=(20, 8))

        self.ship_build_var = tk.StringVar()

        self.ship_build_dropdown = ttk.Combobox(
            self.ship_build_top_row,
            textvariable=self.ship_build_var,
            state="readonly",
            width=35,
            style="Orange.TCombobox"
        )
        self.ship_build_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.add_ship_build_small_btn = tk.Button(
            self.ship_build_top_row,
            text="+",
            command=self.open_add_ship_build_dialog,
            width=3
        )
        self.add_ship_build_small_btn.pack(side="left", padx=(0, 4))

        self.remove_ship_build_btn = tk.Button(
            self.ship_build_top_row,
            text="-",
            command=self.remove_selected_ship_build,
            width=3
        )
        self.remove_ship_build_btn.pack(side="left", padx=(0, 8))

        self.copy_ship_build_btn = tk.Button(
            self.ship_build_top_row,
            text="Copy Build JSON",
            command=self.copy_selected_ship_build,
            padx=10
        )
        self.copy_ship_build_btn.pack(side="left")

        # ── Route overview (links) ─────────────────────────────────────
        self.route_info_frame = tk.LabelFrame(
            self.left_frame,
            text=" Route Overview ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10,
        )
        self.route_info_frame.pack(fill="both", expand=False, padx=10, pady=5)

        self.input_label = tk.Label(
            self.route_info_frame,
            text="Select Spansh Route JSON File (or drop it here):",
            font=("Arial", 10, "bold"),
        )
        self.input_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.file_frame = tk.Frame(self.route_info_frame)
        self.file_frame.pack(fill="x", padx=10, pady=5)

        self.file_entry = tk.Entry(
            self.file_frame,
            font=("Consolas", 10),
            bd=2,
            relief="groove",
        )
        self.file_entry.pack(side="left", fill="x", expand=True, ipady=4)

        if self.last_route_file:
            self.file_entry.insert(0, self.last_route_file)

        self.browse_btn = tk.Button(
            self.file_frame,
            text="Browse...",
            command=self.browse_route_file,
            padx=10,
        )
        self.browse_btn.pack(side="right", padx=(5, 0))

        self.lbl_route_type = tk.Label(
            self.route_info_frame,
            text="Route Type: UNKNOWN",
            font=("Arial", 10, "bold"),
            anchor="w",
        )
        self.lbl_route_type.pack(fill="x", pady=(0, 8))

        self.route_table_frame = tk.Frame(self.route_info_frame)
        self.route_table_frame.pack(fill="both", expand=True)

        self.route_table = ttk.Treeview(
            self.route_table_frame,
            columns=("wp_no", "system", "distance", "scoopable", "neutron", "jumps_to"),
            show="headings",
            height=10,
            style="Route.Treeview",
        )

        self.route_table.heading("wp_no",     text="#")
        self.route_table.heading("system",    text="System Name")
        self.route_table.heading("distance",  text="Distance")
        self.route_table.heading("scoopable", text="Scoopable")
        self.route_table.heading("neutron",   text="Neutron Star")
        self.route_table.heading("jumps_to",  text="Jumps to Reach")

        self.route_table.column("wp_no",     width=60,  minwidth=50,  anchor="center")
        self.route_table.column("system",    width=350, minwidth=200, anchor="w")
        self.route_table.column("distance",  width=100, minwidth=80,  anchor="e")
        self.route_table.column("scoopable", width=90,  minwidth=80,  anchor="center")
        self.route_table.column("neutron",   width=100, minwidth=90,  anchor="center")
        self.route_table.column("jumps_to",  width=110, minwidth=90,  anchor="center")

        self.route_table_scroll_y = tk.Scrollbar(
            self.route_table_frame,
            orient="vertical",
            command=self.route_table.yview,
        )
        self.route_table_scroll_x = tk.Scrollbar(
            self.route_table_frame,
            orient="horizontal",
            command=self.route_table.xview,
        )

        self.route_table.configure(
            yscrollcommand=self.route_table_scroll_y.set,
            xscrollcommand=self.route_table_scroll_x.set,
        )

        self.route_table.grid(row=0, column=0, sticky="nsew")
        self.route_table_scroll_y.grid(row=0, column=1, sticky="ns")
        self.route_table_scroll_x.grid(row=1, column=0, sticky="ew")

        self.route_table_frame.rowconfigure(0, weight=1)
        self.route_table_frame.columnconfigure(0, weight=1)

        self.route_table_item_ids = []
        self.route_table_row_data = []
        # ── Cockpit navigation preview (links) ────────────────────────
        self.dash_frame = tk.LabelFrame(
            self.left_frame,
            text=" Cockpit Navigation Display ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10,
        )
        self.dash_frame.pack(fill="both", expand=False, padx=10, pady=5)

        self.dashboard_image_label = tk.Label(
            self.dash_frame,
            text="Waiting for navigation image...",
            font=("Consolas", 12, "bold"),
            anchor="center",
            justify="center",
        )
        self.dashboard_image_label.pack(fill="both", expand=True)

        self.dashboard_photo = None

        # ── Log output (rechts) ────────────────────────────────────────
        self.output_label = tk.Label(
            self.right_frame,
            text="Log Output and Status:",
            font=("Arial", 10, "bold"),
        )
        self.output_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.log_output = scrolledtext.ScrolledText(
            self.right_frame,
            font=("Consolas", 10),
            wrap="word",
            relief="flat",
            bd=4,
        )
        self.log_output.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.refresh_ship_build_dropdown()

    def open_add_ship_build_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Ship Build")
        dialog.geometry("700x420")
        dialog.minsize(500, 300)
        dialog.transient(self.root)
        dialog.grab_set()

        t = THEMES[self.current_theme_name]
        dialog.config(bg=t["bg"])

        title_label = tk.Label(
            dialog,
            text="Paste Ship Build JSON",
            font=("Arial", 11, "bold"),
            bg=t["bg"],
            fg=t["label_fg"]
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 4))

        info_label = tk.Label(
            dialog,
            text="Paste the full ship build JSON and click 'Add Build'.",
            font=("Arial", 9),
            bg=t["bg"],
            fg=t["fg"]
        )
        info_label.pack(anchor="w", padx=10, pady=(0, 8))

        text_widget = scrolledtext.ScrolledText(
            dialog,
            height=16,
            font=("Consolas", 9),
            wrap="word",
            relief="flat",
            bd=4,
            bg=t["input_bg"],
            fg=t["input_fg"],
            insertbackground=t["input_fg"]
        )
        text_widget.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        button_row = tk.Frame(dialog, bg=t["bg"])
        button_row.pack(fill="x", padx=10, pady=(0, 10))

        def add_and_close():
            raw_text = text_widget.get("1.0", tk.END).strip()
            if not raw_text:
                messagebox.showwarning("No Input", "Please paste a ship build JSON first.", parent=dialog)
                return

            try:
                json.loads(raw_text)
            except Exception as e:
                messagebox.showerror("Invalid JSON", f"Ship build JSON is invalid:\n{e}", parent=dialog)
                return

            ship_name = self.extract_ship_name_from_build(raw_text)

            for existing in self.ship_builds:
                if existing["raw"] == raw_text:
                    self.log(f"Ship build already exists: {ship_name}")
                    self.refresh_ship_build_dropdown()
                    self.ship_build_var.set(ship_name)
                    dialog.destroy()
                    return

            self.ship_builds_raw.append(raw_text)
            self.save_settings()
            self.refresh_ship_build_dropdown()
            self.ship_build_var.set(ship_name)
            self.log(f"Added ship build: {ship_name}")
            dialog.destroy()

        cancel_btn = tk.Button(
            button_row,
            text="Cancel",
            command=dialog.destroy,
            bg=t["btn_stop_bg"],
            fg=t["btn_fg"],
            activebackground="#aa3a00",
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=4
        )
        cancel_btn.pack(side="right", padx=(6, 0))

        add_btn = tk.Button(
            button_row,
            text="Add Build",
            command=add_and_close,
            bg=t["btn_start_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=4
        )
        add_btn.pack(side="right")

    def remove_selected_ship_build(self):
        selected_name = self.ship_build_var.get().strip()
        if not selected_name:
            messagebox.showwarning("No Selection", "Please select a ship build first.")
            return

        selected_entry = None
        for entry in self.ship_builds:
            if entry["name"] == selected_name:
                selected_entry = entry
                break

        if not selected_entry:
            messagebox.showerror("Build Not Found", "The selected ship build could not be found.")
            return

        confirm = messagebox.askyesno(
            "Delete Ship Build",
            f"Do you really want to delete the ship build '{selected_name}'?"
        )
        if not confirm:
            return

        self.ship_builds_raw = [
            raw for raw in self.ship_builds_raw
            if raw != selected_entry["raw"]
        ]

        self.save_settings()
        self.refresh_ship_build_dropdown()
        self.log(f"Deleted ship build: {selected_name}")

    # ------------------------------------------------------------------
    # Theme and styles
    # ------------------------------------------------------------------
    def setup_table_style(self):
        t = THEMES[self.current_theme_name]
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Route.Treeview",
            background=t["panel_bg"],
            fieldbackground=t["panel_bg"],
            foreground=t["value_fg"],
            bordercolor=t["panel_border"],
            borderwidth=1,
            rowheight=24,
            relief="flat",
        )

        style.configure(
            "Route.Treeview.Heading",
            background=t["btn_pause_bg"],
            foreground=t["fg"],
            relief="flat",
            borderwidth=1,
            font=("Arial", 9, "bold"),
        )

        style.map(
            "Route.Treeview",
            background=[("selected", t["accent_fg"])],
            foreground=[("selected", "#000000")],
        )

        style.map(
            "Route.Treeview.Heading",
            background=[("active", t["btn_start_bg"])],
            foreground=[("active", "#ffffff")],
        )
    def apply_theme(self, theme_name):
        t = THEMES[theme_name]

        self.root.config(bg=t["bg"])
        self.main_frame.config(bg=t["bg"])
        self.file_frame.config(bg=t["bg"])
        self.btn_frame.config(bg=t["bg"])

        # ── Neue Frames einfärben ──────────────────────────────────────
        self.content_frame.config(bg=t["bg"])
        self.left_frame.config(bg=t["bg"])
        self.right_frame.config(bg=t["bg"])

        self.input_label.config(bg=t["bg"], fg=t["label_fg"])
        self.output_label.config(bg=t["bg"], fg=t["label_fg"])

        # ── Spansh tools section ────────────────────────────────────────
        self.ship_build_frame.config(
            bg=t["panel_bg"],
            fg=t["label_fg"],
            bd=2,
            relief="groove"
        )
        self.ship_build_top_row.config(bg=t["panel_bg"])
        self.ship_build_label.config(bg=t["panel_bg"], fg=t["label_fg"])

        self.open_spansh_btn.config(
            bg=t["btn_start_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0
        )

        self.copy_ship_build_btn.config(
            bg=t["btn_pause_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_start_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0
        )

        self.add_ship_build_small_btn.config(
            bg=t["btn_start_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0
        )

        self.remove_ship_build_btn.config(
            bg=t["btn_stop_bg"],
            fg=t["btn_fg"],
            activebackground="#aa3a00",
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0
        )

        # ── Route overview section ──────────────────────────────────────
        self.route_info_frame.config(
            bg=t["panel_bg"],
            fg=t["label_fg"],
            bd=2,
            relief="groove"
        )
        self.lbl_route_type.config(
            bg=t["panel_bg"],
            fg=t["accent_fg"]
        )
        self.route_table_frame.config(bg=t["panel_bg"])

        # ── Cockpit preview section ─────────────────────────────────────
        self.dash_frame.config(
            bg=t["panel_bg"],
            fg=t["label_fg"],
            bd=2,
            relief="groove"
        )

        for child in self.dash_frame.winfo_children():
            try:
                child.config(bg=t["panel_bg"], fg=t["fg"])
            except Exception:
                pass

        self.dashboard_image_label.config(
            bg=t["panel_bg"],
            fg=t["accent_fg"]
        )

        # ── Inputs and log ──────────────────────────────────────────────
        self.file_entry.config(
            bg=t["input_bg"],
            fg=t["input_fg"],
            insertbackground=t["input_fg"],
            relief="flat",
            bd=6
        )

        self.log_output.config(
            bg=t["log_bg"],
            fg=t["log_fg"],
            insertbackground=t["log_fg"],
            relief="flat",
            bd=6
        )

        self.browse_btn.config(
            bg=t["btn_start_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0
        )

        # ── Transport buttons (Schwarz / farbige Icons) ─────────────────
        # Relief wird NICHT überschrieben – er zeigt den aktuellen Zustand
        self.start_btn.config(
            bg=BTN_BG,
            fg=BTN_FG_START,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_START,
            bd=3,
        )

        self.pause_btn.config(
            bg=BTN_BG,
            fg=BTN_FG_PAUSE,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_PAUSE,
            bd=3,
        )

        self.stop_btn.config(
            bg=BTN_BG,
            fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE,
            activeforeground=BTN_FG_STOP,
            bd=3,
        )

        # ── Scrollbars ──────────────────────────────────────────────────
        try:
            self.route_table_scroll_y.config(
                bg=t["panel_bg"],
                activebackground=t["btn_start_bg"],
                troughcolor=t["bg"],
                bd=0,
                relief="flat"
            )
            self.route_table_scroll_x.config(
                bg=t["panel_bg"],
                activebackground=t["btn_start_bg"],
                troughcolor=t["bg"],
                bd=0,
                relief="flat"
            )
        except Exception:
            pass

        # ── ttk styles ──────────────────────────────────────────────────
        self.setup_table_style()
        self.setup_combobox_style()

        # ── Route table highlight tags ──────────────────────────────────
        try:
            self.route_table.tag_configure(
                "current_system",
                background="#402200",
                foreground="#ffd6b3"
            )
            self.route_table.tag_configure(
                "next_waypoint",
                background="#ff8c2a",
                foreground="#000000"
            )
        except Exception:
            pass

        # ── Native menu styling (best effort) ───────────────────────────
        try:
            self.menu_bar.config(
                bg=t["panel_bg"],
                fg=t["label_fg"],
                activebackground=t["accent_fg"],
                activeforeground=t["fg"]
            )
            self.settings_menu.config(
                bg=t["panel_bg"],
                fg=t["fg"],
                activebackground=t["accent_fg"],
                activeforeground=t["fg"]
            )
        except Exception:
            pass

    def _update_transport_btn_states(self):
        """Setzt relief der drei Transport-Buttons passend zum aktuellen Zustand."""
        # Start-Button: gedrückt wenn Monitoring läuft
        self.start_btn.config(
            relief="sunken" if self.monitoring_active else "raised"
        )
        # Pause-Button: gedrückt wenn pausiert
        self.pause_btn.config(
            relief="sunken" if self.is_paused else "raised"
        )
        # Stop-Button: immer raised (momentary action)
        self.stop_btn.config(relief="raised")
    def refresh_dashboard_image(self):
        try:
            if not os.path.exists(self.kneeboard_output_img_file):
                return

            img = Image.open(self.kneeboard_output_img_file)

            max_width = 700
            max_height = 320
            width, height = img.size
            scale = min(max_width / width, max_height / height, 1.0)
            new_size = (int(width * scale), int(height * scale))

            if new_size != img.size:
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            self.dashboard_photo = ImageTk.PhotoImage(img)
            self.dashboard_image_label.config(image=self.dashboard_photo, text="")
        except Exception as e:
            self.log(f"Dashboard image refresh error: {e}")

    def update_dashboard(self, next_sys=None, jumps_left=None, final_tgt=None, is_scoopable=None, has_neutron=None):
        self.refresh_dashboard_image()

    def reset_dashboard(self):
        self.dashboard_image_label.config(image="", text="Waiting for navigation image...")
        self.dashboard_photo = None

    # ------------------------------------------------------------------
    # Drag and drop / file input
    # ------------------------------------------------------------------
    def setup_drag_and_drop(self):
        self.file_entry.drop_target_register(DND_FILES)
        self.file_entry.dnd_bind("<<Drop>>", self.handle_drop)

        self.log_output.drop_target_register(DND_FILES)
        self.log_output.dnd_bind("<<Drop>>", self.handle_drop)

    def handle_drop(self, event):
        file_path = event.data
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]

        file_path = os.path.normpath(file_path)

        if file_path.lower().endswith(".json"):
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            self.last_route_file = file_path
            self.save_settings()
            self.log(f"File dropped: {file_path}")
        else:
            messagebox.showerror("Invalid File", "Please drop a valid .json route file.")

    def browse_journal_directory(self):
        selected_dir = filedialog.askdirectory(
            initialdir=self.journal_dir,
            title="Select ED Journal Directory"
        )
        if selected_dir:
            self.journal_dir = os.path.normpath(selected_dir)
            self.save_settings()
            self.log(f"Journal directory updated to: {self.journal_dir}")

    def browse_route_file(self):
        initial_dir = os.path.dirname(self.last_route_file) if self.last_route_file else os.path.expanduser("~")
        selected_file = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select Spansh Route JSON",
            filetypes=[("JSON Files", "*.json")],
        )
        if selected_file:
            self.last_route_file = os.path.normpath(selected_file)
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, self.last_route_file)
            self.save_settings()
            self.log(f"Selected route file: {self.last_route_file}")

    def browse_kneeboard_image_file(self):
        initial_dir = (
            os.path.dirname(self.kneeboard_output_img_file)
            if self.kneeboard_output_img_file
            else os.path.expanduser("~")
        )
        initial_file = (
            os.path.basename(self.kneeboard_output_img_file)
            if self.kneeboard_output_img_file
            else "vr_navigation.png"
        )

        selected_file = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=initial_file,
            title="Select Kneeboard Image Output File",
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")],
        )

        if selected_file:
            self.kneeboard_output_img_file = os.path.normpath(selected_file)
            self.save_settings()
            self.log(f"Kneeboard image output file updated to: {self.kneeboard_output_img_file}")

    # ------------------------------------------------------------------
    # Route table helpers
    # ------------------------------------------------------------------
    def clear_route_table(self):
        for item_id in self.route_table.get_children():
            self.route_table.delete(item_id)

        self.route_table_item_ids = []
        self.route_table_row_data = []

    def populate_route_table(self, route_rows, route_type="UNKNOWN"):
        self.clear_route_table()
        self.lbl_route_type.config(text=f"Route Type: {route_type}")
        self.route_table_row_data = []

        for row in route_rows:
            waypoint_no   = row.get("waypoint_no", "")
            system_name   = row.get("system_name", "")
            distance      = row.get("distance", 0.0)
            scoopable     = row.get("scoopable", None)
            neutron_star  = row.get("neutron_star", False)
            jumps_to_reach = row.get("jumps_to_reach", 0)

            scoopable_text = "-" if scoopable is None else ("Yes" if scoopable else "No")
            neutron_text   = "Yes" if neutron_star else "No"
            distance_text  = f"{distance:.1f} LY" if isinstance(distance, (int, float)) else str(distance)

            item_id = self.route_table.insert(
                "",
                "end",
                values=(
                    waypoint_no,
                    system_name,
                    distance_text,
                    scoopable_text,
                    neutron_text,
                    jumps_to_reach,
                ),
            )

            self.route_table_item_ids.append(item_id)
            self.route_table_row_data.append(
                {
                    "item_id":       item_id,
                    "waypoint_no":   waypoint_no,
                    "system_name":   str(system_name),
                    "distance":      distance,
                    "scoopable":     scoopable,
                    "neutron_star":  neutron_star,
                    "jumps_to_reach": jumps_to_reach,
                }
            )

        self.route_table.tag_configure(
            "current_system",
            background="#4a2a00",
            foreground="#ffd6b3",
        )
        self.route_table.tag_configure(
            "next_waypoint",
            background="#ff7300",
            foreground="#000000",
        )

    def highlight_route_table(self, current_system, next_waypoint):
        for item_id in self.route_table.get_children():
            self.route_table.item(item_id, tags=())

        next_matches = []

        current_system_lc = str(current_system).strip().lower() if current_system else ""
        next_waypoint_lc  = str(next_waypoint).strip().lower()  if next_waypoint  else ""

        for idx, row in enumerate(self.route_table_row_data):
            system_name_lc = row["system_name"].strip().lower()

            if current_system_lc and system_name_lc == current_system_lc:
                self.route_table.item(row["item_id"], tags=("current_system",))

            if next_waypoint_lc and system_name_lc == next_waypoint_lc:
                self.route_table.item(row["item_id"], tags=("next_waypoint",))
                next_matches.append(idx)

        if next_matches:
            next_index = next_matches[0]
            visible_target_index = max(0, next_index - 2)

            total_rows = len(self.route_table_row_data)
            if total_rows > 0:
                self.route_table.yview_moveto(visible_target_index / total_rows)

            next_item_id = self.route_table_row_data[next_index]["item_id"]
            self.route_table.selection_set(next_item_id)
            self.route_table.focus(next_item_id)

    def setup_combobox_style(self):
        t = THEMES[self.current_theme_name]
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Orange.TCombobox",
            fieldbackground=t["input_bg"],
            background=t["panel_bg"],
            foreground=t["input_fg"],
            arrowcolor=t["accent_fg"],
            bordercolor=t["panel_border"],
            lightcolor=t["panel_border"],
            darkcolor=t["panel_border"]
        )
    def open_spansh_website(self):
        try:
            webbrowser.open("https://spansh.co.uk")
            self.log("Opened https://spansh.co.uk in the default browser.")
        except Exception as e:
            messagebox.showerror("Browser Error", f"Could not open browser:\n{e}")

    def extract_ship_name_from_build(self, raw_json_text):
        try:
            parsed = json.loads(raw_json_text)

            if isinstance(parsed, list) and parsed:
                first = parsed[0]
                if isinstance(first, dict):
                    ship_name = first.get("data", {}).get("ShipName")
                    if ship_name:
                        return str(ship_name)

            if isinstance(parsed, dict):
                ship_name = parsed.get("data", {}).get("ShipName")
                if ship_name:
                    return str(ship_name)

        except Exception:
            pass

        return "Unnamed Build"

    def rebuild_ship_build_index(self):
        self.ship_builds = []

        for raw in self.ship_builds_raw:
            ship_name = self.extract_ship_name_from_build(raw)
            self.ship_builds.append({
                "name": ship_name,
                "raw":  raw
            })

    def refresh_ship_build_dropdown(self):
        self.rebuild_ship_build_index()

        names = [entry["name"] for entry in self.ship_builds]
        self.ship_build_dropdown["values"] = names

        if names:
            self.ship_build_var.set(names[0])
        else:
            self.ship_build_var.set("")

    def copy_selected_ship_build(self):
        selected_name = self.ship_build_var.get().strip()
        if not selected_name:
            messagebox.showwarning("No Selection", "Please select a ship build first.")
            return

        for entry in self.ship_builds:
            if entry["name"] == selected_name:
                if self.copy_to_clipboard(entry["raw"]):
                    self.log(f"Copied ship build to clipboard: {selected_name}")
                return

        messagebox.showerror("Build Not Found", "The selected ship build could not be found.")

    # ------------------------------------------------------------------
    # Route parsing
    # ------------------------------------------------------------------
    def build_route_table_data(self, route_type, raw_jumps):
        route_rows = []

        if route_type == "Galaxy Plotter":
            for i, item in enumerate(raw_jumps):
                if not isinstance(item, dict):
                    continue

                system_name = item.get("name")
                if not system_name:
                    continue

                route_rows.append(
                    {
                        "waypoint_no":   i + 1,
                        "system_name":   str(system_name),
                        "distance":      float(item.get("distance", 0.0) or 0.0),
                        "scoopable":     None if item.get("is_scoopable", None) is None
                                         else bool(item.get("is_scoopable")),
                        "neutron_star":  bool(item.get("has_neutron", False)),
                        "jumps_to_reach": i,
                    }
                )

        elif route_type == "Neutron Plotter":
            cumulative_jumps = 0

            for i, item in enumerate(raw_jumps):
                if not isinstance(item, dict):
                    continue

                system_name = item.get("system")
                if not system_name:
                    continue

                jumps_this_leg   = int(item.get("jumps", 0) or 0)
                cumulative_jumps = 0 if i == 0 else cumulative_jumps + jumps_this_leg

                route_rows.append(
                    {
                        "waypoint_no":    i + 1,
                        "system_name":    str(system_name),
                        "distance":       float(item.get("distance_jumped", 0.0) or 0.0),
                        "scoopable":      None,
                        "neutron_star":   bool(item.get("neutron_star", False)),
                        "jumps_to_reach": cumulative_jumps,
                    }
                )

        else:
            cumulative_jumps = 0

            for i, item in enumerate(raw_jumps):
                if not isinstance(item, dict):
                    continue

                system_name = item.get("name") or item.get("system") or item.get("system_name")
                if not system_name:
                    continue

                distance = item.get("distance", 0.0)
                if "distance_to_star" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_to_star", 0.0)
                distance = float(distance or 0.0)

                scoopable = item.get("is_scoopable", item.get("scoopable", None))

                neutron_star = item.get("has_neutron", False)
                if item.get("neutron_star") or item.get("star_type") == "N" or item.get("star_class") == "N":
                    neutron_star = True

                jumps_this_leg   = int(item.get("jumps", 1) or 1)
                cumulative_jumps = 0 if i == 0 and distance == 0 else cumulative_jumps + jumps_this_leg

                route_rows.append(
                    {
                        "waypoint_no":    i + 1,
                        "system_name":    str(system_name),
                        "distance":       distance,
                        "scoopable":      None if scoopable is None else bool(scoopable),
                        "neutron_star":   bool(neutron_star),
                        "jumps_to_reach": cumulative_jumps,
                    }
                )

        return route_rows

    def read_route_file(self):
        file_path = self.file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select or drop a valid existing route JSON file first!")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                route_data = json.load(f)

            raw_jumps  = []
            route_type = "Unknown Spansh Route"

            if "result" in route_data and "jumps" in route_data["result"]:
                raw_jumps  = route_data["result"]["jumps"]
                route_type = "Galaxy Plotter"
            elif "result" in route_data and "system_jumps" in route_data["result"]:
                raw_jumps  = route_data["result"]["system_jumps"]
                route_type = "Neutron Plotter"
            elif "jumps" in route_data:
                raw_jumps  = route_data["jumps"]
                route_type = "Standard Jump Route"
            elif "systems" in route_data:
                raw_jumps  = route_data["systems"]
                route_type = "Road to Riches / Exobiology"
            elif "result" in route_data and "systems" in route_data["result"]:
                raw_jumps  = route_data["result"]["systems"]
                route_type = "Road to Riches / Exobiology (API)"
            elif "route" in route_data:
                raw_jumps  = route_data["route"]
                route_type = "Fleet Carrier Route"
            else:
                raise ValueError("Unknown Spansh JSON structure. Could not find jumps or systems list.")

            parsed_route = []
            for item in raw_jumps:
                if not isinstance(item, dict):
                    continue

                name = item.get("name") or item.get("system") or item.get("system_name")
                if not name:
                    continue

                distance = item.get("distance", 0.0)
                if "distance_to_star" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_to_star", 0.0)
                if "distance_jumped" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_jumped", 0.0)

                is_scoopable = item.get("is_scoopable", item.get("scoopable", None))

                has_neutron = item.get("has_neutron", False)
                if item.get("neutron_star") or item.get("star_type") == "N" or item.get("star_class") == "N":
                    has_neutron = True

                parsed_route.append(
                    {
                        "name":        str(name),
                        "is_scoopable": None if is_scoopable is None else bool(is_scoopable),
                        "has_neutron": bool(has_neutron),
                        "distance":    float(distance or 0.0),
                        "x":           float(item.get("x", 0.0) or 0.0),
                        "y":           float(item.get("y", 0.0) or 0.0),
                        "z":           float(item.get("z", 0.0) or 0.0),
                    }
                )

            if not parsed_route:
                raise ValueError("No valid systems could be parsed from the file.")

            self.my_route    = parsed_route
            self.route_index = 0
            self.last_route_file = file_path

            route_rows = self.build_route_table_data(route_type, raw_jumps)
            self.populate_route_table(route_rows, route_type=route_type)

        except Exception as e:
            messagebox.showerror("JSON Error", f"Failed to read or parse the JSON file:\n{e}")
            return False

        self.log(f"Successfully loaded and standardized {route_type} with {len(self.my_route)} route entries.")
        self.save_settings()
        return True
    # ------------------------------------------------------------------
    # Route logic
    # ------------------------------------------------------------------
    def distance(self, destination_coord, current_coord):
        dest_x,    dest_y,    dest_z    = destination_coord
        current_x, current_y, current_z = current_coord

        dx = dest_x - current_x
        dy = dest_y - current_y
        dz = dest_z - current_z

        return round(math.sqrt(dx ** 2 + dy ** 2 + dz ** 2), 0)

    def find_next_waypoint(self, system_name, current_coordinates):
        if not self.my_route:
            return None

        current_index = -1
        on_route      = False

        for i, jump in enumerate(self.my_route):
            if jump["name"].lower() == system_name.lower():
                current_index = i
                on_route      = True
                break

        if current_index == -1:
            self.log("Current system not in route, searching closest system...")

            min_distance  = float("inf")
            closest_index = -1

            for i, jump in enumerate(self.my_route):
                dist = self.distance((jump["x"], jump["y"], jump["z"]), current_coordinates)
                if dist < min_distance:
                    min_distance  = dist
                    closest_index = i

            current_index = closest_index

            if current_index != -1:
                self.log(f"Closest system in route is {self.my_route[current_index]['name']} ({min_distance} LY)")
                if current_index > 0:
                    current_index -= 1

        if current_index == -1:
            return None

        self.route_index = current_index + 1

        if self.route_index >= len(self.my_route):
            return "ROUTE_FINISHED"

        next_system     = self.my_route[self.route_index]
        remaining_route = self.my_route[self.route_index:]

        next_wp_coord = (
            next_system.get("x", 0.0),
            next_system.get("y", 0.0),
            next_system.get("z", 0.0),
        )
        final_destination_coord = (
            remaining_route[-1]["x"],
            remaining_route[-1]["y"],
            remaining_route[-1]["z"],
        )

        return (
            next_system["name"],
            next_system.get("is_scoopable", None),
            next_system.get("has_neutron", False),
            self.distance(next_wp_coord, current_coordinates),
            len(remaining_route),
            remaining_route[-1]["name"],
            self.distance(final_destination_coord, current_coordinates),
            on_route,
        )

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------
    def _get_text_width(self, draw, text, font):
        bbox = draw.textbbox((0, 0), str(text), font=font)
        return bbox[2] - bbox[0]

    def _fit_font(self, draw, text, font_name, start_size, min_size, max_width):
        text = str(text)

        for size in range(start_size, min_size - 1, -1):
            try:
                font = ImageFont.truetype(font_name, size)
            except IOError:
                return ImageFont.load_default()

            if self._get_text_width(draw, text, font) <= max_width:
                return font

        try:
            return ImageFont.truetype(font_name, min_size)
        except IOError:
            return ImageFont.load_default()

    def gen_galaxy_plotter_image(
        self,
        current_system,
        current_system_on_route,
        system_name,
        destination,
        jump_distance,
        jumps_remain,
        distance_remain,
        distance_traveled,
        scoopable_star,
        neutron_star,
    ):
        img_width  = 1000
        img_height = 445

        bg_color     = (6, 8, 12)
        line_dim     = (80, 40, 0)
        ed_orange    = (255, 115, 0)
        ed_orange_soft = (220, 100, 0)
        ed_orange_dim  = (150, 70, 0)
        ed_cyan      = (89, 223, 227)
        color_on     = (40, 210, 110)
        color_off    = (231, 76, 60)
        color_unknown = (128, 128, 128)
        font_name    = "arial.ttf"

        try:
            font_big    = ImageFont.truetype(font_name, 28)
            font_medium = ImageFont.truetype(font_name, 22)
            font_small  = ImageFont.truetype(font_name, 19)
        except IOError:
            font_big    = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small  = ImageFont.load_default()

        img  = Image.new("RGB", (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)

        title_text   = f"NAVIGATION TO: {str(destination).upper()}"
        title_font   = self._fit_font(draw, title_text, font_name, start_size=22, min_size=14, max_width=740)
        current_text = str(current_system).upper()
        current_font = self._fit_font(draw, current_text, font_name, start_size=38, min_size=20, max_width=900)
        next_text    = f"{str(system_name).upper()} ({jump_distance:.0f} LY)"
        next_font    = self._fit_font(draw, next_text, font_name, start_size=38, min_size=20, max_width=680)

        draw.rectangle([(10, 10), (990, 435)], outline=ed_orange,     width=2)
        draw.rectangle([(22, 22), (978, 423)], outline=ed_orange_dim, width=1)

        draw.line([(35, 68),  (965, 68)],  fill=ed_orange_dim, width=1)
        draw.line([(35, 160), (965, 160)], fill=line_dim,       width=1)
        draw.line([(35, 315), (965, 315)], fill=line_dim,       width=1)

        draw.text((40, 28), title_text, fill=ed_orange, font=title_font)

        route_status_text  = "ON ROUTE" if current_system_on_route else "OFF ROUTE"
        route_status_color = color_on   if current_system_on_route else color_off

        route_dot_y = 30
        draw.ellipse([(820, route_dot_y), (846, route_dot_y + 26)], fill=route_status_color)
        draw.text((860, route_dot_y + 1), route_status_text, fill=ed_orange, font=font_medium)

        draw.text((45, 82),  "CURRENT SYSTEM", fill=ed_orange_soft, font=font_small)
        draw.text((45, 108), current_text,      fill=ed_cyan,        font=current_font)

        draw.text((45, 178), "NEXT WAYPOINT", fill=ed_orange_soft, font=font_small)
        draw.text((45, 205), next_text,        fill=ed_orange,      font=next_font)

        scoop_color = color_unknown if scoopable_star is None else (color_on if scoopable_star else color_off)
        neutron_color = color_on if neutron_star else color_off

        draw.ellipse([(55,  265), (81,  291)], fill=scoop_color)
        draw.text((95,  266), "SCOOPABLE",    fill=ed_orange, font=font_medium)
        draw.ellipse([(310, 265), (336, 291)], fill=neutron_color)
        draw.text((350, 266), "NEUTRON STAR", fill=ed_orange, font=font_medium)

        metric_label_y = 335
        metric_value_y = 362

        draw.text((70,  metric_label_y), "JUMPS LEFT",          fill=ed_orange_dim, font=font_small)
        draw.text((70,  metric_value_y), f"{jumps_remain}",      fill=ed_orange,     font=font_big)
        draw.text((370, metric_label_y), "DISTANCE REMAINING",  fill=ed_orange_dim, font=font_small)
        draw.text((370, metric_value_y), f"{distance_remain:n} LY", fill=ed_orange, font=font_big)
        draw.text((690, metric_label_y), "TRAVELED",            fill=ed_orange_dim, font=font_small)
        draw.text((690, metric_value_y), f"{distance_traveled:n} LY", fill=ed_orange, font=font_big)

        draw.line([(320, 330), (320, 400)], fill=line_dim, width=1)
        draw.line([(645, 330), (645, 400)], fill=line_dim, width=1)

        # Corner brackets
        for x1, y1, x2, y2, dx, dy in [
            (22, 22, 52, 22, 22, 52), (22, 22, 22, 52, 22, 52),
            (948, 22, 978, 22, 978, 52), (978, 22, 978, 52, 978, 52),
            (22, 393, 22, 423, 52, 423), (22, 423, 52, 423, 52, 423),
            (948, 423, 978, 423, 978, 423), (978, 393, 978, 423, 978, 423),
        ]:
            draw.line([(x1, y1), (x2, y2)], fill=ed_orange, width=2)

        output_dir = os.path.dirname(self.kneeboard_output_img_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        img.save(self.kneeboard_output_img_file)
    def gen_destination_reached_image(
        self,
        current_system,
        current_system_on_route,
        destination,
        jumps_remain,
        distance_remain,
        distance_traveled,
    ):
        img_width  = 1000
        img_height = 445

        bg_color       = (6, 8, 12)
        line_dim       = (80, 40, 0)
        ed_orange      = (255, 115, 0)
        ed_orange_soft = (220, 100, 0)
        ed_orange_dim  = (150, 70, 0)
        ed_cyan        = (89, 223, 227)
        color_on       = (40, 210, 110)
        color_off      = (231, 76, 60)
        font_name      = "arial.ttf"

        try:
            font_big    = ImageFont.truetype(font_name, 28)
            font_medium = ImageFont.truetype(font_name, 22)
            font_small  = ImageFont.truetype(font_name, 19)
        except IOError:
            font_big    = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small  = ImageFont.load_default()

        img  = Image.new("RGB", (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)

        title_text   = f"NAVIGATION TO: {str(destination).upper()}"
        title_font   = self._fit_font(draw, title_text, font_name, start_size=22, min_size=14, max_width=740)
        current_text = str(current_system).upper()
        current_font = self._fit_font(draw, current_text, font_name, start_size=38, min_size=20, max_width=900)
        next_text    = "DESTINATION REACHED"
        next_font    = self._fit_font(draw, next_text,    font_name, start_size=38, min_size=20, max_width=680)

        draw.rectangle([(10, 10), (990, 435)], outline=ed_orange,     width=2)
        draw.rectangle([(22, 22), (978, 423)], outline=ed_orange_dim, width=1)

        draw.line([(35, 68),  (965, 68)],  fill=ed_orange_dim, width=1)
        draw.line([(35, 160), (965, 160)], fill=line_dim,       width=1)
        draw.line([(35, 315), (965, 315)], fill=line_dim,       width=1)

        draw.text((40, 28), title_text, fill=ed_orange, font=title_font)

        route_dot_y = 30
        draw.ellipse([(820, route_dot_y), (846, route_dot_y + 26)], fill=color_on)
        draw.text((860, route_dot_y + 1), "REACHED", fill=ed_orange, font=font_medium)

        draw.text((45, 82),  "CURRENT SYSTEM", fill=ed_orange_soft, font=font_small)
        draw.text((45, 108), current_text,      fill=ed_cyan,        font=current_font)
        draw.text((45, 205), next_text,          fill=color_on,       font=next_font)

        metric_label_y = 335
        metric_value_y = 362

        draw.text((70,  metric_label_y), "JUMPS LEFT",             fill=ed_orange_dim, font=font_small)
        draw.text((70,  metric_value_y), f"{jumps_remain}",         fill=ed_orange,     font=font_big)
        draw.text((370, metric_label_y), "DISTANCE REMAINING",     fill=ed_orange_dim, font=font_small)
        draw.text((370, metric_value_y), f"{distance_remain:n} LY", fill=ed_orange,     font=font_big)
        draw.text((690, metric_label_y), "TRAVELED",               fill=ed_orange_dim, font=font_small)
        draw.text((690, metric_value_y), f"{distance_traveled:n} LY", fill=ed_orange,  font=font_big)

        draw.line([(320, 330), (320, 400)], fill=line_dim, width=1)
        draw.line([(645, 330), (645, 400)], fill=line_dim, width=1)

        # Corner brackets
        draw.line([(22,  22),  (52,  22)],  fill=ed_orange, width=2)
        draw.line([(22,  22),  (22,  52)],  fill=ed_orange, width=2)
        draw.line([(948, 22),  (978, 22)],  fill=ed_orange, width=2)
        draw.line([(978, 22),  (978, 52)],  fill=ed_orange, width=2)
        draw.line([(22,  393), (22,  423)], fill=ed_orange, width=2)
        draw.line([(22,  423), (52,  423)], fill=ed_orange, width=2)
        draw.line([(948, 423), (978, 423)], fill=ed_orange, width=2)
        draw.line([(978, 393), (978, 423)], fill=ed_orange, width=2)

        output_dir = os.path.dirname(self.kneeboard_output_img_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        img.save(self.kneeboard_output_img_file)

    # ------------------------------------------------------------------
    # Monitoring controls
    # ------------------------------------------------------------------
    def start_monitoring(self):
        if self.monitoring_active:
            return

        if not self.read_route_file():
            return

        self.total_distance_traveled = 0.0
        self.monitoring_active = True
        self.stop_requested    = False
        self.is_paused         = False

        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        self._update_transport_btn_states()

        threading.Thread(target=self.monitor_journal, daemon=True).start()

    def toggle_pause(self):
        if not self.monitoring_active:
            return

        self.is_paused = not self.is_paused
        self._update_transport_btn_states()

        if self.is_paused:
            self.log("Monitor paused. Events will be ignored.")
        else:
            self.log("Monitor resumed. Waiting for events.")

    def stop_monitoring(self, preserve_arrived_state=False):
        if not self.monitoring_active and not preserve_arrived_state:
            return

        self.stop_requested    = True
        self.monitoring_active = False
        self.is_paused         = False

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self._update_transport_btn_states()

        if not preserve_arrived_state:
            self.reset_dashboard()

        self.log("Monitor stopped.")

    def handle_route_finished(self, system_name):
        self.gen_destination_reached_image(
            destination=self.my_route[-1]["name"],
            current_system=system_name,
            current_system_on_route=True,
            jumps_remain=0,
            distance_remain=0,
            distance_traveled=round(self.total_distance_traveled, 2),
        )
        self.refresh_dashboard_image()
        self.log("Destination reached! You have arrived at the end of your Spansh route.")
        self.stop_monitoring(preserve_arrived_state=True)
    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def jump_detected(self, event_data, is_startup=False):
        if self.is_paused and not is_startup:
            return

        system_name = event_data.get("StarSystem")
        star_pos    = event_data.get("StarPos")

        if not system_name:
            self.log("Ignored event without StarSystem.")
            return

        if not isinstance(star_pos, (list, tuple)) or len(star_pos) != 3:
            self.log(f"Ignored event for {system_name}: missing or invalid StarPos.")
            return

        x, y, z = star_pos

        if is_startup:
            self.log(f"Current location detected at startup: {system_name} ({x} {y} {z})")
        else:
            jump_dist = float(event_data.get("JumpDist", 0.0) or 0.0)
            self.total_distance_traveled += jump_dist
            self.log(f"FSD jump complete! New system: {system_name} (+{jump_dist:.2f} LY)")

        result = self.find_next_waypoint(system_name, (x, y, z))

        if result == "ROUTE_FINISHED":
            self.highlight_route_table(system_name, None)
            self.handle_route_finished(system_name)
            return

        if result is None:
            self.log("Route is empty or no matching waypoint could be determined.")
            self.highlight_route_table(system_name, None)
            return

        next_stop, scoopable, has_neutron, jump_dist, jumps_remain, destination, distance_to_destination, on_route = result

        self.highlight_route_table(system_name, next_stop)
        self.update_dashboard(
            next_sys=next_stop,
            jumps_left=jumps_remain,
            final_tgt=destination,
            is_scoopable=scoopable,
            has_neutron=has_neutron,
        )

        self.log(f"Next: {next_stop} | Scoop: {scoopable} | Neutron: {has_neutron} | Dist: {jump_dist} LY")
        self.log(f"Progress: {jumps_remain} jumps remaining until final target: {destination}")

        if self.copy_to_clipboard(next_stop):
            self.log(f"Copied next waypoint to clipboard: {next_stop}")

        try:
            self.gen_galaxy_plotter_image(
                current_system=system_name,
                current_system_on_route=on_route,
                system_name=next_stop,
                destination=destination,
                jump_distance=jump_dist,
                jumps_remain=jumps_remain,
                distance_remain=distance_to_destination,
                distance_traveled=round(self.total_distance_traveled, 2),
                scoopable_star=scoopable,
                neutron_star=has_neutron,
            )
            self.refresh_dashboard_image()
        except Exception as e:
            self.log(f"Image generation error: {e}")

    # ------------------------------------------------------------------
    # Journal monitoring
    # ------------------------------------------------------------------
    def get_latest_journal_file(self):
        journal_files = glob.glob(os.path.join(self.journal_dir, "Journal.*.log"))
        if not journal_files:
            return None
        return max(journal_files, key=os.path.getmtime)

    def find_current_system_on_startup(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line in reversed(lines):
                try:
                    data = json.loads(line)
                    if data.get("event") in ["Location", "FSDJump"]:
                        return data
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.thread_safe_log(f"Error reading startup location: {e}")

        return None

    def monitor_journal(self):
        self.thread_safe_log("Searching for Elite Dangerous journal files...")
        current_journal = self.get_latest_journal_file()

        if not current_journal:
            self.thread_safe_log(f"No journals found at: {self.journal_dir}")
            self.thread_safe_log("Please verify your path or start Elite Dangerous.")
            self.ui_call(self.stop_monitoring)
            return

        start_event = self.find_current_system_on_startup(current_journal)
        if start_event:
            self.ui_call(self.jump_detected, start_event, True)
        else:
            self.thread_safe_log("Could not find current location in the log file.")

        self.thread_safe_log(f"Monitoring started on file: {os.path.basename(current_journal)}")

        try:
            file = open(current_journal, "r", encoding="utf-8", errors="ignore")
            try:
                file.seek(0, os.SEEK_END)

                while not self.stop_requested:
                    latest_journal = self.get_latest_journal_file()
                    if latest_journal and latest_journal != current_journal:
                        self.thread_safe_log(f"New log file detected: {os.path.basename(latest_journal)}")
                        current_journal = latest_journal
                        file.close()
                        file = open(current_journal, "r", encoding="utf-8", errors="ignore")
                        file.seek(0, os.SEEK_END)

                    line = file.readline()
                    if not line:
                        time.sleep(0.5)
                        continue

                    try:
                        log_entry = json.loads(line)
                        if log_entry.get("event") == "FSDJump":
                            self.ui_call(self.jump_detected, log_entry, False)
                    except json.JSONDecodeError:
                        continue
            finally:
                try:
                    file.close()
                except Exception:
                    pass

        except Exception as e:
            self.thread_safe_log(f"Monitoring thread error: {e}")
            self.ui_call(self.stop_monitoring)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tkinterdnd2.TkinterDnD.Tk()
    app  = EdSpanshApp(root)
    root.mainloop()
