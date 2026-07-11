##########################################################################
# DATE              13.06.2026                                           #
#                                                                        #
# AUTHOR            Bernard Härri (CMDR Weedy Gonzalez), but mostly LLMs #
#                                                                        #
# COMPILE: pyinstaller --noconsole --onefile ed_spansh_helper.py         #
#                                                                        #
##########################################################################

import os
import sys
import json
import time
import glob
import threading
import locale
import hashlib
import shutil
import math
import webbrowser
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
from typing import Any, cast

import tkinterdnd2
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

__version__ = "0.1.0"

DEBUG_MODE = "--debug" in sys.argv

if DEBUG_MODE:
    sys.argv = [arg for arg in sys.argv if arg != "--debug"]

# ----------------------------------------------------------------------
# Default configuration
# ----------------------------------------------------------------------
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "ed_spansh_settings.json")

DEFAULT_JOURNAL_DIR = os.path.expanduser(
    r"~\Saved Games\Frontier Developments\Elite Dangerous"
)
DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE = os.path.join(
    os.path.expanduser("~"), "vr_navigation.png"
)

DEFAULT_ED_HORIZONS_PATH = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Elite Dangerous"
    r"\Products\FORC-FDEV-DO-38-IN-40"
)
DEFAULT_ED_ODYSSEY_PATH = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Elite Dangerous"
    r"\Products\elite-dangerous-odyssey-assets"
)

OPENVR_DLL = "openvr_api.dll"
OPENVR_DLL_STEAMVR = "openvr_api.dll.steamvr"
OPENVR_DLL_OPENXR = "openvr_api.dll.openxr"


# ----------------------------------------------------------------------
# Button color constants
# ----------------------------------------------------------------------
BTN_BG = "#000000"
BTN_BG_ACTIVE = "#1a1a1a"
BTN_FG_START = "#00d26a"
BTN_FG_PAUSE = "#ffd700"
BTN_FG_STOP = "#ff3b30"
BTN_FG_DISABLED = "#3a3a3a"


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
    OFF_ROUTE_ORDER_PRIORITY_THRESHOLD_LY = 80.0

    # ------------------------------------------------------------------
    # Navigation image layout constants
    # Shared layout settings for Road to Riches / Exobiology kneeboard PNGs
    # ------------------------------------------------------------------
    NAV_FONT_NAME = "arial.ttf"

    # Shared table layout
    TABLE_LEFT = 45
    TABLE_RIGHT = 955
    TABLE_TOP = 136
    TABLE_FIRST_ROW_Y_OFFSET = 42
    TABLE_ROW_HEIGHT = 56

    # Shared summary layout
    SUMMARY_BODIES_X = 60

    # Road to Riches table columns
    R2R_COL_BODY_X = 45
    R2R_SINGLE_COL_DIST_X = 560
    R2R_SINGLE_COL_VALUE_X = 910
    R2R_BOTH_COL_DIST_X = 520
    R2R_BOTH_COL_SCAN_X = 735
    R2R_BOTH_COL_MAP_X = 940

    # Road to Riches summary layout
    R2R_SUMMARY_SINGLE_VALUE_X = 360
    R2R_SUMMARY_SCAN_X = 300
    R2R_SUMMARY_MAP_X = 650
    R2R_SUMMARY_SEP_LEFT_X = 250
    R2R_SUMMARY_SEP_RIGHT_X = 610

    # Exobiology table columns
    EXO_COL_BODY_X = 45
    EXO_COL_DIST_X = 310
    EXO_COL_VALUE_X = 520
    EXO_COL_SUBTYPE_X = 610

    # Exobiology text fitting
    EXO_BODY_FONT_START = 30
    EXO_BODY_FONT_MIN = 18
    EXO_BODY_MAX_WIDTH = 220
    EXO_SUBTYPE_FONT_START = 30
    EXO_SUBTYPE_FONT_MIN = 18
    EXO_SUBTYPE_MAX_WIDTH = 340

    # Exobiology summary layout
    EXO_SUMMARY_VALUE_X = 355
    EXO_SUMMARY_WAYPOINTS_X = 690
    EXO_SUMMARY_SEP_LEFT_X = 290
    EXO_SUMMARY_SEP_RIGHT_X = 620

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.debug_mode = DEBUG_MODE
        self.debug_waypoint_entries = []
        self.debug_auto_simulation_active = False
        self.debug_auto_simulation_after_id = None
        self.debug_auto_simulation_delay_ms = 800

        debug_suffix = " [DEBUG MODE]" if self.debug_mode else ""
        self.root.title(
            f"Elite Dangerous - Spansh VR Navigator v{__version__}{debug_suffix}"
        )
        self.root.geometry("1500x1080" if self.debug_mode else "1500x950")
        self.root.minsize(1200, 1230 if self.debug_mode else 1100)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.my_route = []
        self.route_index = 0
        self.route_type = "UNKNOWN"
        self.r2r_value_mode = "both"
        self.monitoring_active = False
        self.is_paused = False
        self.stop_requested = False
        self.total_distance_traveled = 0.0
        self.current_system_name = ""
        self.current_system_coords = None
        self.last_next_waypoint_name = ""
        self.last_next_waypoint_coords = None
        self.route_context_row_data = None

        (
            self.current_theme_name,
            self.journal_dir,
            self.last_route_file,
            self.kneeboard_output_img_file,
            self.ship_builds_raw,
            self.vr_versions,
            self.openxr_dll_source,
            self.r2r_value_mode,
        ) = self.load_settings()

        self.ship_builds = []

        self.create_widgets()
        self.setup_table_style()
        self.setup_combobox_style()
        self.apply_theme(self.current_theme_name)
        self.setup_drag_and_drop()
        self.load_last_route_on_startup()
        self.root.after(300, self.check_vr_setup_on_startup)

    def on_close(self):
        self.stop_requested = True
        self.monitoring_active = False
        self.save_settings()
        self.root.destroy()

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

    def check_vr_setup_on_startup(self):
        versions_needing_setup = []

        for entry in self.vr_versions:
            name = str(entry.get("name", "Unnamed Version")).strip() or "Unnamed Version"
            path = str(entry.get("path", "")).strip()

            if path and os.path.isdir(path):
                mode = self.vr_detect_mode(path)
                if mode in ("needs_setup", "game_updated"):
                    versions_needing_setup.append(name)

        if not versions_needing_setup:
            return

        for version_name in versions_needing_setup:
            self.log(f"VR setup required: {version_name}")
        self.log("Go to Settings > VR Runtime and run 'Setup / Re-Setup'.")

        version_list = "\n".join(f"  • {name}" for name in versions_needing_setup)
        messagebox.showwarning(
            "VR setup required",
            f"The OpenVR DLL setup still needs to be completed for:\n\n"
            f"{version_list}\n\n"
            f"Please open Settings > VR Runtime and run 'Setup / Re-Setup'.",
            parent=self.root,
        )

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
    # Settings helpers
    # ------------------------------------------------------------------
    def normalize_vr_versions(self, versions):
        normalized = []

        if not isinstance(versions, list):
            return normalized

        for item in versions:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip() or "Unnamed Version"
            path = str(item.get("path", "")).strip()

            normalized.append({
                "name": name,
                "path": path,
            })

        return normalized

    def make_unique_name(self, base_name, existing_names, exclude_name=None):
        name = str(base_name).strip() or "Unnamed Version"
        taken = {
            str(existing).strip()
            for existing in existing_names
            if str(existing).strip() and str(existing).strip() != str(exclude_name).strip()
        }

        if name not in taken:
            return name

        counter = 2
        while True:
            candidate = f"{name} ({counter})"
            if candidate not in taken:
                return candidate
            counter += 1

    def get_vr_version_names(self):
        return [entry.get("name", "Unnamed Version") for entry in self.vr_versions]

    def find_vr_version_by_name(self, name):
        for entry in self.vr_versions:
            if entry.get("name") == name:
                return entry
        return None

    def load_settings(self):
        theme = "ed_orange"
        journal_dir = DEFAULT_JOURNAL_DIR
        route_file = ""
        kneeboard_img_file = DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE
        ship_builds = []
        vr_versions = []
        openxr_dll_source = ""
        r2r_value_mode = "both"

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)

                theme = s.get("theme", "ed_orange")
                journal_dir = s.get("journal_dir", DEFAULT_JOURNAL_DIR)
                route_file = s.get("last_route_file", "")
                ship_builds = s.get("ship_builds", [])
                kneeboard_img_file = s.get(
                    "kneeboard_output_img_file",
                    DEFAULT_KNEEBOARD_OUTPUT_IMG_FILE,
                )
                openxr_dll_source = s.get("openxr_dll_source", "")
                r2r_value_mode = s.get("r2r_value_mode", "both")
                vr_versions = self.normalize_vr_versions(s.get("vr_versions", []))

                if not vr_versions:
                    old_horizons = str(s.get("ed_horizons_path", "")).strip()
                    old_odyssey = str(s.get("ed_odyssey_path", "")).strip()

                    if old_horizons:
                        vr_versions.append({
                            "name": "Horizons",
                            "path": old_horizons,
                        })

                    if old_odyssey:
                        vr_versions.append({
                            "name": "Odyssey",
                            "path": old_odyssey,
                        })

                    if not vr_versions:
                        if os.path.isdir(DEFAULT_ED_HORIZONS_PATH):
                            vr_versions.append({
                                "name": "Horizons",
                                "path": DEFAULT_ED_HORIZONS_PATH,
                            })
                        if os.path.isdir(DEFAULT_ED_ODYSSEY_PATH):
                            vr_versions.append({
                                "name": "Odyssey",
                                "path": DEFAULT_ED_ODYSSEY_PATH,
                            })

            except Exception:
                pass

        if theme not in THEMES:
            theme = "ed_orange"

        vr_versions = self.normalize_vr_versions(vr_versions)

        if r2r_value_mode not in ("scan", "mapping", "both"):
            r2r_value_mode = "both"

        return (
            theme,
            journal_dir,
            route_file,
            kneeboard_img_file,
            ship_builds,
            vr_versions,
            openxr_dll_source,
            r2r_value_mode,
        )

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
                        "vr_versions": self.vr_versions,
                        "openxr_dll_source": self.openxr_dll_source,
                        "r2r_value_mode": self.r2r_value_mode,
                    },
                    f,
                    indent=2,
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

    def _format_coordinate_value(self, value):
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                return str(int(numeric_value))
            return f"{numeric_value:.6f}".rstrip("0").rstrip(".")
        except Exception:
            return str(value).strip()

    def format_coordinates(self, x, y, z):
        return ",".join([
            self._format_coordinate_value(x),
            self._format_coordinate_value(y),
            self._format_coordinate_value(z),
        ])

    def copy_current_system(self):
        if not self.current_system_name:
            messagebox.showwarning(
                "No Current System",
                "No current system is known yet.\nStart monitoring first or wait for the first location event."
            )
            return

        if self.copy_to_clipboard(self.current_system_name):
            self.log(f"Copied current system to clipboard: {self.current_system_name}")

    def copy_current_coordinates(self):
        if (
            not self.current_system_coords
            or not isinstance(self.current_system_coords, (list, tuple))
            or len(self.current_system_coords) != 3
        ):
            messagebox.showwarning(
                "No Current Coordinates",
                "No current coordinates are known yet.\nStart monitoring first or wait for the first location event."
            )
            return

        coords_text = self.format_coordinates(*self.current_system_coords)
        if self.copy_to_clipboard(coords_text):
            self.log(f"Copied current coordinates to clipboard: {coords_text}")

    def copy_next_waypoint(self):
        if not self.last_next_waypoint_name:
            messagebox.showwarning(
                "No Next Waypoint",
                "No next waypoint has been determined yet."
            )
            return

        if self.copy_to_clipboard(self.last_next_waypoint_name):
            self.log(f"Copied next waypoint to clipboard: {self.last_next_waypoint_name}")

    def get_route_row_data_by_item_id(self, item_id):
        for row in self.route_table_row_data:
            if row.get("item_id") == item_id:
                return row
        return None

    def get_selected_route_row_data(self):
        selection = self.route_table.selection()
        if not selection:
            return None
        return self.get_route_row_data_by_item_id(selection[0])

    def copy_route_row_system_name(self, row_data=None):
        row_data = row_data or self.get_selected_route_row_data()
        if not row_data:
            return

        system_name = str(row_data.get("system_name", "")).strip()
        if not system_name:
            return

        if self.copy_to_clipboard(system_name):
            self.log(f"Copied route system name to clipboard: {system_name}")

    def copy_route_row_coordinates(self, row_data=None):
        row_data = row_data or self.get_selected_route_row_data()
        if not row_data:
            return

        x = row_data.get("x")
        y = row_data.get("y")
        z = row_data.get("z")

        if x is None or y is None or z is None:
            route_entry = self.get_route_entry_by_name(row_data.get("system_name"))
            if route_entry:
                x = route_entry.get("x")
                y = route_entry.get("y")
                z = route_entry.get("z")

        if x is None or y is None or z is None:
            messagebox.showwarning(
                "No Coordinates",
                "No coordinates are stored for this route entry."
            )
            return

        coords_text = self.format_coordinates(x, y, z)
        if self.copy_to_clipboard(coords_text):
            self.log(
                f"Copied route coordinates to clipboard: "
                f"{row_data.get('system_name', '')} -> {coords_text}"
            )

    def copy_selected_route_system_name(self):
        self.copy_route_row_system_name(self.route_context_row_data)

    def copy_selected_route_coordinates(self):
        self.copy_route_row_coordinates(self.route_context_row_data)

    def show_route_table_context_menu(self, event):
        item_id = self.route_table.identify_row(event.y)
        if not item_id:
            return

        self.route_table.selection_set(item_id)
        self.route_table.focus(item_id)
        self.route_context_row_data = self.get_route_row_data_by_item_id(item_id)

        if not self.route_context_row_data:
            return

        try:
            self.route_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.route_context_menu.grab_release()

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------
    def create_widgets(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Full-width top control buttons
        self.btn_frame = tk.Frame(self.main_frame)
        self.btn_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.start_btn = tk.Button(
            self.btn_frame,
            text="▶",
            command=self.start_monitoring,
            bg=BTN_BG, fg=BTN_FG_START,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_START,
            font=("Arial", 18, "bold"),
            pady=5, relief="raised", bd=3,
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.pause_btn = tk.Button(
            self.btn_frame,
            text="⏸",
            command=self.toggle_pause,
            bg=BTN_BG, fg=BTN_FG_PAUSE,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_PAUSE,
            font=("Arial", 18, "bold"),
            pady=5, state="disabled", relief="raised", bd=3,
        )
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.stop_btn = tk.Button(
            self.btn_frame,
            text="⏹",
            command=self.stop_monitoring,
            bg=BTN_BG, fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_STOP,
            font=("Arial", 18, "bold"),
            pady=5, state="disabled", relief="raised", bd=3,
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.btn_separator = tk.Frame(self.btn_frame, bg="#ff7300", width=2)
        self.btn_separator.pack(side="left", fill="y", padx=12, pady=3)

        self.settings_btn = tk.Button(
            self.btn_frame,
            text="⚙  Settings",
            command=self.open_settings_dialog,
            bg=BTN_BG, fg="#ff7300",
            activebackground=BTN_BG_ACTIVE, activeforeground="#ffaa44",
            font=("Arial", 14, "bold"),
            pady=5, relief="raised", bd=3, padx=14,
        )
        self.settings_btn.pack(side="left", padx=(0, 2))

        self.about_btn = tk.Button(
            self.btn_frame,
            text="ⓘ  About",
            command=self.open_about_dialog,
            bg=BTN_BG, fg="#ff7300",
            activebackground=BTN_BG_ACTIVE, activeforeground="#ffaa44",
            font=("Arial", 14, "bold"),
            pady=5, relief="raised", bd=3, padx=14,
        )
        self.about_btn.pack(side="left", padx=(0, 2))

        self.exit_btn = tk.Button(
            self.btn_frame,
            text="✕  Exit",
            command=self.on_close,
            bg=BTN_BG, fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_STOP,
            font=("Arial", 14, "bold"),
            pady=5, relief="raised", bd=3, padx=14,
        )
        self.exit_btn.pack(side="left", padx=(0, 0))

        # Horizontal split: left content | right log
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.columnconfigure(0, weight=3)
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.left_frame = tk.Frame(self.content_frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew")

        self.right_frame = tk.Frame(self.content_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        # Spansh tools
        self.ship_build_frame = tk.LabelFrame(
            self.left_frame,
            text=" Spansh Tools ",
            font=("Arial", 10, "bold"),
            padx=10, pady=10,
        )
        self.ship_build_frame.pack(fill="x", expand=False, padx=10, pady=5)

        self.ship_build_top_row = tk.Frame(self.ship_build_frame)
        self.ship_build_top_row.pack(fill="x")

        self.open_spansh_btn = tk.Button(
            self.ship_build_top_row,
            text="Open Spansh",
            command=self.open_spansh_website,
            padx=10,
        )
        self.open_spansh_btn.pack(side="left")

        self.ship_build_label = tk.Label(
            self.ship_build_top_row,
            text="Stored Ship Builds:",
            font=("Arial", 9, "bold"),
        )
        self.ship_build_label.pack(side="left", padx=(20, 8))

        self.ship_build_var = tk.StringVar()
        self.ship_build_dropdown = ttk.Combobox(
            self.ship_build_top_row,
            textvariable=self.ship_build_var,
            state="readonly",
            width=35,
            style="Orange.TCombobox",
        )
        self.ship_build_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.add_ship_build_small_btn = tk.Button(
            self.ship_build_top_row,
            text="+",
            command=self.open_add_ship_build_dialog,
            width=3,
        )
        self.add_ship_build_small_btn.pack(side="left", padx=(0, 4))

        self.remove_ship_build_btn = tk.Button(
            self.ship_build_top_row,
            text="-",
            command=self.remove_selected_ship_build,
            width=3,
        )
        self.remove_ship_build_btn.pack(side="left", padx=(0, 8))

        self.copy_ship_build_btn = tk.Button(
            self.ship_build_top_row,
            text="Copy Build JSON",
            command=self.copy_selected_ship_build,
            padx=10,
        )
        self.copy_ship_build_btn.pack(side="left")

        self.ship_build_action_row = tk.Frame(self.ship_build_frame)
        self.ship_build_action_row.pack(fill="x", pady=(8, 0))

        self.copy_current_system_btn = tk.Button(
            self.ship_build_action_row,
            text="Copy Current System",
            command=self.copy_current_system,
            padx=10,
        )
        self.copy_current_system_btn.pack(side="left", padx=(0, 6))

        self.copy_current_coordinates_btn = tk.Button(
            self.ship_build_action_row,
            text="Copy Current Coordinates",
            command=self.copy_current_coordinates,
            padx=10,
        )
        self.copy_current_coordinates_btn.pack(side="left", padx=(0, 6))

        self.copy_next_waypoint_btn = tk.Button(
            self.ship_build_action_row,
            text="Copy next Waypoint",
            command=self.copy_next_waypoint,
            padx=10,
        )
        self.copy_next_waypoint_btn.pack(side="left")

        # Route overview
        self.route_info_frame = tk.LabelFrame(
            self.left_frame,
            text=" Route Overview ",
            font=("Arial", 10, "bold"),
            padx=10, pady=10,
        )
        self.route_info_frame.pack(fill="both", expand=False, padx=10, pady=5)

        self.input_label = tk.Label(
            self.route_info_frame,
            text="Select a Spansh route JSON file (or drop it here):",
            font=("Arial", 10, "bold"),
        )
        self.input_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.file_frame = tk.Frame(self.route_info_frame)
        self.file_frame.pack(fill="x", padx=10, pady=5)

        self.file_entry = tk.Entry(
            self.file_frame,
            font=("Consolas", 10),
            bd=2, relief="groove",
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

        # Route table
        self.route_table_frame = tk.Frame(self.route_info_frame)
        self.route_table_frame.pack(fill="both", expand=True)

        self.route_table = ttk.Treeview(
            self.route_table_frame,
            columns=("wp_no", "system", "distance", "scoopable", "neutron", "jumps_to"),
            show="headings",
            height=10,
            style="Route.Treeview",
        )

        self.route_table.heading("wp_no", text="#")
        self.route_table.heading("system", text="System Name")
        self.route_table.heading("distance", text="Distance")
        self.route_table.heading("scoopable", text="Scoopable")
        self.route_table.heading("neutron", text="Neutron Star")
        self.route_table.heading("jumps_to", text="Jumps to Reach")

        self.route_table.column("wp_no", width=60, minwidth=50, anchor="center")
        self.route_table.column("system", width=350, minwidth=200, anchor="w")
        self.route_table.column("distance", width=100, minwidth=80, anchor="e")
        self.route_table.column("scoopable", width=90, minwidth=80, anchor="center")
        self.route_table.column("neutron", width=100, minwidth=90, anchor="center")
        self.route_table.column("jumps_to", width=110, minwidth=90, anchor="center")

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

        self.route_context_menu = tk.Menu(self.root, tearoff=0)
        self.route_context_menu.add_command(
            label="Copy System Name",
            command=self.copy_selected_route_system_name,
        )
        self.route_context_menu.add_command(
            label="Copy Coordinates",
            command=self.copy_selected_route_coordinates,
        )

        self.route_table.bind("<Button-3>", self.show_route_table_context_menu)

        # Cockpit navigation display
        self.dash_frame = tk.LabelFrame(
            self.left_frame,
            text=" Cockpit Navigation Display ",
            font=("Arial", 10, "bold"),
            padx=10, pady=10,
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

        # Debug: simulate jump
        if self.debug_mode:
            self.debug_frame = tk.LabelFrame(
                self.left_frame,
                text=" Debug / Simulate Jump ",
                font=("Arial", 10, "bold"),
                padx=10, pady=10,
            )
            self.debug_frame.pack(fill="x", expand=False, padx=10, pady=5)

            self.debug_row_top = tk.Frame(self.debug_frame)
            self.debug_row_top.pack(fill="x")

            self.debug_label = tk.Label(
                self.debug_row_top,
                text="Waypoint:",
                font=("Arial", 10, "bold"),
            )
            self.debug_label.pack(side="left", padx=(0, 8))

            self.debug_waypoint_var = tk.StringVar()
            self.debug_waypoint_dropdown = ttk.Combobox(
                self.debug_row_top,
                textvariable=self.debug_waypoint_var,
                state="readonly",
                width=50,
                style="Orange.TCombobox",
            )
            self.debug_waypoint_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 8))

            self.debug_simulate_btn = tk.Button(
                self.debug_row_top,
                text="Simulate Selected",
                command=self.simulate_selected_jump,
                padx=12,
            )
            self.debug_simulate_btn.pack(side="left")

            self.debug_row_bottom = tk.Frame(self.debug_frame)
            self.debug_row_bottom.pack(fill="x", pady=(8, 0))

            self.debug_next_btn = tk.Button(
                self.debug_row_bottom,
                text="Simulate Next Waypoint",
                command=self.simulate_next_waypoint,
                padx=12,
            )
            self.debug_next_btn.pack(side="left", padx=(0, 8))

            self.debug_auto_btn = tk.Button(
                self.debug_row_bottom,
                text="Auto Simulate Route",
                command=self.toggle_auto_simulate_route,
                padx=12,
            )
            self.debug_auto_btn.pack(side="left")

            self.debug_hint_label = tk.Label(
                self.debug_frame,
                text="Available only when the app is started with --debug",
                font=("Arial", 9),
                anchor="w",
                justify="left",
            )
            self.debug_hint_label.pack(fill="x", pady=(8, 0))

        # Log output
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

        tk.Label(
            dialog,
            text="Paste Ship Build JSON",
            font=("Arial", 11, "bold"),
            bg=t["bg"], fg=t["label_fg"],
        ).pack(anchor="w", padx=10, pady=(10, 4))

        tk.Label(
            dialog,
            text="Paste the full ship build JSON and click 'Add Build'.",
            font=("Arial", 9),
            bg=t["bg"], fg=t["fg"],
        ).pack(anchor="w", padx=10, pady=(0, 8))

        text_widget = scrolledtext.ScrolledText(
            dialog,
            height=16,
            font=("Consolas", 9),
            wrap="word",
            relief="flat",
            bd=4,
            bg=t["input_bg"],
            fg=t["input_fg"],
            insertbackground=t["input_fg"],
        )
        text_widget.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        button_row = tk.Frame(dialog, bg=t["bg"])
        button_row.pack(fill="x", padx=10, pady=(0, 10))

        def add_and_close():
            raw_text = text_widget.get("1.0", tk.END).strip()
            if not raw_text:
                messagebox.showwarning(
                    "No Input",
                    "Please paste a ship build JSON first.",
                    parent=dialog
                )
                return

            try:
                json.loads(raw_text)
            except Exception as e:
                messagebox.showerror(
                    "Invalid JSON",
                    f"Ship build JSON is invalid:\n{e}",
                    parent=dialog
                )
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

        tk.Button(
            button_row,
            text="Cancel",
            command=dialog.destroy,
            bg=t["btn_stop_bg"], fg=t["btn_fg"],
            activebackground="#aa3a00", activeforeground=t["btn_fg"],
            relief="flat", bd=0, padx=12, pady=4,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            button_row,
            text="Add Build",
            command=add_and_close,
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0, padx=12, pady=4,
        ).pack(side="right")

    def open_add_vr_version_dialog(self, parent, on_add_callback):
        dialog = tk.Toplevel(parent)
        dialog.title("Add Game Version")
        dialog.geometry("560x220")
        dialog.minsize(500, 220)
        dialog.transient(parent)
        dialog.grab_set()

        t = THEMES[self.current_theme_name]
        dialog.config(bg=t["bg"])

        tk.Label(
            dialog,
            text="Version Name:",
            font=("Arial", 10, "bold"),
            bg=t["bg"], fg=t["label_fg"],
        ).pack(anchor="w", padx=10, pady=(12, 2))

        name_var = tk.StringVar()
        name_entry = tk.Entry(
            dialog,
            textvariable=name_var,
            bg=t["input_bg"], fg=t["input_fg"],
            insertbackground=t["input_fg"],
            font=("Consolas", 10),
            relief="flat", bd=4,
        )
        name_entry.pack(fill="x", padx=10, pady=(0, 10), ipady=4)
        name_entry.focus_set()

        tk.Label(
            dialog,
            text="Game Path:",
            font=("Arial", 10, "bold"),
            bg=t["bg"], fg=t["label_fg"],
        ).pack(anchor="w", padx=10, pady=(0, 2))

        path_row = tk.Frame(dialog, bg=t["bg"])
        path_row.pack(fill="x", padx=10, pady=(0, 10))

        path_var = tk.StringVar()
        path_entry = tk.Entry(
            path_row,
            textvariable=path_var,
            bg=t["input_bg"], fg=t["input_fg"],
            insertbackground=t["input_fg"],
            font=("Consolas", 10),
            relief="flat", bd=4,
        )
        path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        def browse():
            selected = filedialog.askdirectory(
                initialdir=os.path.expanduser("~"),
                title="Select Game Directory",
            )
            if selected:
                path_var.set(os.path.normpath(selected))

        tk.Button(
            path_row,
            text="Browse...",
            command=browse,
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0, padx=10, pady=3,
        ).pack(side="left", padx=(6, 0))

        button_row = tk.Frame(dialog, bg=t["bg"])
        button_row.pack(fill="x", padx=10, pady=(0, 10))

        def add_version():
            name = name_var.get().strip()
            path = path_var.get().strip()

            if not name:
                messagebox.showwarning(
                    "Missing Name",
                    "Please enter a version name.",
                    parent=dialog,
                )
                return

            if not path:
                messagebox.showwarning(
                    "Missing Path",
                    "Please select a game path.",
                    parent=dialog,
                )
                return

            on_add_callback({
                "name": name,
                "path": os.path.normpath(path),
            })
            dialog.destroy()

        tk.Button(
            button_row,
            text="Cancel",
            command=dialog.destroy,
            bg=t["btn_stop_bg"], fg=t["btn_fg"],
            activebackground="#aa3a00", activeforeground=t["btn_fg"],
            relief="flat", bd=0, padx=12, pady=4,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            button_row,
            text="Add",
            command=add_version,
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0, padx=12, pady=4,
        ).pack(side="right")

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
            messagebox.showerror(
                "Build Not Found",
                "The selected ship build could not be found."
            )
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
            darkcolor=t["panel_border"],
        )

        style.map(
            "Orange.TCombobox",
            fieldbackground=[("readonly", t["input_bg"])],
            foreground=[("readonly", t["input_fg"])],
            selectbackground=[("readonly", t["input_bg"])],
            selectforeground=[("readonly", t["accent_fg"])],
        )

        self.root.option_add("*TCombobox*Listbox.background", t["input_bg"])
        self.root.option_add("*TCombobox*Listbox.foreground", t["input_fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", t["accent_fg"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#000000")
        self.root.option_add("*TCombobox*Listbox.font", ("Arial", 10))

    def apply_theme(self, theme_name):
        t = THEMES[theme_name]

        self.root.config(bg=t["bg"])
        self.main_frame.config(bg=t["bg"])
        self.file_frame.config(bg=t["bg"])
        self.btn_frame.config(bg=t["bg"])

        self.content_frame.config(bg=t["bg"])
        self.left_frame.config(bg=t["bg"])
        self.right_frame.config(bg=t["bg"])

        self.input_label.config(bg=t["bg"], fg=t["label_fg"])
        self.output_label.config(bg=t["bg"], fg=t["label_fg"])

        self.ship_build_frame.config(
            bg=t["panel_bg"], fg=t["label_fg"], bd=2, relief="groove"
        )
        self.ship_build_top_row.config(bg=t["panel_bg"])
        self.ship_build_label.config(bg=t["panel_bg"], fg=t["label_fg"])
        self.ship_build_action_row.config(bg=t["panel_bg"])

        self.open_spansh_btn.config(
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.copy_ship_build_btn.config(
            bg=t["btn_pause_bg"], fg=t["btn_fg"],
            activebackground=t["btn_start_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.copy_current_system_btn.config(
            bg=t["btn_pause_bg"], fg=t["btn_fg"],
            activebackground=t["btn_start_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.copy_current_coordinates_btn.config(
            bg=t["btn_pause_bg"], fg=t["btn_fg"],
            activebackground=t["btn_start_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.copy_next_waypoint_btn.config(
            bg=t["btn_pause_bg"], fg=t["btn_fg"],
            activebackground=t["btn_start_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.add_ship_build_small_btn.config(
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )
        self.remove_ship_build_btn.config(
            bg=t["btn_stop_bg"], fg=t["btn_fg"],
            activebackground="#aa3a00", activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )

        self.route_info_frame.config(
            bg=t["panel_bg"], fg=t["label_fg"], bd=2, relief="groove"
        )
        self.lbl_route_type.config(bg=t["panel_bg"], fg=t["accent_fg"])
        self.route_table_frame.config(bg=t["panel_bg"])

        self.dash_frame.config(
            bg=t["panel_bg"], fg=t["label_fg"], bd=2, relief="groove"
        )

        for child in self.dash_frame.winfo_children():
            try:
                cast(Any, child).configure(bg=t["panel_bg"], fg=t["fg"])
            except Exception:
                pass
        self.dashboard_image_label.config(bg=t["panel_bg"], fg=t["accent_fg"])

        self.file_entry.config(
            bg=t["input_bg"], fg=t["input_fg"],
            insertbackground=t["input_fg"], relief="flat", bd=6,
        )
        self.log_output.config(
            bg=t["log_bg"], fg=t["log_fg"],
            insertbackground=t["log_fg"], relief="flat", bd=6,
        )
        self.browse_btn.config(
            bg=t["btn_start_bg"], fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
            relief="flat", bd=0,
        )

        self.start_btn.config(
            bg=BTN_BG, fg=BTN_FG_START,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_START,
            bd=3,
        )
        self.pause_btn.config(
            bg=BTN_BG, fg=BTN_FG_PAUSE,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_PAUSE,
            bd=3,
        )
        self.stop_btn.config(
            bg=BTN_BG, fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_STOP,
            bd=3,
        )

        self.btn_separator.config(bg="#ff7300")
        self.settings_btn.config(
            bg=BTN_BG, fg="#ff7300",
            activebackground=BTN_BG_ACTIVE, activeforeground="#ffaa44",
            bd=3,
        )
        self.about_btn.config(
            bg=BTN_BG, fg="#ff7300",
            activebackground=BTN_BG_ACTIVE, activeforeground="#ffaa44",
            bd=3,
        )
        self.exit_btn.config(
            bg=BTN_BG, fg=BTN_FG_STOP,
            activebackground=BTN_BG_ACTIVE, activeforeground=BTN_FG_STOP,
            bd=3,
        )

        try:
            self.route_table_scroll_y.config(
                bg=t["panel_bg"], activebackground=t["btn_start_bg"],
                troughcolor=t["bg"], bd=0, relief="flat",
            )
            self.route_table_scroll_x.config(
                bg=t["panel_bg"], activebackground=t["btn_start_bg"],
                troughcolor=t["bg"], bd=0, relief="flat",
            )
        except Exception:
            pass

        self.setup_table_style()
        self.setup_combobox_style()

        try:
            self.route_table.tag_configure(
                "current_system", background="#402200", foreground="#ffd6b3"
            )
            self.route_table.tag_configure(
                "next_waypoint", background="#ff8c2a", foreground="#000000"
            )
        except Exception:
            pass

        try:
            self.route_context_menu.config(
                bg=t["panel_bg"],
                fg=t["value_fg"],
                activebackground=t["accent_fg"],
                activeforeground="#000000",
                bd=2,
                relief="flat",
            )
        except Exception:
            pass

        if self.debug_mode and hasattr(self, "debug_frame"):
            self.debug_frame.config(
                bg=t["panel_bg"], fg=t["label_fg"], bd=2, relief="groove"
            )
            self.debug_row_top.config(bg=t["panel_bg"])
            self.debug_row_bottom.config(bg=t["panel_bg"])
            self.debug_label.config(bg=t["panel_bg"], fg=t["label_fg"])
            self.debug_hint_label.config(bg=t["panel_bg"], fg=t["value_fg"])

            self.debug_simulate_btn.config(
                bg=t["btn_start_bg"], fg=t["btn_fg"],
                activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
                relief="flat", bd=0,
            )
            self.debug_next_btn.config(
                bg=t["btn_pause_bg"], fg=t["btn_fg"],
                activebackground=t["btn_start_bg"], activeforeground=t["btn_fg"],
                relief="flat", bd=0,
            )
            self.debug_auto_btn.config(
                bg=t["btn_start_bg"], fg=t["btn_fg"],
                activebackground=t["btn_pause_bg"], activeforeground=t["btn_fg"],
                relief="flat", bd=0,
            )

    def _update_transport_btn_states(self):
        self.start_btn.config(
            relief="sunken" if self.monitoring_active else "raised"
        )
        self.pause_btn.config(
            relief="sunken" if self.is_paused else "raised"
        )
        self.stop_btn.config(relief="raised")

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    def refresh_dashboard_image(self):
        try:
            if not os.path.exists(self.kneeboard_output_img_file):
                return

            with Image.open(self.kneeboard_output_img_file) as img:
                img = img.copy()

            max_width, max_height = 700, 520
            width, height = img.size
            scale = min(max_width / width, max_height / height, 1.0)
            new_size = (int(width * scale), int(height * scale))

            if new_size != img.size:
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            self.dashboard_photo = ImageTk.PhotoImage(img)
            self.dashboard_image_label.config(image=self.dashboard_photo, text="")
        except Exception as e:
            self.log(f"Dashboard image refresh error: {e}")

    def update_dashboard(self, next_sys=None, jumps_left=None,
                         final_tgt=None, is_scoopable=None, has_neutron=None):
        self.refresh_dashboard_image()

    def reset_dashboard(self):
        self.dashboard_image_label.config(
            image="", text="Waiting for navigation image..."
        )
        self.dashboard_photo = None

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------
    def setup_drag_and_drop(self):
        cast(Any, self.file_entry).drop_target_register(DND_FILES)
        cast(Any, self.file_entry).dnd_bind("<<Drop>>", self.handle_drop)
        cast(Any, self.log_output).drop_target_register(DND_FILES)
        cast(Any, self.log_output).dnd_bind("<<Drop>>", self.handle_drop)

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
            messagebox.showerror(
                "Invalid File",
                "Please drop a valid .json route file."
            )

    # ------------------------------------------------------------------
    # Browse helpers
    # ------------------------------------------------------------------
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
        initial_dir = (
            os.path.dirname(self.last_route_file)
            if self.last_route_file
            else os.path.expanduser("~")
        )
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
            self.log(
                f"Kneeboard image output file updated to: "
                f"{self.kneeboard_output_img_file}"
            )

    # ------------------------------------------------------------------
    # Route table helpers
    # ------------------------------------------------------------------
    def clear_route_table(self):
        for item_id in self.route_table.get_children():
            self.route_table.delete(item_id)
        self.route_table_item_ids = []
        self.route_table_row_data = []
        self.route_context_row_data = None

    def populate_route_table(self, route_rows, route_type="UNKNOWN"):
        self.clear_route_table()
        self.lbl_route_type.config(text=f"Route Type: {route_type}")
        self.route_table_row_data = []

        for row in route_rows:
            waypoint_no = row.get("waypoint_no", "")
            system_name = row.get("system_name", "")
            distance = row.get("distance", 0.0)
            scoopable = row.get("scoopable", None)
            neutron_star = row.get("neutron_star", False)
            jumps_to_reach = row.get("jumps_to_reach", 0)

            scoopable_text = "-" if scoopable is None else ("Yes" if scoopable else "No")
            neutron_text = "Yes" if neutron_star else "No"
            distance_text = (
                f"{distance:.1f} LY"
                if isinstance(distance, (int, float)) else str(distance)
            )

            item_id = self.route_table.insert(
                "", "end",
                values=(
                    waypoint_no, system_name, distance_text,
                    scoopable_text, neutron_text, jumps_to_reach,
                ),
            )
            self.route_table_item_ids.append(item_id)
            self.route_table_row_data.append({
                "item_id": item_id,
                "waypoint_no": waypoint_no,
                "system_name": str(system_name),
                "distance": distance,
                "scoopable": scoopable,
                "neutron_star": neutron_star,
                "jumps_to_reach": jumps_to_reach,
                "x": row.get("x"),
                "y": row.get("y"),
                "z": row.get("z"),
            })

        self.route_table.tag_configure(
            "current_system", background="#4a2a00", foreground="#ffd6b3"
        )
        self.route_table.tag_configure(
            "next_waypoint", background="#ff7300", foreground="#000000"
        )

    def highlight_route_table(self, current_system, next_waypoint):
        for item_id in self.route_table.get_children():
            self.route_table.item(item_id, tags=())

        next_matches = []
        current_system_lc = str(current_system).strip().lower() if current_system else ""
        next_waypoint_lc = str(next_waypoint).strip().lower() if next_waypoint else ""

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

    # ------------------------------------------------------------------
    # Spansh / ship build helpers
    # ------------------------------------------------------------------
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
            self.ship_builds.append({"name": ship_name, "raw": raw})

    def refresh_ship_build_dropdown(self):
        previous_selection = self.ship_build_var.get().strip()

        self.rebuild_ship_build_index()
        names = [str(entry["name"]) for entry in self.ship_builds]
        self.ship_build_dropdown.configure(values=tuple(names))

        if names:
            if previous_selection in names:
                self.ship_build_var.set(str(previous_selection or ""))
                self.ship_build_dropdown.current(names.index(previous_selection))
            else:
                self.ship_build_var.set(str(names[0] or ""))
                self.ship_build_dropdown.current(0)
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

        messagebox.showerror(
            "Build Not Found",
            "The selected ship build could not be found."
        )

    def _calculate_precise_distance(self, coord_a, coord_b):
        try:
            ax, ay, az = coord_a
            bx, by, bz = coord_b
            dx = float(ax) - float(bx)
            dy = float(ay) - float(by)
            dz = float(az) - float(bz)
            return round(math.sqrt(dx ** 2 + dy ** 2 + dz ** 2), 2)
        except Exception:
            return 0.0

    def refresh_debug_waypoint_dropdown(self):
        if not self.debug_mode or not hasattr(self, "debug_waypoint_dropdown"):
            return

        self.debug_waypoint_entries = []

        values = []
        for i, entry in enumerate(self.my_route):
            if not isinstance(entry, dict):
                continue

            name = str(entry.get("name", "")).strip()
            if not name:
                continue

            label = f"{i + 1} | {name}"
            values.append(label)
            self.debug_waypoint_entries.append({
                "label": label,
                "index": i,
                "entry": entry,
            })

        self.debug_waypoint_dropdown.configure(values=tuple(values))

        if values:
            next_index = 0
            if 0 <= int(self.route_index) < len(values):
                next_index = int(self.route_index)
            self.debug_waypoint_dropdown.current(next_index)
        else:
            self.debug_waypoint_var.set("")

    def get_selected_debug_waypoint_entry(self):
        if not self.debug_mode or not hasattr(self, "debug_waypoint_dropdown"):
            return None

        try:
            selected_index = self.debug_waypoint_dropdown.current()
        except Exception:
            return None

        if selected_index is None or selected_index < 0:
            return None

        if selected_index >= len(self.debug_waypoint_entries):
            return None

        return self.debug_waypoint_entries[selected_index]

    def get_next_debug_waypoint_entry(self):
        if not self.debug_mode:
            return None

        if not self.my_route:
            return None

        try:
            next_index = int(self.route_index)
        except Exception:
            next_index = 0

        if next_index < 0:
            next_index = 0

        if next_index >= len(self.my_route):
            return None

        route_entry = self.get_route_entry_by_index(next_index)
        if not route_entry:
            return None

        label = f"{next_index + 1} | {str(route_entry.get('name', '')).strip()}"

        return {
            "label": label,
            "index": next_index,
            "entry": route_entry,
        }

    def simulate_jump_to_route_entry(self, route_index, route_entry, source_label="DEBUG"):
        if not route_entry:
            return False

        system_name = str(route_entry.get("name", "")).strip()
        x = route_entry.get("x")
        y = route_entry.get("y")
        z = route_entry.get("z")

        if not system_name:
            messagebox.showerror(
                "Missing System Name",
                "The selected route entry has no valid system name."
            )
            return False

        if x is None or y is None or z is None:
            messagebox.showerror(
                "Missing Coordinates",
                "The selected waypoint has no valid coordinates."
            )
            return False

        target_coords = (x, y, z)
        jump_distance = 0.0

        if (
            self.current_system_coords
            and isinstance(self.current_system_coords, (list, tuple))
            and len(self.current_system_coords) == 3
        ):
            jump_distance = self._calculate_precise_distance(
                self.current_system_coords,
                target_coords,
            )
        elif route_index > 0:
            previous_entry = self.get_route_entry_by_index(route_index - 1)
            if previous_entry:
                previous_coords = (
                    previous_entry.get("x", 0.0),
                    previous_entry.get("y", 0.0),
                    previous_entry.get("z", 0.0),
                )
                jump_distance = self._calculate_precise_distance(
                    previous_coords,
                    target_coords,
                )

        event_data = {
            "event": "FSDJump",
            "StarSystem": system_name,
            "StarPos": [x, y, z],
            "JumpDist": jump_distance,
        }

        self.log(
            f"[DEBUG] {source_label}: waypoint {route_index + 1}: "
            f"{system_name} ({jump_distance:.2f} LY)"
        )

        was_paused = self.is_paused
        self.is_paused = False
        try:
            self.jump_detected(event_data, False)
        finally:
            self.is_paused = was_paused

        if self.debug_mode and hasattr(self, "debug_waypoint_dropdown"):
            self.refresh_debug_waypoint_dropdown()

        return True

    def simulate_selected_jump(self):
        if not self.my_route:
            if not self.read_route_file():
                messagebox.showwarning(
                    "No Route Loaded",
                    "Please load a valid route first."
                )
                return

        selected_item = self.get_selected_debug_waypoint_entry()
        if not selected_item:
            messagebox.showwarning(
                "No Waypoint Selected",
                "Please select a waypoint to simulate."
            )
            return

        self.simulate_jump_to_route_entry(
            route_index=int(selected_item.get("index", 0)),
            route_entry=selected_item.get("entry", {}),
            source_label="Simulate Selected",
        )

    def simulate_next_waypoint(self):
        if not self.my_route:
            if not self.read_route_file():
                messagebox.showwarning(
                    "No Route Loaded",
                    "Please load a valid route first."
                )
                return

        next_item = self.get_next_debug_waypoint_entry()
        if not next_item:
            messagebox.showinfo(
                "No Next Waypoint",
                "There is no next waypoint left to simulate."
            )
            return

        self.simulate_jump_to_route_entry(
            route_index=int(next_item.get("index", 0)),
            route_entry=next_item.get("entry", {}),
            source_label="Simulate Next",
        )

    def toggle_auto_simulate_route(self):
        if self.debug_auto_simulation_active:
            self.stop_auto_simulate_route()
        else:
            self.start_auto_simulate_route()

    def start_auto_simulate_route(self):
        if not self.my_route:
            if not self.read_route_file():
                messagebox.showwarning(
                    "No Route Loaded",
                    "Please load a valid route first."
                )
                return

        next_item = self.get_next_debug_waypoint_entry()
        if not next_item:
            messagebox.showinfo(
                "No Next Waypoint",
                "There is no next waypoint left to simulate."
            )
            return

        self.debug_auto_simulation_active = True

        if hasattr(self, "debug_auto_btn"):
            self.debug_auto_btn.config(text="Stop Auto Simulation")

        self.log("[DEBUG] Starting automatic route simulation.")
        self._run_auto_simulation_tick()

    def stop_auto_simulate_route(self, log_message=True):
        self.debug_auto_simulation_active = False

        if self.debug_auto_simulation_after_id is not None:
            try:
                self.root.after_cancel(self.debug_auto_simulation_after_id)
            except Exception:
                pass
            self.debug_auto_simulation_after_id = None

        if hasattr(self, "debug_auto_btn"):
            self.debug_auto_btn.config(text="Auto Simulate Route")

        if log_message:
            self.log("[DEBUG] Automatic route simulation stopped.")

    def _run_auto_simulation_tick(self):
        self.debug_auto_simulation_after_id = None

        if not self.debug_auto_simulation_active:
            return

        next_item = self.get_next_debug_waypoint_entry()
        if not next_item:
            self.stop_auto_simulate_route(log_message=False)
            self.log("[DEBUG] Automatic route simulation finished.")
            return

        success = self.simulate_jump_to_route_entry(
            route_index=int(next_item.get("index", 0)),
            route_entry=next_item.get("entry", {}),
            source_label="Auto Simulate",
        )

        if not success:
            self.stop_auto_simulate_route()
            return

        if self.route_index >= len(self.my_route):
            self.stop_auto_simulate_route(log_message=False)
            self.log("[DEBUG] Automatic route simulation finished.")
            return

        self.debug_auto_simulation_after_id = self.root.after(
            self.debug_auto_simulation_delay_ms,
            self._run_auto_simulation_tick,
        )

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
                route_rows.append({
                    "waypoint_no": i + 1,
                    "system_name": str(system_name),
                    "distance": float(item.get("distance", 0.0) or 0.0),
                    "scoopable": None if item.get("is_scoopable") is None
                                 else bool(item.get("is_scoopable")),
                    "neutron_star": bool(item.get("has_neutron", False)),
                    "jumps_to_reach": i,
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "z": item.get("z"),
                })

        elif route_type == "Neutron Plotter":
            cumulative_jumps = 0
            for i, item in enumerate(raw_jumps):
                if not isinstance(item, dict):
                    continue
                system_name = item.get("system")
                if not system_name:
                    continue
                jumps_this_leg = int(item.get("jumps", 0) or 0)
                cumulative_jumps = 0 if i == 0 else cumulative_jumps + jumps_this_leg
                route_rows.append({
                    "waypoint_no": i + 1,
                    "system_name": str(system_name),
                    "distance": float(item.get("distance_jumped", 0.0) or 0.0),
                    "scoopable": None,
                    "neutron_star": bool(item.get("neutron_star", False)),
                    "jumps_to_reach": cumulative_jumps,
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "z": item.get("z"),
                })

        else:
            cumulative_jumps = 0
            for i, item in enumerate(raw_jumps):
                if not isinstance(item, dict):
                    continue
                system_name = (
                    item.get("name") or item.get("system") or item.get("system_name")
                )
                if not system_name:
                    continue
                distance = item.get("distance", 0.0)
                if "distance_to_star" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_to_star", 0.0)
                distance = float(distance or 0.0)
                scoopable = item.get("is_scoopable", item.get("scoopable", None))
                neutron_star = item.get("has_neutron", False)
                if (
                    item.get("neutron_star")
                    or item.get("star_type") == "N"
                    or item.get("star_class") == "N"
                ):
                    neutron_star = True
                jumps_this_leg = int(item.get("jumps", 1) or 1)
                cumulative_jumps = (
                    0 if i == 0 and distance == 0
                    else cumulative_jumps + jumps_this_leg
                )
                route_rows.append({
                    "waypoint_no": i + 1,
                    "system_name": str(system_name),
                    "distance": distance,
                    "scoopable": None if scoopable is None else bool(scoopable),
                    "neutron_star": bool(neutron_star),
                    "jumps_to_reach": cumulative_jumps,
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "z": item.get("z"),
                })

        return route_rows

    def get_waypoint_jumps(self, system_name):
        route_entry = self.get_route_entry_by_name(system_name)
        if not route_entry:
            return 0
        return int(route_entry.get("jumps", 0) or 0)

    def detect_systems_route_type(self, raw_systems):
        has_r2r_markers = False
        has_exo_markers = False

        for system in raw_systems:
            if not isinstance(system, dict):
                continue

            bodies = system.get("bodies", [])
            if not isinstance(bodies, list):
                continue

            for body in bodies:
                if not isinstance(body, dict):
                    continue

                # Road to Riches marker
                if (
                    body.get("estimated_scan_value") is not None
                    or body.get("estimated_mapping_value") is not None
                ):
                    has_r2r_markers = True

                # Exobiology marker
                landmarks = body.get("landmarks", [])
                if isinstance(landmarks, list) and len(landmarks) > 0:
                    has_exo_markers = True

        # Prefer R2R if scan/mapping values are present
        if has_r2r_markers:
            return "Road to Riches"
        if has_exo_markers:
            return "Exobiology"

        return "Road to Riches"

    def read_route_file(self):
        file_path = self.file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror(
                "Error",
                "Please select or drop a valid existing route JSON file first!"
            )
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                route_data = json.load(f)

            raw_jumps = []
            route_type = "Unknown Spansh Route"
            result_data = route_data.get("result")

            if isinstance(result_data, dict) and "jumps" in result_data:
                raw_jumps = result_data["jumps"]
                route_type = "Galaxy Plotter"

            elif isinstance(result_data, dict) and "system_jumps" in result_data:
                raw_jumps = result_data["system_jumps"]
                route_type = "Neutron Plotter"

            elif isinstance(result_data, list):
                raw_jumps = result_data
                route_type = self.detect_systems_route_type(raw_jumps)

            elif "jumps" in route_data:
                raw_jumps = route_data["jumps"]
                route_type = "Standard Jump Route"

            elif "systems" in route_data:
                raw_jumps = route_data["systems"]
                route_type = self.detect_systems_route_type(raw_jumps)

            elif isinstance(result_data, dict) and "systems" in result_data:
                raw_jumps = result_data["systems"]
                route_type = self.detect_systems_route_type(raw_jumps)

            elif "route" in route_data:
                raw_jumps = route_data["route"]
                route_type = "Fleet Carrier Route"

            else:
                raise ValueError(
                    "Unknown Spansh JSON structure. Could not find a jumps or systems list."
                )

            parsed_route = []
            for item in raw_jumps:
                if not isinstance(item, dict):
                    continue

                name = (
                    item.get("name") or item.get("system") or item.get("system_name")
                )
                if not name:
                    continue

                distance = item.get("distance", 0.0)
                if "distance_to_star" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_to_star", 0.0)
                if "distance_jumped" in item and (distance == 0.0 or distance is None):
                    distance = item.get("distance_jumped", 0.0)

                is_scoopable = item.get("is_scoopable", item.get("scoopable", None))
                has_neutron = item.get("has_neutron", False)
                if (
                    item.get("neutron_star")
                    or item.get("star_type") == "N"
                    or item.get("star_class") == "N"
                ):
                    has_neutron = True

                parsed_route.append({
                    "name": str(name),
                    "is_scoopable": None if is_scoopable is None else bool(is_scoopable),
                    "has_neutron": bool(has_neutron),
                    "distance": float(distance or 0.0),
                    "x": float(item.get("x", 0.0) or 0.0),
                    "y": float(item.get("y", 0.0) or 0.0),
                    "z": float(item.get("z", 0.0) or 0.0),
                    "jumps": int(item.get("jumps", 0) or 0),
                    "bodies": item.get("bodies", []),
                })

            if not parsed_route:
                raise ValueError("No valid systems could be parsed from the file.")

            self.my_route = parsed_route
            self.route_index = 0
            self.route_type = route_type
            self.last_route_file = file_path
            self.last_next_waypoint_name = ""
            self.last_next_waypoint_coords = None
            self.route_context_row_data = None

            route_rows = self.build_route_table_data(route_type, raw_jumps)
            self.populate_route_table(route_rows, route_type=route_type)
            self.refresh_debug_waypoint_dropdown()

        except Exception as e:
            messagebox.showerror(
                "JSON Error",
                f"Failed to read or parse the JSON file:\n{e}"
            )
            return False

        self.log(
            f"Successfully loaded and standardized {route_type} "
            f"with {len(self.my_route)} route entries."
        )
        self.save_settings()
        return True

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------
    def open_about_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"About - Spansh VR Navigator v{__version__}")
        dialog.geometry("700x420")
        dialog.minsize(620, 360)
        dialog.transient(self.root)
        dialog.grab_set()

        t = THEMES[self.current_theme_name]
        dialog.config(bg=t["bg"])

        main_frame = tk.Frame(dialog, bg=t["bg"], padx=18, pady=18)
        main_frame.pack(fill="both", expand=True)

        # --------------------------------------------------------------
        # Top area: icon + title/version
        # --------------------------------------------------------------
        top_frame = tk.Frame(main_frame, bg=t["bg"])
        top_frame.pack(fill="x", pady=(0, 14))

        icon_canvas = tk.Canvas(
            top_frame,
            width=92,
            height=92,
            bg=t["bg"],
            highlightthickness=0,
            bd=0,
        )
        icon_canvas.pack(side="left", padx=(0, 16))

        # Small custom HUD / navigator style icon
        cx, cy = 46, 46
        icon_canvas.create_oval(10, 10, 82, 82, outline=t["accent_fg"], width=2)
        icon_canvas.create_oval(20, 20, 72, 72, outline=t["panel_border"], width=1)
        icon_canvas.create_line(cx, 14, cx, 78, fill=t["accent_fg"], width=2)
        icon_canvas.create_line(14, cy, 78, cy, fill=t["accent_fg"], width=2)
        icon_canvas.create_oval(40, 40, 52, 52, fill=t["accent_fg"], outline=t["accent_fg"])
        icon_canvas.create_line(24, 24, 34, 34, fill=t["value_fg"], width=2)
        icon_canvas.create_line(58, 58, 68, 68, fill=t["value_fg"], width=2)
        icon_canvas.create_line(58, 34, 68, 24, fill=t["label_fg"], width=2)
        icon_canvas.create_line(24, 68, 34, 58, fill=t["label_fg"], width=2)

        text_frame = tk.Frame(top_frame, bg=t["bg"])
        text_frame.pack(side="left", fill="both", expand=True)

        tk.Label(
            text_frame,
            text="Elite Dangerous - Spansh VR Navigator",
            font=("Arial", 16, "bold"),
            bg=t["bg"],
            fg=t["label_fg"],
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(6, 6))

        tk.Label(
            text_frame,
            text=f"Version {__version__}",
            font=("Consolas", 11, "bold"),
            bg=t["bg"],
            fg=t["accent_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        tk.Label(
            text_frame,
            text="VR route helper for Elite Dangerous / Spansh",
            font=("Arial", 10),
            bg=t["bg"],
            fg=t["value_fg"],
            anchor="w",
        ).pack(fill="x")

        # --------------------------------------------------------------
        # Separator
        # --------------------------------------------------------------
        tk.Frame(main_frame, bg=t["panel_border"], height=1).pack(fill="x", pady=(4, 14))

        # --------------------------------------------------------------
        # Information block
        # --------------------------------------------------------------
        info_frame = tk.Frame(main_frame, bg=t["bg"])
        info_frame.pack(fill="both", expand=True)

        info_lines = [
            "Author: Bernard Härri (CMDR Weedy Gonzalez), but mostly LLMs",
            "Purpose: VR navigation helper for Elite Dangerous / Spansh routes",
            "Supported routes: Galaxy Plotter, Neutron Plotter, Road to Riches, Exobiology",
            "Build command: pyinstaller --noconsole --onefile ed_spansh_helper.py",
        ]

        for line in info_lines:
            tk.Label(
                info_frame,
                text=line,
                font=("Arial", 10),
                bg=t["bg"],
                fg=t["fg"],
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=2)

        tk.Frame(main_frame, bg=t["panel_border"], height=1).pack(fill="x", pady=14)

        tk.Label(
            main_frame,
            text=(
                "This tool monitors Elite Dangerous journal files and generates\n"
                "a cockpit / kneeboard navigation image for VR use."
            ),
            font=("Arial", 10),
            bg=t["bg"],
            fg=t["value_fg"],
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 16))

        # --------------------------------------------------------------
        # Bottom buttons
        # --------------------------------------------------------------
        button_row = tk.Frame(main_frame, bg=t["bg"])
        button_row.pack(fill="x", side="bottom")

        def copy_version():
            if self.copy_to_clipboard(__version__):
                self.log(f"Copied app version to clipboard: {__version__}")

        tk.Button(
            button_row,
            text="Copy Version",
            command=copy_version,
            bg=t["btn_pause_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_start_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Arial", 10, "bold"),
        ).pack(side="left")

        tk.Button(
            button_row,
            text="Close",
            command=dialog.destroy,
            bg=t["btn_start_bg"],
            fg=t["btn_fg"],
            activebackground=t["btn_pause_bg"],
            activeforeground=t["btn_fg"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            font=("Arial", 10, "bold"),
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------
    def open_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("760x620")
        dialog.minsize(680, 560)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.config(bg="#000000")

        style = ttk.Style()
        style.configure(
            "Settings.TNotebook",
            background="#000000",
            bordercolor="#ff7300",
            tabmargins=[2, 4, 0, 0],
        )
        style.configure(
            "Settings.TNotebook.Tab",
            background="#1a1a1a",
            foreground="#ff7300",
            padding=[12, 5],
            font=("Arial", 10, "bold"),
        )
        style.map(
            "Settings.TNotebook.Tab",
            background=[("selected", "#000000"), ("active", "#2a2a2a")],
            foreground=[("selected", "#ff7300"), ("active", "#ffaa44")],
        )

        notebook = ttk.Notebook(dialog, style="Settings.TNotebook")
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # ==============================================================
        # Tab 1: General Settings
        # ==============================================================
        tab_files = tk.Frame(notebook, bg="#000000")
        notebook.add(tab_files, text="  General Settings  ")
        tab_files.columnconfigure(0, weight=1)
        tab_files.columnconfigure(1, weight=0)

        tk.Label(
            tab_files,
            text="ED Journal Directory:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(14, 2))

        journal_var = tk.StringVar(value=self.journal_dir)
        tk.Entry(
            tab_files,
            textvariable=journal_var,
            bg="#1a1a1a", fg="#ff7300",
            insertbackground="#ff7300",
            font=("Consolas", 9), relief="flat", bd=4,
        ).grid(row=1, column=0, sticky="ew", padx=(12, 4), pady=(0, 8), ipady=4)

        def browse_journal():
            selected = filedialog.askdirectory(
                initialdir=journal_var.get(),
                title="Select ED Journal Directory",
            )
            if selected:
                journal_var.set(os.path.normpath(selected))

        tk.Button(
            tab_files, text="Browse...", command=browse_journal,
            bg="#000000", fg="#ff7300",
            activebackground="#1a1a1a", activeforeground="#ffaa44",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 8))

        tk.Label(
            tab_files,
            text="Kneeboard Image Output File:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 2))

        kneeboard_var = tk.StringVar(value=self.kneeboard_output_img_file)
        tk.Entry(
            tab_files,
            textvariable=kneeboard_var,
            bg="#1a1a1a", fg="#ff7300",
            insertbackground="#ff7300",
            font=("Consolas", 9), relief="flat", bd=4,
        ).grid(row=3, column=0, sticky="ew", padx=(12, 4), pady=(0, 8), ipady=4)

        def browse_kneeboard():
            initial_dir = (
                os.path.dirname(kneeboard_var.get())
                if kneeboard_var.get() else os.path.expanduser("~")
            )
            initial_file = (
                os.path.basename(kneeboard_var.get())
                if kneeboard_var.get() else "vr_navigation.png"
            )
            selected = filedialog.asksaveasfilename(
                initialdir=initial_dir,
                initialfile=initial_file,
                title="Select Kneeboard Image Output File",
                defaultextension=".png",
                filetypes=[("PNG Files", "*.png")],
            )
            if selected:
                kneeboard_var.set(os.path.normpath(selected))

        tk.Button(
            tab_files, text="Browse...", command=browse_kneeboard,
            bg="#000000", fg="#ff7300",
            activebackground="#1a1a1a", activeforeground="#ffaa44",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        ).grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=(0, 8))

        tk.Label(
            tab_files,
            text="Road to Riches Value Display:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 2))

        r2r_mode_map = {
            "Scan only": "scan",
            "Mapping only": "mapping",
            "Scan + Mapping": "both",
        }
        r2r_mode_reverse_map = {v: k for k, v in r2r_mode_map.items()}

        r2r_mode_var = tk.StringVar(
            value=r2r_mode_reverse_map.get(self.r2r_value_mode, "Scan + Mapping")
        )

        r2r_mode_dropdown = ttk.Combobox(
            tab_files,
            textvariable=r2r_mode_var,
            state="readonly",
            values=list(r2r_mode_map.keys()),
            style="Orange.TCombobox",
            width=28,
        )
        r2r_mode_dropdown.grid(
            row=5, column=0, columnspan=2,
            sticky="w", padx=12, pady=(0, 8)
        )

        # ==============================================================
        # Tab 2: VR Runtime
        # ==============================================================
        tab_vr = tk.Frame(notebook, bg="#000000")
        notebook.add(tab_vr, text="  VR Runtime  ")
        tab_vr.columnconfigure(0, weight=1)
        tab_vr.columnconfigure(1, weight=0)
        tab_vr.columnconfigure(2, weight=0)
        tab_vr.columnconfigure(3, weight=0)

        tk.Label(
            tab_vr,
            text="OpenXR DLL Source (downloaded by the user):",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(12, 2))

        openxr_source_var = tk.StringVar(value=self.openxr_dll_source)

        tk.Entry(
            tab_vr,
            textvariable=openxr_source_var,
            bg="#1a1a1a", fg="#ff7300",
            insertbackground="#ff7300",
            font=("Consolas", 9), relief="flat", bd=4,
        ).grid(
            row=1, column=0, columnspan=3,
            sticky="ew", padx=(12, 4), pady=(0, 4), ipady=4
        )

        def browse_openxr_source():
            selected = filedialog.askopenfilename(
                initialdir=(
                    os.path.dirname(openxr_source_var.get())
                    if openxr_source_var.get()
                    else os.path.expanduser("~")
                ),
                title="Select OpenXR DLL",
                filetypes=[("DLL Files", "*.dll"), ("All Files", "*.*")],
            )
            if selected:
                openxr_source_var.set(os.path.normpath(selected))

        tk.Button(
            tab_vr, text="Browse...", command=browse_openxr_source,
            bg="#000000", fg="#ff7300",
            activebackground="#1a1a1a", activeforeground="#ffaa44",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        ).grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=(0, 4))

        tk.Frame(tab_vr, bg="#ff7300", height=1).grid(
            row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=(4, 8)
        )

        vr_versions_tmp: list[dict[str, str]] = [dict(item) for item in self.vr_versions]
        selected_vr_var = tk.StringVar()
        version_name_var = tk.StringVar()
        version_path_var = tk.StringVar()
        status_var = tk.StringVar(value="No stored game version")

        current_loaded_name: dict[str, str | None] = {"value": None}
        ignore_name_focus: dict[str, bool] = {"value": False}
        ignore_path_focus: dict[str, bool] = {"value": False}

        tk.Label(
            tab_vr,
            text="Stored Game Versions:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=12, pady=(0, 2))

        vr_dropdown = ttk.Combobox(
            tab_vr,
            textvariable=selected_vr_var,
            state="readonly",
            style="Orange.TCombobox",
            width=36,
        )
        vr_dropdown.grid(row=4, column=0, sticky="ew", padx=(12, 4), pady=(0, 8))

        tk.Button(
            tab_vr,
            text="+",
            command=lambda: self.open_add_vr_version_dialog(dialog, add_vr_version),
            bg="#ff7300", fg="#000000",
            activebackground="#cc5c00", activeforeground="#000000",
            relief="flat", bd=2, padx=12, pady=3,
            font=("Arial", 10, "bold"),
        ).grid(row=4, column=1, sticky="ew", padx=(0, 4), pady=(0, 8))

        tk.Button(
            tab_vr,
            text="-",
            command=lambda: remove_vr_version(),
            bg="#8c2f00", fg="#ffffff",
            activebackground="#aa3a00", activeforeground="#ffffff",
            relief="flat", bd=2, padx=12, pady=3,
            font=("Arial", 10, "bold"),
        ).grid(row=4, column=2, sticky="ew", padx=(0, 12), pady=(0, 8))

        tk.Label(
            tab_vr,
            text="Version Name:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=5, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 2))

        version_name_entry = tk.Entry(
            tab_vr,
            textvariable=version_name_var,
            bg="#1a1a1a", fg="#ff7300",
            insertbackground="#ff7300",
            font=("Consolas", 9), relief="flat", bd=4,
        )
        version_name_entry.grid(
            row=6, column=0, columnspan=4,
            sticky="ew", padx=12, pady=(0, 8), ipady=4
        )

        tk.Label(
            tab_vr,
            text="Game Path:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=7, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 2))

        version_path_entry = tk.Entry(
            tab_vr,
            textvariable=version_path_var,
            bg="#1a1a1a", fg="#ff7300",
            insertbackground="#ff7300",
            font=("Consolas", 9), relief="flat", bd=4,
        )
        version_path_entry.grid(
            row=8, column=0, columnspan=3,
            sticky="ew", padx=(12, 4), pady=(0, 4), ipady=4
        )

        def get_entry_by_name(name):
            for item in vr_versions_tmp:
                if item.get("name") == name:
                    return item
            return None

        def set_vr_controls_enabled(enabled):
            state = "normal" if enabled else "disabled"
            try:
                version_name_entry.config(state=state)
                version_path_entry.config(state=state)
                browse_game_path_btn.config(state=state)
                setup_btn.config(state=state)
                steamvr_btn.config(state=state)
                openxr_btn.config(state=state)
            except Exception:
                pass

        def update_status(path):
            mode = self.vr_detect_mode(path)
            status_var.set(self.vr_mode_label(mode))
            status_label.config(fg=self.vr_mode_color(mode))

        def refresh_vr_dropdown(select_name=None):
            names = [str(item.get("name") or "Unnamed Version") for item in vr_versions_tmp]
            vr_dropdown.configure(values=tuple(names))

            if not names:
                selected_vr_var.set("")
                current_loaded_name["value"] = None
                ignore_name_focus["value"] = True
                ignore_path_focus["value"] = True
                version_name_var.set("")
                version_path_var.set("")
                ignore_name_focus["value"] = False
                ignore_path_focus["value"] = False
                status_var.set("No stored game version")
                status_label.configure(fg="#808080")
                set_vr_controls_enabled(False)
                return

            target_name = select_name if select_name in names else names[0]
            selected_vr_var.set(str(target_name or ""))
            vr_dropdown.current(names.index(target_name))
            load_selected_version()

        def load_selected_version(event=None):
            selected_name = selected_vr_var.get().strip()
            entry = get_entry_by_name(selected_name)

            if not entry:
                current_loaded_name["value"] = None
                ignore_name_focus["value"] = True
                ignore_path_focus["value"] = True
                version_name_var.set("")
                version_path_var.set("")
                ignore_name_focus["value"] = False
                ignore_path_focus["value"] = False
                status_var.set("No game version selected")
                status_label.configure(fg="#808080")
                set_vr_controls_enabled(False)
                return

            current_loaded_name["value"] = str(entry.get("name") or "")

            ignore_name_focus["value"] = True
            ignore_path_focus["value"] = True
            version_name_var.set(str(entry.get("name") or ""))
            version_path_var.set(str(entry.get("path") or ""))
            ignore_name_focus["value"] = False
            ignore_path_focus["value"] = False

            update_status(str(entry.get("path") or ""))
            set_vr_controls_enabled(True)

        def apply_name_field(event=None):
            if ignore_name_focus["value"]:
                return

            old_name = current_loaded_name["value"]
            if not old_name:
                return

            entry = get_entry_by_name(old_name)
            if not entry:
                return

            existing_names = [item.get("name", "") for item in vr_versions_tmp]
            new_name = self.make_unique_name(
                version_name_var.get().strip(),
                existing_names,
                exclude_name=old_name,
            )

            entry["name"] = new_name
            current_loaded_name["value"] = new_name
            version_name_var.set(new_name)
            refresh_vr_dropdown(select_name=new_name)

        def apply_path_field(event=None):
            if ignore_path_focus["value"]:
                return

            current_name = current_loaded_name["value"]
            if not current_name:
                return

            entry = get_entry_by_name(current_name)
            if not entry:
                return

            raw_path = version_path_var.get().strip()
            normalized_path = os.path.normpath(raw_path) if raw_path else ""
            entry["path"] = normalized_path
            version_path_var.set(normalized_path)
            update_status(normalized_path)

        def add_vr_version(data):
            existing_names = [item.get("name", "") for item in vr_versions_tmp]
            unique_name = self.make_unique_name(data.get("name", ""), existing_names)
            path = os.path.normpath(data.get("path", "").strip())

            vr_versions_tmp.append({
                "name": unique_name,
                "path": path,
            })
            refresh_vr_dropdown(select_name=unique_name)

        def remove_vr_version():
            selected_name = selected_vr_var.get().strip()
            if not selected_name:
                messagebox.showwarning(
                    "No Selection",
                    "Please select a stored game version first.",
                    parent=dialog,
                )
                return

            entry = get_entry_by_name(selected_name)
            if not entry:
                messagebox.showerror(
                    "Version Not Found",
                    "The selected game version could not be found.",
                    parent=dialog,
                )
                return

            confirm = messagebox.askyesno(
                "Delete Game Version",
                f"Do you really want to delete the game version '{selected_name}'?",
                parent=dialog,
            )
            if not confirm:
                return

            index = vr_versions_tmp.index(entry)
            del vr_versions_tmp[index]

            if vr_versions_tmp:
                next_index = min(index, len(vr_versions_tmp) - 1)
                refresh_vr_dropdown(select_name=vr_versions_tmp[next_index]["name"])
            else:
                refresh_vr_dropdown()

        def browse_selected_game_path():
            selected_name = selected_vr_var.get().strip()
            if not selected_name:
                messagebox.showwarning(
                    "No Selection",
                    "Please select a stored game version first.",
                    parent=dialog,
                )
                return

            current_path = version_path_var.get().strip()
            initialdir = (
                current_path if os.path.isdir(current_path)
                else os.path.expanduser("~")
            )

            selected = filedialog.askdirectory(
                initialdir=initialdir,
                title="Select Elite Dangerous Game Directory",
                parent=dialog,
            )
            if selected:
                version_path_var.set(os.path.normpath(selected))
                apply_path_field()

        browse_game_path_btn = tk.Button(
            tab_vr,
            text="Browse...",
            command=browse_selected_game_path,
            bg="#000000", fg="#ff7300",
            activebackground="#1a1a1a", activeforeground="#ffaa44",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        )
        browse_game_path_btn.grid(row=8, column=3, sticky="ew", padx=(0, 12), pady=(0, 4))

        tk.Label(
            tab_vr,
            text="Status:",
            bg="#000000", fg="#ff7300",
            font=("Arial", 10, "bold"), anchor="w",
        ).grid(row=9, column=0, columnspan=4, sticky="w", padx=12, pady=(4, 2))

        status_label = tk.Label(
            tab_vr,
            textvariable=status_var,
            bg="#000000", fg="#808080",
            font=("Consolas", 10, "bold"), anchor="w",
        )
        status_label.grid(row=10, column=0, columnspan=4, sticky="w", padx=16, pady=(0, 6))

        action_row = tk.Frame(tab_vr, bg="#000000")
        action_row.grid(row=11, column=0, columnspan=4, sticky="w", padx=12, pady=(2, 10))

        def run_setup():
            apply_path_field()
            current_name = current_loaded_name["value"]
            entry = get_entry_by_name(current_name)
            if not entry:
                return

            ok, msg = self.vr_do_setup(entry.get("path", ""), openxr_source_var.get().strip())
            self.log(f"{current_name}: {msg}")
            update_status(entry.get("path", ""))

            if ok:
                messagebox.showinfo("VR Setup", msg, parent=dialog)
            else:
                messagebox.showerror("VR Setup Error", msg, parent=dialog)

        def switch_vr_mode(target_mode):
            apply_path_field()
            current_name = current_loaded_name["value"]
            entry = get_entry_by_name(current_name)
            if not entry:
                return

            ok, msg = self.vr_switch(entry.get("path", ""), target_mode)
            self.log(f"{current_name}: {msg}")
            update_status(entry.get("path", ""))

            if ok:
                messagebox.showinfo("VR Runtime", msg, parent=dialog)
            else:
                messagebox.showerror("VR Runtime Error", msg, parent=dialog)

        setup_btn = tk.Button(
            action_row, text="Setup / Re-Setup",
            command=run_setup,
            bg="#ff7300", fg="#000000",
            activebackground="#cc5c00", activeforeground="#000000",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        )
        setup_btn.pack(side="left", padx=(0, 10))

        steamvr_btn = tk.Button(
            action_row, text="→ SteamVR / OpenVR",
            command=lambda: switch_vr_mode("steamvr"),
            bg="#000000", fg="#ffd700",
            activebackground="#1a1a1a", activeforeground="#ffe566",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        )
        steamvr_btn.pack(side="left", padx=(0, 6))

        openxr_btn = tk.Button(
            action_row, text="→ OpenXR",
            command=lambda: switch_vr_mode("openxr"),
            bg="#000000", fg="#00d26a",
            activebackground="#1a1a1a", activeforeground="#33ff88",
            relief="flat", bd=2, padx=10, pady=3,
            font=("Arial", 9, "bold"),
        )
        openxr_btn.pack(side="left")

        vr_dropdown.bind("<<ComboboxSelected>>", load_selected_version)
        version_name_entry.bind("<FocusOut>", apply_name_field)
        version_name_entry.bind("<Return>", apply_name_field)
        version_path_entry.bind("<FocusOut>", apply_path_field)
        version_path_entry.bind("<Return>", apply_path_field)

        refresh_vr_dropdown()

        # ==============================================================
        # Bottom buttons
        # ==============================================================
        btn_row_main = tk.Frame(dialog, bg="#000000")
        btn_row_main.pack(fill="x", padx=10, pady=(0, 10))

        def save_and_close():
            apply_name_field()
            apply_path_field()

            self.journal_dir = journal_var.get().strip()
            self.kneeboard_output_img_file = kneeboard_var.get().strip()
            self.openxr_dll_source = openxr_source_var.get().strip()
            self.vr_versions = self.normalize_vr_versions(vr_versions_tmp)
            self.r2r_value_mode = r2r_mode_map.get(r2r_mode_var.get(), "both")

            self.save_settings()
            self.log("Settings saved.")
            self.log(f"  Journal Dir : {self.journal_dir}")
            self.log(f"  Kneeboard   : {self.kneeboard_output_img_file}")
            self.log(f"  OpenXR DLL  : {self.openxr_dll_source}")
            self.log(f"  VR Versions : {len(self.vr_versions)}")
            self.log(f"  R2R Mode    : {self.r2r_value_mode}")
            dialog.destroy()

        tk.Button(
            btn_row_main, text="Cancel",
            command=dialog.destroy,
            bg="#000000", fg=BTN_FG_STOP,
            activebackground="#1a1a1a", activeforeground=BTN_FG_STOP,
            relief="flat", bd=2, padx=14, pady=4,
            font=("Arial", 10, "bold"),
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_row_main, text="Save & Close",
            command=save_and_close,
            bg="#000000", fg="#ff7300",
            activebackground="#1a1a1a", activeforeground="#ffaa44",
            relief="flat", bd=2, padx=14, pady=4,
            font=("Arial", 10, "bold"),
        ).pack(side="right")

    # ------------------------------------------------------------------
    # VR mode helpers
    # ------------------------------------------------------------------
    def vr_md5(self, file_path):
        try:
            h = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def vr_detect_mode(self, game_path):
        """
        Detect the active VR mode based on an MD5 comparison.

        Returns:
          'steamvr'      - active DLL matches the .steamvr backup
          'openxr'       - active DLL matches the .openxr backup
          'needs_setup'  - no backup exists yet
          'game_updated' - active DLL matches neither backup
          'unknown'      - invalid path or DLL missing
        """
        if not game_path or not os.path.isdir(game_path):
            return "unknown"

        dll = os.path.join(game_path, OPENVR_DLL)
        steamvr = os.path.join(game_path, OPENVR_DLL_STEAMVR)
        openxr = os.path.join(game_path, OPENVR_DLL_OPENXR)

        if not os.path.exists(dll):
            return "unknown"

        has_steamvr = os.path.exists(steamvr)
        has_openxr = os.path.exists(openxr)

        if not has_steamvr and not has_openxr:
            return "needs_setup"

        dll_md5 = self.vr_md5(dll)

        if has_steamvr and dll_md5 == self.vr_md5(steamvr):
            return "steamvr"
        if has_openxr and dll_md5 == self.vr_md5(openxr):
            return "openxr"

        return "game_updated"

    def vr_do_setup(self, game_path, openxr_source):
        """
        Initial setup or re-setup after a game update:
          1. openvr_api.dll  -> openvr_api.dll.steamvr
          2. openxr_source   -> openvr_api.dll.openxr

        Returns (success: bool, message: str).
        """
        if not game_path or not os.path.isdir(game_path):
            return False, f"Game path not found: {game_path}"

        dll = os.path.join(game_path, OPENVR_DLL)
        steamvr = os.path.join(game_path, OPENVR_DLL_STEAMVR)
        openxr = os.path.join(game_path, OPENVR_DLL_OPENXR)

        if not os.path.exists(dll):
            return False, f"{OPENVR_DLL} was not found in:\n{game_path}"

        if not openxr_source or not os.path.exists(openxr_source):
            return False, (
                "OpenXR DLL source was not found.\n"
                "Please set the path under 'OpenXR DLL Source'."
            )

        try:
            shutil.copy2(dll, steamvr)
            shutil.copy2(openxr_source, openxr)
            return True, (
                f"Setup completed successfully:\n"
                f"  {OPENVR_DLL_STEAMVR} created\n"
                f"  {OPENVR_DLL_OPENXR} copied"
            )
        except PermissionError:
            return False, "Access denied - please run the application as administrator."
        except Exception as e:
            return False, f"Setup failed: {e}"

    def vr_switch(self, game_path, target_mode):
        """
        Switch the VR mode by copying a backup DLL over openvr_api.dll.

        Returns (success: bool, message: str).
        """
        if not game_path or not os.path.isdir(game_path):
            return False, f"Game path not found: {game_path}"

        dll = os.path.join(game_path, OPENVR_DLL)
        steamvr = os.path.join(game_path, OPENVR_DLL_STEAMVR)
        openxr = os.path.join(game_path, OPENVR_DLL_OPENXR)

        try:
            if target_mode == "steamvr":
                if not os.path.exists(steamvr):
                    return False, (
                        f"{OPENVR_DLL_STEAMVR} was not found.\n"
                        f"Please run setup first."
                    )
                shutil.copy2(steamvr, dll)
                return True, "Successfully switched to SteamVR / OpenVR."

            if target_mode == "openxr":
                if not os.path.exists(openxr):
                    return False, (
                        f"{OPENVR_DLL_OPENXR} was not found.\n"
                        f"Please run setup first."
                    )
                shutil.copy2(openxr, dll)
                return True, "Successfully switched to OpenXR."

            return False, f"Unknown mode: {target_mode}"

        except PermissionError:
            return False, "Access denied - please run the application as administrator."
        except Exception as e:
            return False, f"Copy operation failed: {e}"

    def vr_mode_label(self, mode):
        return {
            "steamvr": "● SteamVR / OpenVR (active)",
            "openxr": "● OpenXR (active)",
            "needs_setup": "⚠ Setup required (first use)",
            "game_updated": "⚠ Game updated - run setup again",
            "unknown": "● Unknown / path not found",
        }.get(mode, "● ?")

    def vr_mode_color(self, mode):
        return {
            "steamvr": "#ffd700",
            "openxr": "#00d26a",
            "needs_setup": "#ff7300",
            "game_updated": "#ff3b30",
            "unknown": "#808080",
        }.get(mode, "#808080")

    # ------------------------------------------------------------------
    # Route logic
    # ------------------------------------------------------------------
    def get_route_entry_by_name(self, system_name):
        if not system_name:
            return None

        system_name_lc = str(system_name).strip().lower()

        for entry in self.my_route:
            entry_name = str(entry.get("name", "")).strip().lower()
            if entry_name == system_name_lc:
                return entry

        return None

    def get_route_entry_by_index(self, index):
        try:
            index = int(index)
        except Exception:
            return None

        if 0 <= index < len(self.my_route):
            return self.my_route[index]
        return None

    def get_next_waypoint_jumps(self):
        next_entry = self.get_route_entry_by_index(self.route_index)
        if not next_entry:
            return 0
        return int(next_entry.get("jumps", 0) or 0)

    def get_r2r_display_bodies(self, system_name, max_rows=None):
        route_entry = self.get_route_entry_by_name(system_name)
        if not route_entry:
            return []

        bodies = route_entry.get("bodies", [])
        if not isinstance(bodies, list):
            return []

        valid_bodies = [body for body in bodies if isinstance(body, dict)]

        if self.r2r_value_mode == "scan":
            sorted_bodies = sorted(
                valid_bodies,
                key=lambda body: (
                    int(body.get("estimated_scan_value", 0) or 0),
                    int(body.get("estimated_mapping_value", 0) or 0),
                    -(float(body.get("distance_to_arrival", 0) or 0)),
                ),
                reverse=True,
            )
        else:
            sorted_bodies = sorted(
                valid_bodies,
                key=lambda body: (
                    int(body.get("estimated_mapping_value", 0) or 0),
                    int(body.get("estimated_scan_value", 0) or 0),
                    -(float(body.get("distance_to_arrival", 0) or 0)),
                ),
                reverse=True,
            )

        if max_rows is None:
            return sorted_bodies

        return sorted_bodies[:max_rows]

    def get_r2r_totals(self, system_name):
        route_entry = self.get_route_entry_by_name(system_name)
        if not route_entry:
            return {
                "count": 0,
                "scan_total": 0,
                "mapping_total": 0,
            }

        bodies = route_entry.get("bodies", [])
        if not isinstance(bodies, list):
            bodies = []

        valid_bodies = [body for body in bodies if isinstance(body, dict)]

        return {
            "count": len(valid_bodies),
            "scan_total": sum(
                int(body.get("estimated_scan_value", 0) or 0)
                for body in valid_bodies
            ),
            "mapping_total": sum(
                int(body.get("estimated_mapping_value", 0) or 0)
                for body in valid_bodies
            ),
        }

    def _get_primary_landmark_subtype(self, body):
        landmarks = body.get("landmarks", [])
        if not isinstance(landmarks, list):
            return "-"

        valid_landmarks = [lm for lm in landmarks if isinstance(lm, dict)]
        if not valid_landmarks:
            return "-"

        best = max(
            valid_landmarks,
            key=lambda lm: (
                int(lm.get("value", 0) or 0),
                int(lm.get("count", 0) or 0),
                str(lm.get("subtype", "") or ""),
            ),
        )
        return str(best.get("subtype", "-") or "-")

    def get_exobiology_display_bodies(self, system_name, max_rows=None):
        route_entry = self.get_route_entry_by_name(system_name)
        if not route_entry:
            return []

        bodies = route_entry.get("bodies", [])
        if not isinstance(bodies, list):
            return []

        valid_bodies = [
            body for body in bodies
            if isinstance(body, dict) and (
                int(body.get("landmark_value", 0) or 0) > 0
                or (isinstance(body.get("landmarks", []), list) and body.get("landmarks"))
            )
        ]

        sorted_bodies = sorted(
            valid_bodies,
            key=lambda body: (
                -int(body.get("landmark_value", 0) or 0),
                float(body.get("distance_to_arrival", 0) or 0),
                str(body.get("name", "") or ""),
            ),
        )

        display_rows = []

        for body in sorted_bodies:
            body_name = str(body.get("name", "") or "")
            display_body_name = body_name.replace(f"{system_name} ", "", 1).strip()
            body_subtype = str(body.get("subtype", "") or "")
            body_color = self._get_body_subtype_color(body_subtype)
            distance_ls = int(round(float(body.get("distance_to_arrival", 0) or 0)))

            landmarks = body.get("landmarks", [])
            if not isinstance(landmarks, list):
                landmarks = []

            valid_landmarks = [lm for lm in landmarks if isinstance(lm, dict)]

            valid_landmarks = sorted(
                valid_landmarks,
                key=lambda lm: (
                    -int(lm.get("value", 0) or 0),
                    -int(lm.get("count", 0) or 0),
                    str(lm.get("subtype", "") or ""),
                ),
            )

            if not valid_landmarks:
                display_rows.append({
                    "display_body_name": display_body_name,
                    "body_color": body_color,
                    "distance_ls": distance_ls,
                    "landmark_value": int(body.get("landmark_value", 0) or 0),
                    "landmark_subtype": "-",
                })
                continue

            for idx, landmark in enumerate(valid_landmarks):
                landmark_subtype = str(landmark.get("subtype", "-") or "-")
                landmark_count = int(landmark.get("count", 0) or 0)
                landmark_value = int(landmark.get("value", 0) or 0)

                if landmark_count > 1:
                    landmark_subtype = f"{landmark_subtype} x{landmark_count}"

                display_rows.append({
                    "display_body_name": display_body_name if idx == 0 else "",
                    "body_color": body_color,
                    "distance_ls": distance_ls if idx == 0 else None,
                    "landmark_value": landmark_value,
                    "landmark_subtype": landmark_subtype,
                })

        if max_rows is None:
            return display_rows

        return display_rows[:max_rows]

    def get_exobiology_totals(self, system_name):
        route_entry = self.get_route_entry_by_name(system_name)
        if not route_entry:
            return {
                "count": 0,
                "landmark_total": 0,
            }

        bodies = route_entry.get("bodies", [])
        if not isinstance(bodies, list):
            bodies = []

        valid_bodies = [
            body for body in bodies
            if isinstance(body, dict) and (
                int(body.get("landmark_value", 0) or 0) > 0
                or (isinstance(body.get("landmarks", []), list) and body.get("landmarks"))
            )
        ]

        landmark_total = 0

        for body in valid_bodies:
            landmarks = body.get("landmarks", [])
            if isinstance(landmarks, list):
                valid_landmarks = [lm for lm in landmarks if isinstance(lm, dict)]
            else:
                valid_landmarks = []

            if valid_landmarks:
                landmark_total += sum(
                    int(lm.get("value", 0) or 0)
                    for lm in valid_landmarks
                )
            else:
                landmark_total += int(body.get("landmark_value", 0) or 0)

        return {
            "count": len(valid_bodies),
            "landmark_total": landmark_total,
        }

    def distance(self, destination_coord, current_coord):
        dest_x, dest_y, dest_z = destination_coord
        current_x, current_y, current_z = current_coord
        dx = dest_x - current_x
        dy = dest_y - current_y
        dz = dest_z - current_z
        return round(math.sqrt(dx ** 2 + dy ** 2 + dz ** 2), 0)

    def find_next_waypoint(self, system_name, current_coordinates):
        if not self.my_route:
            return None

        system_name_lc = str(system_name).strip().lower()
        current_index = -1
        on_route = False

        # Important for round trips:
        # start searching from the current route progress so duplicate system
        # names do not always resolve to the first occurrence in the route.
        search_start = min(max(int(self.route_index), 0), len(self.my_route) - 1)

        for i in range(search_start, len(self.my_route)):
            jump_name = str(self.my_route[i].get("name", "")).strip().lower()
            if jump_name == system_name_lc:
                current_index = i
                on_route = True
                break

        # Fallback: if nothing was found from the current progress onward,
        # search the entire route once.
        if current_index == -1:
            for i, jump in enumerate(self.my_route):
                jump_name = str(jump.get("name", "")).strip().lower()
                if jump_name == system_name_lc:
                    current_index = i
                    on_route = True
                    break

        if current_index == -1:
            self.log(
                "Current system is not in the route. "
                "Searching for the best matching route system..."
            )

            near_threshold_ly = self.OFF_ROUTE_ORDER_PRIORITY_THRESHOLD_LY
            closest_index = -1
            min_distance = float("inf")

            # First priority:
            # walk through the remaining route in order and select the earliest
            # waypoint that is within the configured threshold distance.
            for i in range(search_start, len(self.my_route)):
                jump = self.my_route[i]
                dist = self.distance(
                    (jump.get("x", 0.0), jump.get("y", 0.0), jump.get("z", 0.0)),
                    current_coordinates
                )

                if dist < min_distance:
                    min_distance = dist
                    closest_index = i

                if dist < near_threshold_ly:
                    current_index = i
                    self.log(
                        f"Selected route system by route order: "
                        f"{self.my_route[current_index]['name']} "
                        f"({dist} LY, within {near_threshold_ly:.0f} LY threshold)"
                    )
                    break

            # If no upcoming waypoint is within the threshold,
            # fall back to the closest waypoint in the remaining route.
            if current_index == -1 and closest_index != -1:
                current_index = closest_index
                self.log(
                    f"No route-ordered waypoint within {near_threshold_ly:.0f} LY. "
                    f"Using closest remaining route system: "
                    f"{self.my_route[current_index]['name']} ({min_distance} LY)"
                )

            # Final fallback:
            # if nothing usable was found in the remaining route, search the full route.
            if current_index == -1:
                closest_index = -1
                min_distance = float("inf")

                for i, jump in enumerate(self.my_route):
                    dist = self.distance(
                        (jump.get("x", 0.0), jump.get("y", 0.0), jump.get("z", 0.0)),
                        current_coordinates
                    )
                    if dist < min_distance:
                        min_distance = dist
                        closest_index = i

                current_index = closest_index
                if current_index != -1:
                    self.log(
                        f"Fallback to closest route system in full route: "
                        f"{self.my_route[current_index]['name']} ({min_distance} LY)"
                    )

            # Step one entry back so the next waypoint still points forward
            # from the matched route position.
            if current_index > 0:
                current_index -= 1

        if current_index == -1:
            return None

        # Advance route progress to the next route entry after the current system.
        self.route_index = current_index + 1

        if self.route_index >= len(self.my_route):
            return "ROUTE_FINISHED"

        next_system = self.my_route[self.route_index]
        remaining_route = self.my_route[self.route_index:]

        next_wp_coord = (
            next_system.get("x", 0.0),
            next_system.get("y", 0.0),
            next_system.get("z", 0.0),
        )
        final_destination_coord = (
            remaining_route[-1].get("x", 0.0),
            remaining_route[-1].get("y", 0.0),
            remaining_route[-1].get("z", 0.0),
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

    def _format_int(self, value):
        try:
            return f"{int(value):n}"
        except Exception:
            return "0"

    def _get_body_subtype_color(self, subtype):
        table_text = (240, 240, 245)
        rocky_grey = (185, 185, 185)
        water_blue = (80, 190, 255)
        earthlike_cyan = (80, 255, 220)
        ammonia_lime = (185, 220, 90)
        hmc_orange = (255, 185, 90)

        subtype_colors = {
            "Earth-like world": earthlike_cyan,
            "Water world": water_blue,
            "Ammonia world": ammonia_lime,
            "High metal content world": hmc_orange,
            "Rocky body": rocky_grey,
        }
        return subtype_colors.get(str(subtype or ""), table_text)

    def _get_nav_image_palette(self):
        return {
            "bg_color": (6, 8, 12),
            "line_dim": (80, 40, 0),
            "ed_orange": (255, 115, 0),
            "ed_orange_soft": (220, 100, 0),
            "ed_orange_dim": (150, 70, 0),
            "ed_cyan": (89, 223, 227),
            "color_on": (40, 210, 110),
            "color_off": (231, 76, 60),
            "table_header": (255, 170, 68),
            "table_text": (240, 240, 245),
        }

    def _load_nav_image_fonts(self, font_name="arial.ttf"):
        try:
            return {
                "big": ImageFont.truetype(font_name, 36),
                "medium": ImageFont.truetype(font_name, 24),
                "tiny": ImageFont.truetype(font_name, 14),
                "table_header": ImageFont.truetype(font_name, 22),
                "table_row": ImageFont.truetype(font_name, 30),
            }
        except IOError:
            default_font = ImageFont.load_default()
            return {
                "big": default_font,
                "medium": default_font,
                "tiny": default_font,
                "table_header": default_font,
                "table_row": default_font,
            }

    def _get_tabular_nav_layout(
        self,
        body_count,
        base_img_width=1000,
        base_img_height=620,
        row_height=None,
        base_rows=6,
    ):
        if row_height is None:
            row_height = self.TABLE_ROW_HEIGHT

        body_count_for_layout = max(int(body_count or 0), base_rows)
        extra_rows = max(0, body_count_for_layout - base_rows)
        height_extra = extra_rows * row_height

        return {
            "img_width": base_img_width,
            "img_height": base_img_height + height_extra,
            "height_extra": height_extra,
            "outer_bottom": 610 + height_extra,
            "inner_bottom": 598 + height_extra,
            "summary_line_y": 485 + height_extra,
            "summary_y_label": 500 + height_extra,
            "summary_y_value": 528 + height_extra,
            "summary_vline_top": 496 + height_extra,
            "summary_vline_bottom": 565 + height_extra,
            "bottom_corner_top": 568 + height_extra,
            "bottom_corner_bottom": 598 + height_extra,
        }

    def _format_next_waypoint_text(self, next_waypoint, next_waypoint_jumps=0):
        if not next_waypoint:
            return "-"

        jumps = int(next_waypoint_jumps or 0)
        if jumps <= 0:
            return str(next_waypoint).upper()

        jump_label = "JUMP" if jumps == 1 else "JUMPS"
        return f"{str(next_waypoint).upper()} ({jumps} {jump_label})"

    def _draw_nav_corner_accents(self, draw, bottom_corner_top, bottom_corner_bottom, colors):
        draw.line([(22, 22), (52, 22)], fill=colors["ed_orange"], width=2)
        draw.line([(22, 22), (22, 52)], fill=colors["ed_orange"], width=2)
        draw.line([(948, 22), (978, 22)], fill=colors["ed_orange"], width=2)
        draw.line([(978, 22), (978, 52)], fill=colors["ed_orange"], width=2)
        draw.line(
            [(22, bottom_corner_top), (22, bottom_corner_bottom)],
            fill=colors["ed_orange"],
            width=2
        )
        draw.line(
            [(22, bottom_corner_bottom), (52, bottom_corner_bottom)],
            fill=colors["ed_orange"],
            width=2
        )
        draw.line(
            [(948, bottom_corner_bottom), (978, bottom_corner_bottom)],
            fill=colors["ed_orange"],
            width=2
        )
        draw.line(
            [(978, bottom_corner_top), (978, bottom_corner_bottom)],
            fill=colors["ed_orange"],
            width=2
        )

    def _draw_tabular_nav_frame(self, draw, layout, colors):
        draw.rectangle(
            [(10, 10), (990, layout["outer_bottom"])],
            outline=colors["ed_orange"],
            width=2
        )
        draw.rectangle(
            [(22, 22), (978, layout["inner_bottom"])],
            outline=colors["ed_orange_dim"],
            width=1
        )

        draw.line([(35, 68), (965, 68)], fill=colors["ed_orange_dim"], width=1)
        draw.line([(35, 128), (965, 128)], fill=colors["line_dim"], width=1)
        draw.line(
            [(35, layout["summary_line_y"]), (965, layout["summary_line_y"])],
            fill=colors["line_dim"],
            width=1
        )

        self._draw_nav_corner_accents(
            draw,
            layout["bottom_corner_top"],
            layout["bottom_corner_bottom"],
            colors,
        )

    def _draw_tabular_nav_header(
        self,
        draw,
        title_text,
        current_system,
        next_waypoint_text,
        current_system_on_route,
        colors,
        fonts,
        font_name="arial.ttf",
    ):
        title_font = self._fit_font(
            draw, title_text, font_name,
            start_size=18, min_size=12, max_width=420
        )
        current_system_font = self._fit_font(
            draw, str(current_system).upper(), font_name,
            start_size=26, min_size=16, max_width=420
        )
        next_waypoint_font = self._fit_font(
            draw, str(next_waypoint_text), font_name,
            start_size=26, min_size=16, max_width=420
        )

        draw.text((40, 30), title_text, fill=colors["ed_orange"], font=title_font)

        draw.text(
            (42, 76),
            "CURRENT SYSTEM",
            fill=colors["ed_orange_soft"],
            font=fonts["tiny"]
        )
        draw.text(
            (42, 94),
            str(current_system).upper(),
            fill=colors["ed_cyan"],
            font=current_system_font
        )

        draw.text(
            (520, 76),
            "NEXT WAYPOINT",
            fill=colors["ed_orange_soft"],
            font=fonts["tiny"]
        )
        draw.text(
            (520, 94),
            str(next_waypoint_text),
            fill=colors["ed_orange"],
            font=next_waypoint_font
        )

        route_status_text = "ON ROUTE" if current_system_on_route else "OFF ROUTE"
        route_status_color = colors["color_on"] if current_system_on_route else colors["color_off"]

        route_dot_y = 28
        draw.ellipse(
            [(810, route_dot_y), (836, route_dot_y + 26)],
            fill=route_status_color
        )
        draw.text(
            (850, route_dot_y + 2),
            route_status_text,
            fill=colors["ed_orange"],
            font=fonts["medium"]
        )

    def _draw_table_headers(self, draw, table_top, table_left, table_right, columns, colors, fonts):
        for header, x, align in columns:
            if align == "left":
                draw.text(
                    (x, table_top),
                    header,
                    fill=colors["table_header"],
                    font=fonts["table_header"]
                )
            else:
                text_width = self._get_text_width(draw, header, fonts["table_header"])
                draw.text(
                    (x - text_width, table_top),
                    header,
                    fill=colors["table_header"],
                    font=fonts["table_header"]
                )

        draw.line(
            [(table_left, table_top + 30), (table_right, table_top + 30)],
            fill=colors["line_dim"],
            width=1
        )

    def _draw_summary_blocks(self, draw, items, layout, colors, fonts, separators=None):
        for item in items:
            draw.text(
                (item["x"], layout["summary_y_label"]),
                item["label"],
                fill=colors["ed_orange_dim"],
                font=fonts["tiny"]
            )
            draw.text(
                (item["x"], layout["summary_y_value"]),
                str(item["value"]),
                fill=item.get("color", colors["ed_orange"]),
                font=fonts["big"]
            )

        for x in (separators or []):
            draw.line(
                [(x, layout["summary_vline_top"]), (x, layout["summary_vline_bottom"])],
                fill=colors["line_dim"],
                width=1
            )

    def _get_table_row_y(self, table_top, row_index):
        return table_top + self.TABLE_FIRST_ROW_Y_OFFSET + (row_index * self.TABLE_ROW_HEIGHT)

    def _get_exobiology_columns(self):
        return [
            ("BODY", self.EXO_COL_BODY_X, "left"),
            ("DIST", self.EXO_COL_DIST_X, "right"),
            ("VALUE", self.EXO_COL_VALUE_X, "right"),
            ("LANDMARK SUBTYPE", self.EXO_COL_SUBTYPE_X, "left"),
        ]

    def _get_r2r_columns(self, value_mode):
        if value_mode == "scan":
            return [
                ("BODY", self.R2R_COL_BODY_X, "left"),
                ("DIST", self.R2R_SINGLE_COL_DIST_X, "right"),
                ("SCAN", self.R2R_SINGLE_COL_VALUE_X, "right"),
            ]
        elif value_mode == "mapping":
            return [
                ("BODY", self.R2R_COL_BODY_X, "left"),
                ("DIST", self.R2R_SINGLE_COL_DIST_X, "right"),
                ("MAP", self.R2R_SINGLE_COL_VALUE_X, "right"),
            ]
        else:
            return [
                ("BODY", self.R2R_COL_BODY_X, "left"),
                ("DIST", self.R2R_BOTH_COL_DIST_X, "right"),
                ("SCAN", self.R2R_BOTH_COL_SCAN_X, "right"),
                ("MAP", self.R2R_BOTH_COL_MAP_X, "right"),
            ]

    def _get_r2r_value_positions(self, value_mode):
        if value_mode == "scan":
            return {
                "body_x": self.R2R_COL_BODY_X,
                "dist_x": self.R2R_SINGLE_COL_DIST_X,
                "scan_x": self.R2R_SINGLE_COL_VALUE_X,
                "map_x": None,
            }
        elif value_mode == "mapping":
            return {
                "body_x": self.R2R_COL_BODY_X,
                "dist_x": self.R2R_SINGLE_COL_DIST_X,
                "scan_x": None,
                "map_x": self.R2R_SINGLE_COL_VALUE_X,
            }
        else:
            return {
                "body_x": self.R2R_COL_BODY_X,
                "dist_x": self.R2R_BOTH_COL_DIST_X,
                "scan_x": self.R2R_BOTH_COL_SCAN_X,
                "map_x": self.R2R_BOTH_COL_MAP_X,
            }

    def _get_r2r_summary_config(self, value_mode, body_count, scan_total, mapping_total, colors):
        if value_mode == "scan":
            return {
                "items": [
                    {
                        "x": self.SUMMARY_BODIES_X,
                        "label": "BODIES",
                        "value": f"{body_count}",
                        "color": colors["ed_orange"],
                    },
                    {
                        "x": self.R2R_SUMMARY_SINGLE_VALUE_X,
                        "label": "SCAN TOTAL",
                        "value": self._format_int(scan_total),
                        "color": colors["ed_orange"],
                    },
                ],
                "separators": [],
            }

        if value_mode == "mapping":
            return {
                "items": [
                    {
                        "x": self.SUMMARY_BODIES_X,
                        "label": "BODIES",
                        "value": f"{body_count}",
                        "color": colors["ed_orange"],
                    },
                    {
                        "x": self.R2R_SUMMARY_SINGLE_VALUE_X,
                        "label": "MAP TOTAL",
                        "value": self._format_int(mapping_total),
                        "color": colors["ed_orange"],
                    },
                ],
                "separators": [],
            }

        return {
            "items": [
                {
                    "x": self.SUMMARY_BODIES_X,
                    "label": "BODIES",
                    "value": f"{body_count}",
                    "color": colors["ed_orange"],
                },
                {
                    "x": self.R2R_SUMMARY_SCAN_X,
                    "label": "SCAN TOTAL",
                    "value": self._format_int(scan_total),
                    "color": colors["table_text"],
                },
                {
                    "x": self.R2R_SUMMARY_MAP_X,
                    "label": "MAP TOTAL",
                    "value": self._format_int(mapping_total),
                    "color": colors["ed_orange"],
                },
            ],
            "separators": [self.R2R_SUMMARY_SEP_LEFT_X, self.R2R_SUMMARY_SEP_RIGHT_X],
        }

    def _get_exobiology_summary_config(
        self,
        body_count,
        landmark_total,
        waypoints_left,
        colors,
    ):
        return {
            "items": [
                {
                    "x": self.SUMMARY_BODIES_X,
                    "label": "BODIES",
                    "value": f"{body_count}",
                    "color": colors["ed_orange"],
                },
                {
                    "x": self.EXO_SUMMARY_VALUE_X,
                    "label": "VALUE TOTAL",
                    "value": self._format_int(landmark_total),
                    "color": colors["ed_orange"],
                },
                {
                    "x": self.EXO_SUMMARY_WAYPOINTS_X,
                    "label": "WAYPOINTS LEFT",
                    "value": f"{int(waypoints_left or 0)}",
                    "color": colors["table_text"],
                },
            ],
            "separators": [
                self.EXO_SUMMARY_SEP_LEFT_X,
                self.EXO_SUMMARY_SEP_RIGHT_X,
            ],
        }

    def _save_kneeboard_image(self, img):
        output_dir = os.path.dirname(self.kneeboard_output_img_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        img.save(self.kneeboard_output_img_file)

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
        img_width = 1000
        img_height = 445

        bg_color = (6, 8, 12)
        line_dim = (80, 40, 0)
        ed_orange = (255, 115, 0)
        ed_orange_soft = (220, 100, 0)
        ed_orange_dim = (150, 70, 0)
        ed_cyan = (89, 223, 227)
        color_on = (40, 210, 110)
        color_off = (231, 76, 60)
        font_name = "arial.ttf"

        try:
            font_big = ImageFont.truetype(font_name, 28)
            font_medium = ImageFont.truetype(font_name, 22)
            font_small = ImageFont.truetype(font_name, 19)
        except IOError:
            font_big = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        img = Image.new("RGB", (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)

        title_text = f"NAVIGATION TO: {str(destination).upper()}"
        title_font = self._fit_font(
            draw, title_text, font_name,
            start_size=22, min_size=14, max_width=740
        )
        current_text = str(current_system).upper()
        current_font = self._fit_font(
            draw, current_text, font_name,
            start_size=38, min_size=20, max_width=900
        )
        next_text = f"{str(system_name).upper()} ({jump_distance:.0f} LY)"
        next_font = self._fit_font(
            draw, next_text, font_name,
            start_size=38, min_size=20, max_width=680
        )

        draw.rectangle([(10, 10), (990, 435)], outline=ed_orange, width=2)
        draw.rectangle([(22, 22), (978, 423)], outline=ed_orange_dim, width=1)

        draw.line([(35, 68), (965, 68)], fill=ed_orange_dim, width=1)
        draw.line([(35, 160), (965, 160)], fill=line_dim, width=1)
        draw.line([(35, 315), (965, 315)], fill=line_dim, width=1)

        draw.text((40, 28), title_text, fill=ed_orange, font=title_font)

        route_status_text = "ON ROUTE" if current_system_on_route else "OFF ROUTE"
        route_status_color = color_on if current_system_on_route else color_off
        route_dot_y = 30
        draw.ellipse(
            [(810, route_dot_y), (836, route_dot_y + 26)],
            fill=route_status_color
        )
        draw.text(
            (850, route_dot_y + 1),
            route_status_text,
            fill=ed_orange,
            font=font_medium
        )

        draw.text((45, 82), "CURRENT SYSTEM", fill=ed_orange_soft, font=font_small)
        draw.text((45, 108), current_text, fill=ed_cyan, font=current_font)
        draw.text((45, 178), "NEXT WAYPOINT", fill=ed_orange_soft, font=font_small)
        draw.text((45, 205), next_text, fill=ed_orange, font=next_font)

        neutron_color = color_on if neutron_star else color_off

        if scoopable_star is None:
            neutron_dot_x = 55
            neutron_text_x = 95
        else:
            scoop_color = color_on if scoopable_star else color_off

            draw.ellipse([(55, 265), (81, 291)], fill=scoop_color)
            draw.text((95, 266), "REFUEL", fill=ed_orange, font=font_medium)

            neutron_dot_x = 310
            neutron_text_x = 350

        draw.ellipse([(neutron_dot_x, 265), (neutron_dot_x + 26, 291)], fill=neutron_color)
        draw.text((neutron_text_x, 266), "NEUTRON STAR", fill=ed_orange, font=font_medium)

        metric_label_y = 335
        metric_value_y = 362

        draw.text(
            (70, metric_label_y),
            "JUMPS LEFT",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (70, metric_value_y),
            f"{jumps_remain}",
            fill=ed_orange,
            font=font_big
        )
        draw.text(
            (370, metric_label_y),
            "DISTANCE REMAINING",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (370, metric_value_y),
            f"{distance_remain:n} LY",
            fill=ed_orange,
            font=font_big
        )
        draw.text(
            (690, metric_label_y),
            "TRAVELED",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (690, metric_value_y),
            f"{distance_traveled:n} LY",
            fill=ed_orange,
            font=font_big
        )

        draw.line([(320, 330), (320, 400)], fill=line_dim, width=1)
        draw.line([(645, 330), (645, 400)], fill=line_dim, width=1)

        draw.line([(22, 22), (52, 22)], fill=ed_orange, width=2)
        draw.line([(22, 22), (22, 52)], fill=ed_orange, width=2)
        draw.line([(948, 22), (978, 22)], fill=ed_orange, width=2)
        draw.line([(978, 22), (978, 52)], fill=ed_orange, width=2)
        draw.line([(22, 393), (22, 423)], fill=ed_orange, width=2)
        draw.line([(22, 423), (52, 423)], fill=ed_orange, width=2)
        draw.line([(948, 423), (978, 423)], fill=ed_orange, width=2)
        draw.line([(978, 393), (978, 423)], fill=ed_orange, width=2)

        output_dir = os.path.dirname(self.kneeboard_output_img_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        img.save(self.kneeboard_output_img_file)

    def gen_road_to_riches_image(
        self,
        current_system,
        current_system_on_route,
        next_waypoint,
        bodies,
        totals,
        value_mode="both",
        next_waypoint_jumps=0,
    ):
        colors = self._get_nav_image_palette()
        fonts = self._load_nav_image_fonts()
        layout = self._get_tabular_nav_layout(len(bodies))

        img = Image.new(
            "RGB",
            (layout["img_width"], layout["img_height"]),
            color=colors["bg_color"]
        )
        draw = ImageDraw.Draw(img)

        next_waypoint_text = self._format_next_waypoint_text(
            next_waypoint,
            next_waypoint_jumps,
        )

        self._draw_tabular_nav_frame(draw, layout, colors)
        self._draw_tabular_nav_header(
            draw=draw,
            title_text="ROAD TO RICHES",
            current_system=current_system,
            next_waypoint_text=next_waypoint_text,
            current_system_on_route=current_system_on_route,
            colors=colors,
            fonts=fonts,
        )

        table_left = self.TABLE_LEFT
        table_right = self.TABLE_RIGHT
        table_top = self.TABLE_TOP
        columns = self._get_r2r_columns(value_mode)
        positions = self._get_r2r_value_positions(value_mode)

        self._draw_table_headers(
            draw=draw,
            table_top=table_top,
            table_left=table_left,
            table_right=table_right,
            columns=columns,
            colors=colors,
            fonts=fonts,
        )

        for i, body in enumerate(bodies):
            row_y = self._get_table_row_y(table_top, i)

            body_name = str(body.get("name", "") or "")
            display_body_name = body_name.replace(f"{current_system} ", "", 1).strip()
            subtype = str(body.get("subtype", "") or "")
            distance_ls = int(round(float(body.get("distance_to_arrival", 0) or 0)))
            scan_value = int(body.get("estimated_scan_value", 0) or 0)
            mapping_value = int(body.get("estimated_mapping_value", 0) or 0)

            body_color = self._get_body_subtype_color(subtype)

            draw.text(
                (positions["body_x"], row_y),
                display_body_name,
                fill=body_color,
                font=fonts["table_row"]
            )

            dist_text = f"{self._format_int(distance_ls)} LS"
            dist_width = self._get_text_width(draw, dist_text, fonts["table_row"])

            if value_mode == "scan":
                scan_text = self._format_int(scan_value)
                scan_width = self._get_text_width(draw, scan_text, fonts["table_row"])

                draw.text(
                    (positions["dist_x"] - dist_width, row_y),
                    dist_text,
                    fill=colors["table_text"],
                    font=fonts["table_row"]
                )
                draw.text(
                    (positions["scan_x"] - scan_width, row_y),
                    scan_text,
                    fill=colors["ed_orange"],
                    font=fonts["table_row"]
                )

            elif value_mode == "mapping":
                map_text = self._format_int(mapping_value)
                map_width = self._get_text_width(draw, map_text, fonts["table_row"])

                draw.text(
                    (positions["dist_x"] - dist_width, row_y),
                    dist_text,
                    fill=colors["table_text"],
                    font=fonts["table_row"]
                )
                draw.text(
                    (positions["map_x"] - map_width, row_y),
                    map_text,
                    fill=colors["ed_orange"],
                    font=fonts["table_row"]
                )

            else:
                scan_text = self._format_int(scan_value)
                map_text = self._format_int(mapping_value)
                scan_width = self._get_text_width(draw, scan_text, fonts["table_row"])
                map_width = self._get_text_width(draw, map_text, fonts["table_row"])

                draw.text(
                    (positions["dist_x"] - dist_width, row_y),
                    dist_text,
                    fill=colors["table_text"],
                    font=fonts["table_row"]
                )
                draw.text(
                    (positions["scan_x"] - scan_width, row_y),
                    scan_text,
                    fill=colors["table_text"],
                    font=fonts["table_row"]
                )
                draw.text(
                    (positions["map_x"] - map_width, row_y),
                    map_text,
                    fill=colors["ed_orange"],
                    font=fonts["table_row"]
                )

        body_count = int(totals.get("count", 0) or 0)
        scan_total = int(totals.get("scan_total", 0) or 0)
        mapping_total = int(totals.get("mapping_total", 0) or 0)

        summary_config = self._get_r2r_summary_config(
            value_mode=value_mode,
            body_count=body_count,
            scan_total=scan_total,
            mapping_total=mapping_total,
            colors=colors,
        )

        self._draw_summary_blocks(
            draw=draw,
            items=summary_config["items"],
            layout=layout,
            colors=colors,
            fonts=fonts,
            separators=summary_config["separators"],
        )

        self._save_kneeboard_image(img)

    def gen_exobiology_image(
        self,
        current_system,
        current_system_on_route,
        next_waypoint,
        bodies,
        totals,
        next_waypoint_jumps=0,
        waypoints_left=0,
    ):
        colors = self._get_nav_image_palette()
        fonts = self._load_nav_image_fonts()
        layout = self._get_tabular_nav_layout(len(bodies))
        font_name = self.NAV_FONT_NAME

        img = Image.new(
            "RGB",
            (layout["img_width"], layout["img_height"]),
            color=colors["bg_color"]
        )
        draw = ImageDraw.Draw(img)

        next_waypoint_text = self._format_next_waypoint_text(
            next_waypoint,
            next_waypoint_jumps,
        )

        self._draw_tabular_nav_frame(draw, layout, colors)
        self._draw_tabular_nav_header(
            draw=draw,
            title_text="EXOBIOLOGY",
            current_system=current_system,
            next_waypoint_text=next_waypoint_text,
            current_system_on_route=current_system_on_route,
            colors=colors,
            fonts=fonts,
        )

        table_left = self.TABLE_LEFT
        table_right = self.TABLE_RIGHT
        table_top = self.TABLE_TOP
        columns = self._get_exobiology_columns()

        self._draw_table_headers(
            draw=draw,
            table_top=table_top,
            table_left=table_left,
            table_right=table_right,
            columns=columns,
            colors=colors,
            fonts=fonts,
        )

        for i, body in enumerate(bodies):
            row_y = self._get_table_row_y(table_top, i)

            display_body_name = str(body.get("display_body_name", "") or "")
            body_color = body.get("body_color", colors["table_text"])
            distance_ls = body.get("distance_ls")
            landmark_value = body.get("landmark_value")
            landmark_subtype = str(body.get("landmark_subtype", "-") or "-")

            if display_body_name:
                body_font = self._fit_font(
                    draw,
                    display_body_name,
                    font_name,
                    start_size=self.EXO_BODY_FONT_START,
                    min_size=self.EXO_BODY_FONT_MIN,
                    max_width=self.EXO_BODY_MAX_WIDTH,
                )
                draw.text(
                    (self.EXO_COL_BODY_X, row_y),
                    display_body_name,
                    fill=body_color,
                    font=body_font
                )

            if distance_ls is not None:
                dist_text = f"{self._format_int(distance_ls)} LS"
                dist_width = self._get_text_width(draw, dist_text, fonts["table_row"])
                draw.text(
                    (self.EXO_COL_DIST_X - dist_width, row_y),
                    dist_text,
                    fill=colors["table_text"],
                    font=fonts["table_row"]
                )

            if landmark_value is not None:
                value_text = self._format_int(landmark_value)
                value_width = self._get_text_width(draw, value_text, fonts["table_row"])
                draw.text(
                    (self.EXO_COL_VALUE_X - value_width, row_y),
                    value_text,
                    fill=colors["ed_orange"],
                    font=fonts["table_row"]
                )

            subtype_font = self._fit_font(
                draw,
                landmark_subtype,
                font_name,
                start_size=self.EXO_SUBTYPE_FONT_START,
                min_size=self.EXO_SUBTYPE_FONT_MIN,
                max_width=self.EXO_SUBTYPE_MAX_WIDTH,
            )

            draw.text(
                (self.EXO_COL_SUBTYPE_X, row_y + 4),
                landmark_subtype,
                fill=colors["table_text"],
                font=subtype_font
            )

        body_count = int(totals.get("count", 0) or 0)
        landmark_total = int(totals.get("landmark_total", 0) or 0)

        summary_config = self._get_exobiology_summary_config(
            body_count=body_count,
            landmark_total=landmark_total,
            waypoints_left=waypoints_left,
            colors=colors,
        )

        self._draw_summary_blocks(
            draw=draw,
            items=summary_config["items"],
            layout=layout,
            colors=colors,
            fonts=fonts,
            separators=summary_config["separators"],
        )

        self._save_kneeboard_image(img)

    def gen_destination_reached_image(
        self,
        current_system,
        current_system_on_route,
        destination,
        jumps_remain,
        distance_remain,
        distance_traveled,
    ):
        img_width = 1000
        img_height = 445

        bg_color = (6, 8, 12)
        line_dim = (80, 40, 0)
        ed_orange = (255, 115, 0)
        ed_orange_soft = (220, 100, 0)
        ed_orange_dim = (150, 70, 0)
        ed_cyan = (89, 223, 227)
        color_on = (40, 210, 110)
        font_name = "arial.ttf"

        try:
            font_big = ImageFont.truetype(font_name, 28)
            font_medium = ImageFont.truetype(font_name, 22)
            font_small = ImageFont.truetype(font_name, 19)
        except IOError:
            font_big = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        img = Image.new("RGB", (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)

        title_text = f"NAVIGATION TO: {str(destination).upper()}"
        title_font = self._fit_font(
            draw, title_text, font_name,
            start_size=22, min_size=14, max_width=740
        )
        current_text = str(current_system).upper()
        current_font = self._fit_font(
            draw, current_text, font_name,
            start_size=38, min_size=20, max_width=900
        )
        next_text = "DESTINATION REACHED"
        next_font = self._fit_font(
            draw, next_text, font_name,
            start_size=38, min_size=20, max_width=680
        )

        draw.rectangle([(10, 10), (990, 435)], outline=ed_orange, width=2)
        draw.rectangle([(22, 22), (978, 423)], outline=ed_orange_dim, width=1)

        draw.line([(35, 68), (965, 68)], fill=ed_orange_dim, width=1)
        draw.line([(35, 160), (965, 160)], fill=line_dim, width=1)
        draw.line([(35, 315), (965, 315)], fill=line_dim, width=1)

        draw.text((40, 28), title_text, fill=ed_orange, font=title_font)

        route_dot_y = 30
        draw.ellipse([(820, route_dot_y), (846, route_dot_y + 26)], fill=color_on)
        draw.text((860, route_dot_y + 1), "REACHED", fill=ed_orange, font=font_medium)

        draw.text((45, 82), "CURRENT SYSTEM", fill=ed_orange_soft, font=font_small)
        draw.text((45, 108), current_text, fill=ed_cyan, font=current_font)
        draw.text((45, 205), next_text, fill=color_on, font=next_font)

        metric_label_y = 335
        metric_value_y = 362

        draw.text(
            (70, metric_label_y),
            "JUMPS LEFT",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (70, metric_value_y),
            f"{jumps_remain}",
            fill=ed_orange,
            font=font_big
        )
        draw.text(
            (370, metric_label_y),
            "DISTANCE REMAINING",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (370, metric_value_y),
            f"{distance_remain:n} LY",
            fill=ed_orange,
            font=font_big
        )
        draw.text(
            (690, metric_label_y),
            "TRAVELED",
            fill=ed_orange_dim,
            font=font_small
        )
        draw.text(
            (690, metric_value_y),
            f"{distance_traveled:n} LY",
            fill=ed_orange,
            font=font_big
        )

        draw.line([(320, 330), (320, 400)], fill=line_dim, width=1)
        draw.line([(645, 330), (645, 400)], fill=line_dim, width=1)

        draw.line([(22, 22), (52, 22)], fill=ed_orange, width=2)
        draw.line([(22, 22), (22, 52)], fill=ed_orange, width=2)
        draw.line([(948, 22), (978, 22)], fill=ed_orange, width=2)
        draw.line([(978, 22), (978, 52)], fill=ed_orange, width=2)
        draw.line([(22, 393), (22, 423)], fill=ed_orange, width=2)
        draw.line([(22, 423), (52, 423)], fill=ed_orange, width=2)
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
        self.stop_requested = False
        self.is_paused = False

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

        self.stop_requested = True
        self.monitoring_active = False
        self.is_paused = False

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self._update_transport_btn_states()

        if not preserve_arrived_state:
            self.reset_dashboard()

        self.log("Monitor stopped.")

    def handle_route_finished(self, system_name):
        self.last_next_waypoint_name = ""
        self.last_next_waypoint_coords = None

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
        star_pos = event_data.get("StarPos")

        if not system_name:
            self.log("Ignored event without StarSystem.")
            return

        if not isinstance(star_pos, (list, tuple)) or len(star_pos) != 3:
            self.log(f"Ignored event for {system_name}: missing or invalid StarPos.")
            return

        x, y, z = star_pos
        self.current_system_name = str(system_name)
        self.current_system_coords = (x, y, z)

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

        (
            next_stop,
            scoopable,
            has_neutron,
            jump_dist,
            jumps_remain,
            destination,
            distance_to_destination,
            on_route,
        ) = result

        next_waypoint_jumps = self.get_next_waypoint_jumps()

        self.last_next_waypoint_name = str(next_stop)

        # Use the current route index instead of searching by system name,
        # because duplicate names can appear in round-trip routes.
        next_route_entry = self.get_route_entry_by_index(self.route_index)
        if next_route_entry:
            self.last_next_waypoint_coords = (
                next_route_entry.get("x", 0.0),
                next_route_entry.get("y", 0.0),
                next_route_entry.get("z", 0.0),
            )
        else:
            self.last_next_waypoint_coords = None

        self.highlight_route_table(system_name, next_stop)
        self.update_dashboard(
            next_sys=next_stop,
            jumps_left=jumps_remain,
            final_tgt=destination,
            is_scoopable=scoopable,
            has_neutron=has_neutron,
        )

        self.log(
            f"Next: {next_stop} | Jumps to reach: {next_waypoint_jumps} | "
            f"Scoopable: {scoopable} | Neutron: {has_neutron} | Distance: {jump_dist} LY"
        )
        self.log(
            f"Progress: {jumps_remain} jumps remaining until "
            f"final destination: {destination}"
        )

        if self.copy_to_clipboard(next_stop):
            self.log(f"Copied next waypoint to clipboard: {next_stop}")

        try:
            if self.route_type.startswith("Exobiology"):
                exo_bodies = self.get_exobiology_display_bodies(system_name)
                exo_totals = self.get_exobiology_totals(system_name)

                self.gen_exobiology_image(
                    current_system=system_name,
                    current_system_on_route=on_route,
                    next_waypoint=next_stop,
                    bodies=exo_bodies,
                    totals=exo_totals,
                    next_waypoint_jumps=next_waypoint_jumps,
                    waypoints_left=jumps_remain,
                )

            elif self.route_type.startswith("Road to Riches"):
                r2r_bodies = self.get_r2r_display_bodies(system_name)
                r2r_totals = self.get_r2r_totals(system_name)

                self.gen_road_to_riches_image(
                    current_system=system_name,
                    current_system_on_route=on_route,
                    next_waypoint=next_stop,
                    bodies=r2r_bodies,
                    totals=r2r_totals,
                    value_mode=self.r2r_value_mode,
                    next_waypoint_jumps=next_waypoint_jumps,
                )

            else:
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
        journal_files = glob.glob(
            os.path.join(self.journal_dir, "Journal.*.log")
        )
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
            self.thread_safe_log(
                "Please verify your path or start Elite Dangerous."
            )
            self.ui_call(self.stop_monitoring)
            return

        start_event = self.find_current_system_on_startup(current_journal)
        if start_event:
            self.ui_call(self.jump_detected, start_event, True)
        else:
            self.thread_safe_log(
                "Could not find the current location in the log file."
            )

        self.thread_safe_log(
            f"Monitoring started on file: {os.path.basename(current_journal)}"
        )

        try:
            file = open(current_journal, "r", encoding="utf-8", errors="ignore")
            try:
                file.seek(0, os.SEEK_END)

                while not self.stop_requested:
                    latest_journal = self.get_latest_journal_file()
                    if latest_journal and latest_journal != current_journal:
                        self.thread_safe_log(
                            f"New log file detected: "
                            f"{os.path.basename(latest_journal)}"
                        )
                        current_journal = latest_journal
                        file.close()
                        file = open(
                            current_journal,
                            "r",
                            encoding="utf-8",
                            errors="ignore"
                        )
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
    app = EdSpanshApp(root)
    root.mainloop()
