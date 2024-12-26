#  OBS Smart Replays is an OBS script that allows more flexible replay buffer management:
#  set the clip name depending on the current window, set the file name format, etc.
#  Copyright (C) 2024 qvvonk
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.

import tkinter as tk
import time
import sys
import ctypes
import json
import traceback
import webbrowser
import os
import winsound
import subprocess
from tkinter import font as f
from enum import Enum
from threading import Lock
from threading import Thread
from pathlib import Path
from collections import deque
from urllib.request import urlopen
from datetime import datetime
from ctypes import wintypes

if __name__ != '__main__':
    import obspython as obs


# -------------------- ui.py --------------------
# This part of the script uses only when it is run as a main program, not imported by OBS.
#
# You can run this script to show notification:
# python smart_replays.py <Notification Title> <Notification Text> <Notification Color>
class ScrollingText:
    def __init__(self, canvas: tk.Canvas, text, visible_area_width, start_pos, font, speed=1):
        """
        Scrolling text widget.

        :param canvas: canvas.
        :param text: text.
        :param visible_area_width: width of the visible area of the text.
        :param start_pos: text's start position (most likely padding from left border).
        :param font: font.
        :param speed: scrolling speed.
        """

        self.canvas = canvas
        self.text = text
        self.area_width = visible_area_width
        self.start_pos = start_pos
        self.font = font
        self.speed = speed

        self.text_width = font.measure(text)
        self.text_height = font.metrics("ascent") + font.metrics("descent")
        self.text_id = self.canvas.create_text(0, round((self.canvas.winfo_height() - self.text_height) / 2),
                                               anchor='nw', text=self.text, font=self.font, fill="#ffffff")
        self.text_curr_pos = start_pos
        self.canvas.after(1000, self.update_scroll)  # type: ignore

    def update_scroll(self):
        if self.text_curr_pos + self.text_width > self.area_width:
            self.canvas.move(self.text_id, -self.speed, 0)
            self.text_curr_pos -= self.speed

            self.canvas.after(20, self.update_scroll)  # type: ignore


class NotificationWindow:
    def __init__(self, title: str, message: str, main_color: str = "#76B900"):
        self.title = title
        self.message = message
        self.back_bg = main_color
        self.main_bg = "#000000"

        self.root = tk.Tk()
        self.root.withdraw()
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True, "-alpha", 0.99)
        self.scr_w, self.scr_h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.wnd_w, self.wnd_h = round(self.scr_w / 6.4) * 2, round(self.scr_h / 12)
        self.main_frm_padding = round(self.wnd_w / 80)
        self.content_frm_padding_x, self.content_frm_padding_y = round(self.wnd_w / 80), round(self.wnd_h / 12)
        # window width is x2 bigger, cz half of the window is out of screen

        self.wnd_x = self.scr_w - round(self.wnd_w / 2)  # half of the window is out of screen.
        self.wnd_y = round(self.scr_h / 10)
        self.main_frm_x, self.main_frm_y = round(self.wnd_w / 2), 0
        self.main_frm_w, self.main_frm_h = round(self.wnd_w / 2) - self.main_frm_padding, self.wnd_h

        self.title_font_size = round(self.wnd_h / 5)
        self.text_font_size = round(self.wnd_h / 8)

        self.green_frame = tk.Frame(self.window, bg=self.back_bg, bd=0)
        self.green_frame.pack(fill=tk.BOTH, expand=True)

        self.main_frame = tk.Frame(self.window, bg=self.main_bg, bd=0, width=self.main_frm_w, height=self.main_frm_h)
        self.main_frame.pack_propagate(False)
        self.main_frame.place(x=self.main_frm_x, y=0)
        self.main_frame.lift()

        self.content_frame = tk.Frame(self.main_frame, bg=self.main_bg, bd=0)
        self.content_frame.pack(fill=tk.BOTH, anchor=tk.W, padx=self.content_frm_padding_x,
                                pady=self.content_frm_padding_y)

        self.title_label = tk.Label(self.content_frame, text=self.title,
                                    font=("Bahnschrift", self.title_font_size, "bold"), bg=self.main_bg, fg=self.back_bg)
        self.title_label.pack(anchor=tk.W)

        self.canvas = tk.Canvas(self.content_frame, bg=self.main_bg, highlightthickness=0)
        self.canvas.pack(expand=True)
        self.canvas.update()
        font = f.Font(family="Cascadia Mono", size=self.text_font_size)
        message = ScrollingText(self.canvas, message, self.main_frm_w, self.content_frm_padding_x * 2, font=font,
                                speed=3)

    def animate_window(self, current_x: int, target_x: int, speed: int = 5):
        speed = speed if current_x < target_x else -speed
        curr_x = current_x
        for x in range(current_x, target_x, speed):
            curr_x = x
            self.window.geometry(f"+{x}+{self.wnd_y}")
            self.window.update()

        if curr_x != target_x:
            self.window.geometry(f"+{target_x}+{self.wnd_y}")
            self.window.update()

    def animate_main_frame(self, current_x: int, target_x: int, speed: int = 5):
        speed = speed if current_x < target_x else -speed
        curr_x = current_x
        for x in range(current_x, target_x, speed):
            curr_x = x
            self.main_frame.place(x=x, y=self.main_frm_y)
            self.window.update()
            time.sleep(0.001)

        if curr_x != target_x:
            self.main_frame.place(x=target_x, y=self.main_frm_y)
            self.window.update()

    def show(self):
        self.window.geometry(f"{self.wnd_w}x{self.wnd_h}+{0}+{self.wnd_y}")
        self.animate_window(self.scr_w, self.wnd_x)
        time.sleep(0.1)
        self.animate_main_frame(self.main_frm_x, self.main_frm_padding)
        self.window.after(5000, self.close)  # type: ignore
        self.root.mainloop()

    def close(self):
        self.animate_main_frame(self.main_frm_padding, self.main_frm_x)
        time.sleep(0.1)
        self.animate_window(self.wnd_x, self.scr_w)
        self.window.destroy()
        self.root.destroy()


if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else "Test Title"
    m = sys.argv[2] if len(sys.argv) > 2 else "Test Message"
    color = sys.argv[3] if len(sys.argv) > 3 else "#76B900"
    NotificationWindow(t, m, color).show()
    sys.exit(0)


# -------------------- globals.py --------------------
VERSION = "1.0.2"
OBS_VERSION_STRING = obs.obs_get_version_string()
OBS_VERSION = (int(i) for i in OBS_VERSION_STRING.split('.'))
FORCE_MODE_LOCK = Lock()
FILENAME_PROHIBITED_CHARS = r'/\:"<>*?|%'
PATH_PROHIBITED_CHARS = r'"<>*?|%'
DEFAULT_FILENAME_FORMAT = "%NAME_%d.%m.%Y_%H-%M-%S"
DEFAULT_CUSTOM_NAMES = (
    {"value": "C:\\Windows\\explorer.exe > Desktop", "selected": False, "hidden": False},
    {"value": f"{sys.executable} > OBS", "selected": False, "hidden": False}
)
user32 = ctypes.windll.user32


class VARIABLES:
    update_available: bool = False
    clip_exe_history: deque[Path, ...] | None = None
    video_exe_history: dict[Path, int] | None = None  # {Path(path/to/executable): active_seconds_amount
    custom_names: dict[Path, str] = {}
    script_settings = None
    hotkey_ids: dict = {}
    force_mode = 0


class ConfigTypes(Enum):
    PROFILE = 0
    APP = 1
    USER = 2


class ClipNamingModes(Enum):
    CURRENT_PROCESS = 0
    MOST_RECORDED_PROCESS = 1
    CURRENT_SCENE = 2


class VideoNamingModes(Enum):
    CURRENT_PROCESS = 0
    MOST_RECORDED_PROCESS = 1
    CURRENT_SCENE = 2


class PropertiesNames:
    # Properties groups
    GR_CLIPS_PATHS = "clip_paths"
    GR_VIDEO_PATHS = "video_paths"
    GR_NOTIFICATIONS = "notifications"
    GR_POPUP = "popup"
    GR_CUSTOM_NAMES = "custom_names"
    GR_OTHER = "other"

    # Clips path settings
    PROP_CLIPS_BASE_PATH = "clips_base_path"
    TEXT_BASE_PATH_INFO = "base_path_info"
    PROP_CLIPS_FILENAME_CONDITION = "clips_filename_condition"
    TXT_CLIPS_HOTKEY_TIP = "clips_hotkey_tip"
    PROP_CLIPS_FILENAME_FORMAT = "clips_filename_format"
    TXT_CLIPS_FILENAME_FORMAT_ERR = "clips_filename_format_err"
    PROP_CLIPS_SAVE_TO_FOLDER = "clips_save_to_folder"

    # Videos path settings
    PROP_VIDEOS_FILENAME_CONDITION = "videos_filename_condition"
    TXT_VIDEOS_HOTKEY_TIP = "videos_hotkey_tip"
    PROP_VIDEOS_FILENAME_FORMAT = "videos_filename_format"
    PROP_VIDEOS_SAVE_TO_FOLDER = "videos_save_to_folder"

    # Sound notification settings
    PROP_NOTIFICATION_ON_SUCCESS = "notification_on_success"
    PROP_NOTIFICATION_ON_SUCCESS_PATH = "notification_on_success_file"
    PROP_NOTIFICATION_ON_FAILURE = "notification_on_failure"
    PROP_NOTIFICATION_ON_FAILURE_PATH = "notification_on_failure_file"

    # Popup notification settings
    PROP_POPUP_ON_SUCCESS = "prop_popup_on_success"
    PROP_POPUP_ON_FAILURE = "prop_popup_on_failure"

    # Custom names settings
    PROP_CUSTOM_NAMES_LIST = "custom_names_list"
    TXT_CUSTOM_NAME_DESC = "custom_names_desc"

    # Custom names parsing error texts
    TXT_CUSTOM_NAMES_PATH_EXISTS = "custom_names_path_exists_err"
    TXT_CUSTOM_NAMES_INVALID_FORMAT = "custom_names_invalid_format_err"
    TXT_CUSTOM_NAMES_INVALID_CHARACTERS = "custom_names_invalid_characters_err"

    # Export / Import custom names section
    PROP_CUSTOM_NAMES_EXPORT_PATH = "custom_names_export_path"
    BTN_CUSTOM_NAMES_EXPORT = "btn_custom_names_export"
    PROP_CUSTOM_NAMES_IMPORT_PATH = "custom_names_import_path"
    BTN_CUSTOM_NAMES_IMPORT = "btn_custom_names_import"

    # Other section
    PROP_RESTART_BUFFER = "restart_buffer"
    PROP_RESTART_BUFFER_LOOP = "restart_buffer_loop"
    TXT_RESTART_BUFFER_LOOP = "txt_restart_buffer_loop"

    # Hotkeys
    HK_SAVE_BUFFER_MODE_1 = "save_buffer_force_mode_1"
    HK_SAVE_BUFFER_MODE_2 = "save_buffer_force_mode_2"
    HK_SAVE_BUFFER_MODE_3 = "save_buffer_force_mode_3"
    HK_SAVE_VIDEO_MODE_1 = "save_video_force_mode_1"
    HK_SAVE_VIDEO_MODE_2 = "save_video_force_mode_2"
    HK_SAVE_VIDEO_MODE_3 = "save_video_force_mode_3"

PN = PropertiesNames


# -------------------- exceptions.py --------------------
class CustomNameParsingError(Exception):
    """
    Base exception for all custom names related exceptions.
    """
    def __init__(self, index):
        """
        :param index: custom name index.
        """
        super().__init__(Exception)
        self.index = index


class CustomNamePathAlreadyExists(CustomNameParsingError):
    """
    Exception raised when a custom name is already exists.
    """
    def __init__(self, index):
        """
        :param index: custom name index.
        """
        super().__init__(index)


class CustomNameInvalidCharacters(CustomNameParsingError):
    """
    Exception raised when a custom name has invalid characters.
    """
    def __init__(self, index):
        """
        :param index: custom name index.
        """
        super().__init__(index)


class CustomNameInvalidFormat(CustomNameParsingError):
    """
    Exception raised when a custom name is invalid format.
    """
    def __init__(self, index):
        """
        :param index: custom name index.
        """
        super().__init__(index)


# -------------------- updates_check.py --------------------
def get_latest_release_tag() -> dict | None:
    url = "https://api.github.com/repos/qvvonk/smart_replays/releases/latest"

    try:
        with urlopen(url, timeout=2) as response:
            if response.status == 200:
                data = json.load(response)
                return data.get('tag_name')
    # except:
    #         _print(f"Failed to check updates: bad response status code: {e.code}")
    except:
        _print(f"Failed to check updates.")
        _print(traceback.format_exc())

    return None


def check_updates(current_version):
    latest_version = get_latest_release_tag()
    _print(latest_version)
    if latest_version and f'v{current_version}' != latest_version:
        return True
    return False


# -------------------- properties.py --------------------
def setup_clip_paths_settings(group_obj):
    # ----- Clips base path -----
    base_path_prop = obs.obs_properties_add_path(
        props=group_obj,
        name=PN.PROP_CLIPS_BASE_PATH,
        description="Base path for clips",
        type=obs.OBS_PATH_DIRECTORY,
        filter=None,
        default_path="C:\\"
    )
    t = obs.obs_properties_add_text(
        props=group_obj,
        name=PN.TEXT_BASE_PATH_INFO,
        description="The path must be on the same disk as the path for OBS records "
                    "(File -> Settings -> Output -> Recording -> Recording Path).\n"
                    "Otherwise, the script will not be able to move the clip to the correct folder.",
        type=obs.OBS_TEXT_INFO
    )
    obs.obs_property_text_set_info_type(t, obs.OBS_TEXT_INFO_WARNING)

    # ----- Clips name condition -----
    filename_condition = obs.obs_properties_add_list(
        props=group_obj,
        name=PN.PROP_CLIPS_FILENAME_CONDITION,
        description="Clip name depends on",
        type=obs.OBS_COMBO_TYPE_RADIO,
        format=obs.OBS_COMBO_FORMAT_INT
    )
    obs.obs_property_list_add_int(
        p=filename_condition,
        name="the name of an active app (.exe file name) at the moment of clip saving",
        val=1
    )
    obs.obs_property_list_add_int(
        p=filename_condition,
        name="the name of an app (.exe file name) that was active most of the time during the clip recording",
        val=2
    )
    obs.obs_property_list_add_int(
        p=filename_condition,
        name="the name of the current scene",
        val=3
    )

    t = obs.obs_properties_add_text(
        props=group_obj,
        name=PN.TXT_CLIPS_HOTKEY_TIP,
        description="You can set up hotkeys for each mode in File -> Settings -> Hotkeys",
        type=obs.OBS_TEXT_INFO
    )
    obs.obs_property_text_set_info_type(t, obs.OBS_TEXT_INFO_WARNING)

    # ----- Clip file name format -----
    filename_format_prop = obs.obs_properties_add_text(
        props=group_obj,
        name=PN.PROP_CLIPS_FILENAME_FORMAT,
        description="File name format",
        type=obs.OBS_TEXT_DEFAULT
    )
    obs.obs_property_set_long_description(
        filename_format_prop,
        """<table>
<tr><th align='left'>%NAME</th><td> - name of the clip.</td></tr>

<tr><th align='left'>%a</th><td> - Weekday as locale’s abbreviated name.<br/>
Example: Sun, Mon, …, Sat (en_US); So, Mo, …, Sa (de_DE)</td></tr>

<tr><th align='left'>%A</th><td> - Weekday as locale’s full name.<br/>
Example: Sunday, Monday, …, Saturday (en_US); Sonntag, Montag, …, Samstag (de_DE)</td></tr>

<tr><th align='left'>%w</th><td> - Weekday as a decimal number, where 0 is Sunday and 6 is Saturday.<br/>
Example: 0, 1, …, 6</td></tr>

<tr><th align='left'>%d</th><td> - Day of the month as a zero-padded decimal number.<br/>
Example: 01, 02, …, 31</td></tr>

<tr><th align='left'>%b</th><td> - Month as locale’s abbreviated name.<br/>
Example: Jan, Feb, …, Dec (en_US); Jan, Feb, …, Dez (de_DE)</td></tr>

<tr><th align='left'>%B</th><td> - Month as locale’s full name.<br/>
Example: January, February, …, December (en_US); Januar, Februar, …, Dezember (de_DE)</td></tr>

<tr><th align='left'>%m</th><td> - Month as a zero-padded decimal number.<br/>
Example: 01, 02, …, 12</td></tr>

<tr><th align='left'>%y</th><td> - Year without century as a zero-padded decimal number.<br/>
Example: 00, 01, …, 99</td></tr>

<tr><th align='left'>%Y</th><td> - Year with century as a decimal number.<br/>
Example: 0001, 0002, …, 2013, 2014, …, 9998, 9999</td></tr>

<tr><th align='left'>%H</th><td> - Hour (24-hour clock) as a zero-padded decimal number.<br/>
Example: 00, 01, …, 23</td></tr>

<tr><th align='left'>%I</th><td> - Hour (12-hour clock) as a zero-padded decimal number.<br/>
Example: 01, 02, …, 12</td></tr>

<tr><th align='left'>%p</th><td> - Locale’s equivalent of either AM or PM.<br/>
Example: AM, PM (en_US); am, pm (de_DE)</td></tr>

<tr><th align='left'>%M</th><td> - Minute as a zero-padded decimal number.<br/>
Example: 00, 01, …, 59</td></tr>

<tr><th align='left'>%S</th><td> - Second as a zero-padded decimal number.<br/>
Example: 00, 01, …, 59</td></tr>

<tr><th align='left'>%f</th><td> - Microsecond as a decimal number, zero-padded to 6 digits.<br/>
Example: 000000, 000001, …, 999999</td></tr>

<tr><th align='left'>%z</th><td> - UTC offset in the form ±HHMM[SS[.ffffff]]<br/>
Example: +0000, -0400, +1030, +063415, -030712.345216</td></tr>

<tr><th align='left'>%Z</th><td> - Time zone name<br/>
Example: UTC, GMT</td></tr>

<tr><th align='left'>%j</th><td> - Day of the year as a zero-padded decimal number.<br/>
Example: 001, 002, …, 366</td></tr>

<tr><th align='left'>%U</th><td> - Week number of the year (Sunday as the first day of the week) as a zero-padded decimal number. All days in a new year preceding the first Sunday are considered to be in week 0.<br/>
Example: 00, 01, …, 53</td></tr>

<tr><th align='left'>%W</th><td> - Week number of the year (Monday as the first day of the week) as a zero-padded decimal number. All days in a new year preceding the first Monday are considered to be in week 0.<br/>
Example: 00, 01, …, 53</td></tr>

<tr><th align='left'>%%</th><td> - A literal '%' character.</td></tr>
</table>""")

    t = obs.obs_properties_add_text(
        props=group_obj,
        name=PN.TXT_CLIPS_FILENAME_FORMAT_ERR,
        description="<font color=\"red\"><pre> Invalid format!</pre></font>",
        type=obs.OBS_TEXT_INFO
    )
    obs.obs_property_set_visible(t, False)

    # ----- Save to folders checkbox -----
    obs.obs_properties_add_bool(
        props=group_obj,
        name=PN.PROP_CLIPS_SAVE_TO_FOLDER,
        description="Create different folders for different clip names",
    )

    # ----- Callbacks -----
    obs.obs_property_set_modified_callback(base_path_prop, check_base_path_callback)
    obs.obs_property_set_modified_callback(filename_format_prop, check_filename_template_callback)


def script_properties():
    p = obs.obs_properties_create()  # main properties object
    clip_path_gr = obs.obs_properties_create()
    notification_props = obs.obs_properties_create()
    popup_props = obs.obs_properties_create()
    custom_names_props = obs.obs_properties_create()
    other_props = obs.obs_properties_create()

    # ----- Ungrouped properties -----
    # Updates text
    t = obs.obs_properties_add_text(p, 'check_updates', 'New update available', obs.OBS_TEXT_INFO)
    obs.obs_property_set_visible(t, VARIABLES.update_available)

    # Like btn
    obs.obs_properties_add_button(
        p,
        "like_btn",
        "🌟 Like this script? Star it! 🌟",
        open_github_callback
    )

    # ----- Groups -----
    obs.obs_properties_add_group(p, PN.GR_CLIPS_PATHS, "Clip path settings", obs.OBS_PROPERTY_GROUP, clip_path_gr)
    obs.obs_properties_add_group(p, PN.GR_NOTIFICATIONS, "Sound notifications", obs.OBS_GROUP_CHECKABLE, notification_props)
    obs.obs_properties_add_group(p, PN.GR_POPUP, "Popup notifications", obs.OBS_GROUP_CHECKABLE, popup_props)
    obs.obs_properties_add_group(p, PN.GR_CUSTOM_NAMES, "Custom names", obs.OBS_GROUP_NORMAL, custom_names_props)
    obs.obs_properties_add_group(p, PN.GR_OTHER, "Other", obs.OBS_GROUP_NORMAL, other_props)

    # ------ Setup properties ------
    setup_clip_paths_settings(clip_path_gr)

    # ------ Notification Settings ------
    notification_success_prop = obs.obs_properties_add_bool(
        props=notification_props,
        name=PN.PROP_NOTIFICATION_ON_SUCCESS,
        description="On success"
    )
    obs.obs_properties_add_path(
        props=notification_props,
        name=PN.PROP_NOTIFICATION_ON_SUCCESS_PATH,
        description="",
        type=obs.OBS_PATH_FILE,
        filter=None,
        default_path="C:\\"
    )

    notification_failure_prop = obs.obs_properties_add_bool(
        props=notification_props,
        name=PN.PROP_NOTIFICATION_ON_FAILURE,
        description="On failure"
    )
    obs.obs_properties_add_path(
        props=notification_props,
        name=PN.PROP_NOTIFICATION_ON_FAILURE_PATH,
        description="",
        type=obs.OBS_PATH_FILE,
        filter=None,
        default_path="C:\\"
    )

    update_notifications_menu_callback(p, None, VARIABLES.script_settings)

    # ------ Popup notifications ------
    obs.obs_properties_add_bool(
        props=popup_props,
        name=PN.PROP_POPUP_ON_SUCCESS,
        description="On success"
    )

    obs.obs_properties_add_bool(
        props=popup_props,
        name=PN.PROP_POPUP_ON_FAILURE,
        description="On failure"
    )
    # ------ Custom names settings ------
    obs.obs_properties_add_text(
        props=custom_names_props,
        name=PN.TXT_CUSTOM_NAME_DESC,
        description="Since the executable name doesn't always match the name of the application/game "
                    "(e.g. the game is called Deadlock, but the executable is project8.exe), "
                    "you can set custom names for clips based on the name of the executable / folder "
                    "where the executable is located.",
        type=obs.OBS_TEXT_INFO
    )

    err_text_1 = obs.obs_properties_add_text(
        props=custom_names_props,
        name=PN.TXT_CUSTOM_NAMES_INVALID_CHARACTERS,
        description="""
<div style="font-size: 14px">
<span style="color: red">Invalid path or clip name value.<br></span>
<span style="color: orange">Clip name cannot contain <code style="color: cyan">&lt; &gt; / \\ | * ? : " %</code> characters.<br>
Path cannot contain <code style="color: cyan">&lt; &gt; | * ? " %</code> characters.</span>
</div>
""",
        type=obs.OBS_TEXT_INFO
    )

    err_text_2 = obs.obs_properties_add_text(
        props=custom_names_props,
        name=PN.TXT_CUSTOM_NAMES_PATH_EXISTS,
        description="""<div style="font-size: 14px; color: red">This path has already been added to the list.</div>""",
        type=obs.OBS_TEXT_INFO
    )

    err_text_3 = obs.obs_properties_add_text(
        props=custom_names_props,
        name=PN.TXT_CUSTOM_NAMES_INVALID_FORMAT,
        description="""
<div style="font-size: 14px">
<span style="color: red">Invalid format.<br></span>
<span style="color: orange">Required format: DISK:\\path\\to\\folder\\or\\executable > ClipName<br></span>
<span style="color: lightgreen">Example: C:\\Program Files\\Minecraft > Minecraft</span>
</div>""",
        type=obs.OBS_TEXT_INFO
    )

    obs.obs_property_set_visible(err_text_1, False)
    obs.obs_property_set_visible(err_text_2, False)
    obs.obs_property_set_visible(err_text_3, False)

    custom_names_list = obs.obs_properties_add_editable_list(
        props=custom_names_props,
        name=PN.PROP_CUSTOM_NAMES_LIST,
        description="",
        type=obs.OBS_EDITABLE_LIST_TYPE_STRINGS,
        filter=None,
        default_path=None
    )

    t = obs.obs_properties_add_text(
        props=custom_names_props,
        name="temp",
        description="Format:  DISK:\\path\\to\\folder\\or\\executable > ClipName\n"
                    f"Example: {sys.executable} > OBS",
        type=obs.OBS_TEXT_INFO
    )
    obs.obs_property_text_set_info_type(t, obs.OBS_TEXT_INFO_WARNING)

    obs.obs_properties_add_path(
        props=custom_names_props,
        name=PN.PROP_CUSTOM_NAMES_IMPORT_PATH,
        description="",
        type=obs.OBS_PATH_FILE,
        filter=None,
        default_path="C:\\"
    )

    obs.obs_properties_add_button(
        custom_names_props,
        PN.BTN_CUSTOM_NAMES_IMPORT,
        "Import custom names",
        import_custom_names_from_json_callback,
    )

    obs.obs_properties_add_path(
        props=custom_names_props,
        name=PN.PROP_CUSTOM_NAMES_EXPORT_PATH,
        description="",
        type=obs.OBS_PATH_DIRECTORY,
        filter=None,
        default_path="C:\\"
    )

    obs.obs_properties_add_button(
        custom_names_props,
        PN.BTN_CUSTOM_NAMES_EXPORT,
        "Export custom names",
        export_custom_names_to_json_callback,
    )

    # ------ Other ------
    obs.obs_properties_add_text(
        props=other_props,
        name=PN.TXT_RESTART_BUFFER_LOOP,
        description="""If you don't restart replay buffering for a long time, saving clips can take a very long time and other bugs can happen (thanks, OBS).
It is recommended to keep the value within 1-2 hours (3600-7200 seconds).
Before a scheduled restart of replay buffering, script looks at the max clip length in the OBS settings and checks if keyboard or mouse input was made at that time. If input was made, the restart will be delayed for the time of max clip length, otherwise it restarts replay baffering.
If you want to disable scheduled restart of replay buffering, set the value to 0.
""",
        type=obs.OBS_TEXT_INFO
    )

    obs.obs_properties_add_int(
        props=other_props,
        name=PN.PROP_RESTART_BUFFER_LOOP,
        description="Restart every (s)",
        min=0, max=7200,
        step=10
    )

    obs.obs_properties_add_bool(
        props=other_props,
        name=PN.PROP_RESTART_BUFFER,
        description="Restart replay buffer after clip saving"
    )

    obs.obs_property_set_modified_callback(notification_success_prop, update_notifications_menu_callback)
    obs.obs_property_set_modified_callback(notification_failure_prop, update_notifications_menu_callback)
    obs.obs_property_set_modified_callback(custom_names_list, update_custom_names_callback)
    return p


# -------------------- properties_callbacks.py --------------------
# All UI callbacks have the same parameters:
# p: properties object (controls the properties UI)
# prop: property that changed
# data: script settings
# Usually I don't use `data`, cuz we have script_settings global variable.
def open_github_callback(*args):
    webbrowser.open("https://github.com/qvvonk/smart_replays", 1)


def update_custom_names_callback(p, prop, data):
    """
    Checks the list of custom names and updates custom names menu (shows / hides error texts).
    """
    invalid_format_err_text = obs.obs_properties_get(p, PN.TXT_CUSTOM_NAMES_INVALID_FORMAT)
    invalid_chars_err_text = obs.obs_properties_get(p, PN.TXT_CUSTOM_NAMES_INVALID_CHARACTERS)
    path_exists_err_text = obs.obs_properties_get(p, PN.TXT_CUSTOM_NAMES_PATH_EXISTS)

    settings_json: dict = json.loads(obs.obs_data_get_json(data))
    if not settings_json:
        return False

    try:
        load_custom_names(settings_json)
        obs.obs_property_set_visible(invalid_format_err_text, False)
        obs.obs_property_set_visible(invalid_chars_err_text, False)
        obs.obs_property_set_visible(path_exists_err_text, False)
        return True

    except CustomNameInvalidCharacters as e:
        obs.obs_property_set_visible(invalid_format_err_text, False)
        obs.obs_property_set_visible(invalid_chars_err_text, True)
        obs.obs_property_set_visible(path_exists_err_text, False)
        index = e.index

    except CustomNameInvalidFormat as e:
        obs.obs_property_set_visible(invalid_format_err_text, True)
        obs.obs_property_set_visible(invalid_chars_err_text, False)
        obs.obs_property_set_visible(path_exists_err_text, False)
        index = e.index

    except CustomNamePathAlreadyExists as e:
        obs.obs_property_set_visible(invalid_format_err_text, False)
        obs.obs_property_set_visible(invalid_chars_err_text, False)
        obs.obs_property_set_visible(path_exists_err_text, True)
        index = e.index

    except CustomNameParsingError as e:
        index = e.index

    # If error in parsing
    settings_json[PN.PROP_CUSTOM_NAMES_LIST].pop(index)
    new_custom_names_array = obs.obs_data_array_create()

    for index, custom_name in enumerate(settings_json[PN.PROP_CUSTOM_NAMES_LIST]):
        custom_name_data = obs.obs_data_create_from_json(json.dumps(custom_name))
        obs.obs_data_array_insert(new_custom_names_array, index, custom_name_data)

    obs.obs_data_set_array(data, PN.PROP_CUSTOM_NAMES_LIST, new_custom_names_array)
    obs.obs_data_array_release(new_custom_names_array)
    return True


def check_filename_template_callback(p, prop, data):
    """
    Checks filename template.
    If template is invalid, shows warning.
    """
    error_text = obs.obs_properties_get(p, PN.TXT_CLIPS_FILENAME_FORMAT_ERR)
    dt = datetime.now()

    try:
        format_filename("clipname", dt, raise_exception=True)
        obs.obs_property_set_visible(error_text, False)
    except:
        obs.obs_property_set_visible(error_text, True)
    return True


def update_notifications_menu_callback(p, prop, data):
    """
    Updates notifications settings menu.
    If notification is enabled, shows path widget.
    """
    success_path_prop = obs.obs_properties_get(p, PN.PROP_NOTIFICATION_ON_SUCCESS_PATH)
    failure_path_prop = obs.obs_properties_get(p, PN.PROP_NOTIFICATION_ON_FAILURE_PATH)

    on_success = obs.obs_data_get_bool(data, PN.PROP_NOTIFICATION_ON_SUCCESS)
    on_failure = obs.obs_data_get_bool(data, PN.PROP_NOTIFICATION_ON_FAILURE)

    obs.obs_property_set_visible(success_path_prop, on_success)
    obs.obs_property_set_visible(failure_path_prop, on_failure)
    return True


def check_base_path_callback(p, prop, data):
    """
    Checks base path is in the same disk as OBS recordings path.
    If it's not - sets OBS records path as base path for clips and shows warning.
    """
    warn_text = obs.obs_properties_get(p, PN.TEXT_BASE_PATH_INFO)

    obs_records_path = Path(get_base_path(from_obs_config=True))
    curr_path = Path(obs.obs_data_get_string(data, PN.PROP_CLIPS_BASE_PATH))

    if not len(curr_path.parts) or obs_records_path.parts[0] == curr_path.parts[0]:
        obs.obs_property_text_set_info_type(warn_text, obs.OBS_TEXT_INFO_WARNING)
    else:
        obs.obs_property_text_set_info_type(warn_text, obs.OBS_TEXT_INFO_ERROR)
        obs.obs_data_set_string(data, PN.PROP_CLIPS_BASE_PATH, str(obs_records_path))
    return True


def import_custom_names_from_json_callback(*args):
    """
    Imports custom names from JSON file.
    """
    path = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_CUSTOM_NAMES_IMPORT_PATH)
    if not path or not os.path.exists(path) or not os.path.isfile(path):
        return False

    with open(path, "r") as f:
        data = f.read()

    try:
        data = json.loads(data)
    except:
        return False

    arr = obs.obs_data_array_create()
    for index, i in enumerate(data):
        item = obs.obs_data_create_from_json(json.dumps(i))
        obs.obs_data_array_insert(arr, index, item)

    obs.obs_data_set_array(VARIABLES.script_settings, PN.PROP_CUSTOM_NAMES_LIST, arr)
    return True


def export_custom_names_to_json_callback(*args):
    """
    Exports custom names to JSON file.
    """
    path = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_CUSTOM_NAMES_EXPORT_PATH)
    if not path or not os.path.exists(path) or not os.path.isdir(path):
        return False

    custom_names_dict = json.loads(obs.obs_data_get_last_json(VARIABLES.script_settings))
    custom_names_dict = custom_names_dict.get(PN.PROP_CUSTOM_NAMES_LIST) or DEFAULT_CUSTOM_NAMES

    with open(os.path.join(path, "obs_smart_replays_custom_names.json"), "w") as f:
        f.write(json.dumps(custom_names_dict, ensure_ascii=False))


# -------------------- tech.py --------------------
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT),
                ("dwTime", wintypes.DWORD)]


def _print(*values, sep: str | None = None, end: str | None = None, file=None, flush: bool = False):
    time_ = datetime.now()
    str_time = time_.strftime(f"%d.%m.%Y %H:%M:%S")
    prefix = f"[{str_time}]"
    print(prefix, *values, sep=sep, end=end, file=file, flush=flush)


def get_active_window_pid() -> int | None:
    """
    Gets process ID of the current active window.
    """
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_executable_path(pid) -> str:
    """
    Gets path of process's executable.

    :param pid: process ID.
    :return: Executable path.
    """
    process_handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
    # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ

    if not process_handle:
        raise OSError(f"Process {pid} does not exist.")

    filename_buffer = ctypes.create_unicode_buffer(260)  # Windows path is 260 characters max.
    result = ctypes.windll.psapi.GetModuleFileNameExW(process_handle, None, filename_buffer, 260)
    ctypes.windll.kernel32.CloseHandle(process_handle)
    if result:
        return filename_buffer.value
    else:
        raise RuntimeError(f"Cannot get executable path for process {pid}.")


def play_sound(path: str):
    """
    Plays sound using windows engine.

    :param path: path to sound (.wav)
    """
    try:
        winsound.PlaySound(path, winsound.SND_ASYNC)
    except:
        pass


def get_time_since_last_input() -> float:
    """
    Gets the time (in seconds) since the last mouse or keyboard input.
    """
    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info)):
        current_time = ctypes.windll.kernel32.GetTickCount()
        idle_time_ms = current_time - last_input_info.dwTime
        return idle_time_ms / 1000.0
    else:
        return 0


# -------------------- obs_related.py --------------------
def get_obs_config(section_name: str | None = None,
                   param_name: str | None = None,
                   value_type: type[str, int, bool, float] = str,
                   config_type: ConfigTypes = ConfigTypes.PROFILE):
    """
    Gets a value from OBS config.
    If the value is not set, it will use the default value. If there is no default value, it will return NULL.
    If section_name or param_name are not specified, returns OBS config obj.

    :param section_name: Section name. If not specified, returns the OBS config.
    :param param_name: Parameter name. If not specified, returns the OBS config.
    :param value_type: Type of value (str, int, bool, float).
    :param config_type: Which config search in? (global / profile / user (obs v31 or higher)
    """
    if config_type is ConfigTypes.PROFILE:
        cfg = obs.obs_frontend_get_profile_config()
    elif config_type is ConfigTypes.APP:
        cfg = obs.obs_frontend_get_global_config()
    else:
        if OBS_VERSION[0] < 31:
            cfg = obs.obs_frontend_get_global_config()
        else:
            cfg = obs.obs_frontend_get_user_config()


    if not section_name or not param_name:
        return cfg

    functions = {
        str: obs.config_get_string,
        int: obs.config_get_int,
        bool: obs.config_get_bool,
        float: obs.config_get_double
    }

    if value_type not in functions.keys():
        raise ValueError("Unsupported type.")

    return functions[value_type](cfg, section_name, param_name)


def get_last_replay_file_name() -> str:
    """
    Returns the last saved buffer file name.
    """
    replay_buffer = obs.obs_frontend_get_replay_buffer_output()
    cd = obs.calldata_create()
    proc_handler = obs.obs_output_get_proc_handler(replay_buffer)
    obs.proc_handler_call(proc_handler, 'get_last_replay', cd)
    path = obs.calldata_string(cd, 'path')
    obs.calldata_destroy(cd)
    obs.obs_output_release(replay_buffer)
    return path


def get_current_scene_name() -> str:
    """
    Returns the current OBS scene name.
    """
    current_scene = obs.obs_frontend_get_current_scene()
    name = obs.obs_source_get_name(current_scene)
    obs.obs_source_release(current_scene)
    return name


def get_base_path(from_obs_config: bool = False) -> str:
    """
    Returns current base path for clips.

    :param from_obs_config: If True, returns base path from OBS config, otherwise - from script config.
        It's True only on script launch and only if there is no value in script config.
    """
    if not from_obs_config:
        script_path = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_CLIPS_BASE_PATH)
        # If PN.PROP_CLIPS_BASE_PATH is not saved in the script config, then it has a default value,
        # which is the value from the OBS config.
        if script_path:
            return script_path

    config_mode = get_obs_config("Output", "Mode")
    if config_mode == "Simple":
        return get_obs_config("SimpleOutput", "FilePath")
    else:
        return get_obs_config("AdvOut", "RecFilePath")


def get_replay_buffer_max_time() -> int:
    """
    Returns replay buffer max time from OBS config (in seconds).
    """
    config_mode = get_obs_config("Output", "Mode")
    if config_mode == "Simple":
        return get_obs_config("SimpleOutput", "RecRBTime", value_type=int)
    else:
        return get_obs_config("AdvOut", "RecRBTime", value_type=int)


def restart_replay_buffering():
    """
    Restart replay buffering, obviously -_-
    """
    _print("Stopping replay buffering...")
    replay_output = obs.obs_frontend_get_replay_buffer_output()
    obs.obs_frontend_replay_buffer_stop()

    while not obs.obs_output_can_begin_data_capture(replay_output, 0):
        time.sleep(0.1)
    _print("Replay buffering stopped.")
    _print("Starting replay buffering...")
    obs.obs_frontend_replay_buffer_start()
    _print("Replay buffering started.")


# -------------------- script_helpers.py --------------------
def notify(success: bool, clip_path: str):
    """
    Plays and shows success / failure notification if it's enabled in notifications settings.
    """
    sound_notifications = obs.obs_data_get_bool(VARIABLES.script_settings, PN.GR_NOTIFICATIONS)
    popup_notifications = obs.obs_data_get_bool(VARIABLES.script_settings, PN.GR_POPUP)
    python_exe = os.path.join(get_obs_config("Python", "Path64bit", str, ConfigTypes.APP), "pythonw.exe")

    if success:
        if sound_notifications and obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_NOTIFICATION_ON_SUCCESS):
            path = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_NOTIFICATION_ON_SUCCESS_PATH)
            play_sound(path)

        if popup_notifications and obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_POPUP_ON_SUCCESS):
            subprocess.Popen([python_exe, __file__, "Clip saved", f"Clip saved to {clip_path}"])
    else:
        if sound_notifications and obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_NOTIFICATION_ON_FAILURE):
            path = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_NOTIFICATION_ON_FAILURE_PATH)
            play_sound(path)

        if popup_notifications and obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_POPUP_ON_FAILURE):
            subprocess.Popen([python_exe, __file__, "Clip not saved", f"More in the logs.", "#C00000"])


def load_custom_names(script_settings_dict: dict):
    """
    Loads custom names to global custom_name variable.
    Raises exception if path or name are invalid.

    :param script_settings_dict: Script settings as dict.
    """
    _print("Loading custom names...")

    new_custom_names = {}
    custom_names_list = script_settings_dict.get(PN.PROP_CUSTOM_NAMES_LIST)
    if custom_names_list is None:
        custom_names_list = DEFAULT_CUSTOM_NAMES

    for index, i in enumerate(custom_names_list):
        value = i.get("value")
        spl = value.split(">", 1)
        try:
            path, name = spl[0].strip(), spl[1].strip()
        except IndexError:
            raise CustomNameInvalidFormat(index)

        path = os.path.expandvars(path)
        if any(i in path for i in PATH_PROHIBITED_CHARS) or any(i in name for i in FILENAME_PROHIBITED_CHARS):
            raise CustomNameInvalidCharacters(index)

        if Path(path) in new_custom_names.keys():
            raise CustomNamePathAlreadyExists(index)

        new_custom_names[Path(path)] = name

    VARIABLES.custom_names = new_custom_names
    _print(f"{len(VARIABLES.custom_names)} custom names are loaded.")


# -------------------- clipname_gen.py --------------------
def gen_clip_base_name(mode: int) -> str:
    """
    Generates clip base name based on clip naming mode.
    It's NOT generates new path for clip.

    :param mode: Clip naming mode. If 0 - gets mode from script config.
    """
    _print("Generating clip base name...")
    mode = obs.obs_data_get_int(VARIABLES.script_settings, PN.PROP_CLIPS_FILENAME_CONDITION) if not mode else mode

    if mode in [1, 2]:
        if mode == 1:
            _print("Clip file name depends on the name of an active app (.exe file name) at the moment of clip saving.")
            pid = get_active_window_pid()
            executable_path = get_executable_path(pid)
            executable_path_obj = Path(executable_path)
            _print(f"Current active window process ID: {pid}")
            _print(f"Current active window executable: {executable_path}")

        else:  # if mode == 2
            _print("Clip file name depends on the name of an app (.exe file name) "
                   "that was active most of the time during the clip recording.")
            if VARIABLES.clip_exe_history:
                executable_path = max(VARIABLES.clip_exe_history, key=VARIABLES.clip_exe_history.count)
            else:
                executable_path = get_executable_path(get_active_window_pid())
            executable_path_obj = Path(executable_path)


        if custom_name := get_name_from_custom_names(executable_path):
            return custom_name
        else:
            _print(f"{executable_path} or its parents weren't found in custom names list. "
                   f"Assigning the name of the executable: {executable_path_obj.stem}")
            return executable_path_obj.stem

    elif mode == 3:
        _print("Clip filename depends on the name of the current scene name.")
        return get_current_scene_name()


def get_name_from_custom_names(executable_path: str) -> str | None:
    """
    Searches for the passed path or its parents in the custom names list.
    Returns None if nothing wasn't found.

    :param executable_path: Path to executable.
    """
    _print(f"Looking for {executable_path} in custom names ...")

    executable_path = Path(executable_path)
    last_result = None
    for i in VARIABLES.custom_names:
        if last_result is None and any([executable_path == i, i in executable_path.parents]):
            last_result = i
            continue

        if last_result in i.parents:
            last_result = i

    if last_result is None:
        _print(f"{executable_path} or its parents are not in custom names.")
        return None

    _print(f"{executable_path} or its parent was found on the list: {last_result} > {VARIABLES.custom_names[last_result]}.")
    return VARIABLES.custom_names[last_result]


def format_filename(clip_name: str, dt: datetime | None = None,
                    force_default_template: bool = False, raise_exception: bool = False) -> str:
    """
    Formats the clip file name based on the template.
    If the template is invalid, uses the default template.

    :param clip_name: clip name.
    :param dt: datetime obj.
    :param force_default_template: use the default template even if the template in the settings is valid.
        This param uses only in this function (in recursive call) and only if something wrong with users template.
    :param raise_exception: raise exception if template is invalid instead of using default template.
        This param uses when this function called from properties callback to check template imputed by user.
    """
    if dt is None:
        dt = datetime.now()

    template = obs.obs_data_get_string(VARIABLES.script_settings, PN.PROP_CLIPS_FILENAME_FORMAT)

    if not template:
        if raise_exception:
            raise ValueError
        template = DEFAULT_FILENAME_FORMAT

    if force_default_template:
        template = DEFAULT_FILENAME_FORMAT

    filename = template.replace("%NAME", clip_name)

    try:
        filename = dt.strftime(filename)
    except:
        _print("An error occurred while formatting filename.")
        _print(traceback.format_exc())
        if raise_exception:
            raise ValueError

        _print("Using default filename format.")
        return format_filename(clip_name, dt, force_default_template=True)

    for i in FILENAME_PROHIBITED_CHARS:
        if i in filename:
            if raise_exception:
                raise SyntaxError
            filename = filename.replace(i, "")

    return filename


def add_duplicate_suffix(path: str | Path) -> Path:
    """
    Adds "(n)" to the end of the file name if the passed file already exists.
    If "FILE_NAME (n)" also exists - increments n.

    :param path: path to file.
    :return: updated path.
    """
    path = str(path)

    filename, ext = os.path.splitext(path)
    num = 1
    while os.path.exists(path):
        path = filename + f" ({num})" + ext
        num += 1

    return Path(path)


# -------------------- save_buffer.py --------------------
def save_buffer(mode: int = 0) -> tuple[str, Path]:
    dt = datetime.now()

    old_file_path = get_last_replay_file_name()
    _print(f"Old clip file path: {old_file_path}")

    clip_name = gen_clip_base_name(mode)
    ext = old_file_path.split(".")[-1]
    filename = format_filename(clip_name, dt) + f".{ext}"

    new_folder = Path(get_base_path())
    if obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_CLIPS_SAVE_TO_FOLDER):
        new_folder = new_folder.joinpath(clip_name)

    os.makedirs(str(new_folder), exist_ok=True)
    new_path = new_folder.joinpath(filename)
    new_path = add_duplicate_suffix(new_path)
    _print(f"New clip file path: {new_path}")

    os.rename(old_file_path, str(new_path))
    _print("Clip file successfully moved.")
    return clip_name, new_path


def save_buffer_with_force_mode(mode: int):
    """
    Sends a request to save the replay buffer and setting a specific clip naming mode.
    Can only be called using hotkeys.
    """
    if not obs.obs_frontend_replay_buffer_active():
        return

    if FORCE_MODE_LOCK.locked():
        return

    FORCE_MODE_LOCK.acquire()
    VARIABLES.force_mode = mode
    obs.obs_frontend_replay_buffer_save()


# -------------------- obs_events_callbacks.py --------------------
# noinspection PyUnresolvedReferences
def on_buffer_recording_started_callback(event):
    """
    Resets and starts recording executables history.
    Starts replay buffer auto restart loop.
    """
    if event is not obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        return

    # Reset and restart exe history
    replay_max_size = get_replay_buffer_max_time()
    VARIABLES.clip_exe_history = deque([], maxlen=replay_max_size)
    _print(f"Exe history deque created. Maxlen={VARIABLES.clip_exe_history.maxlen}.")
    obs.timer_add(append_clip_exe_history, 1000)

    # Start replay buffer auto restart loop.
    if restart_loop_time := obs.obs_data_get_int(VARIABLES.script_settings, PN.PROP_RESTART_BUFFER_LOOP):
        obs.timer_add(restart_replay_buffering_callback, restart_loop_time * 1000)


def on_buffer_recording_stopped_callback(event):
    """
    Stops recording executables history.
    Stops replay buffer auto restart loop.
    """
    if event is not obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED:
        return

    obs.timer_remove(append_clip_exe_history)
    obs.timer_remove(restart_replay_buffering_callback)
    VARIABLES.clip_exe_history.clear()


def on_buffer_save_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        return

    _print("------ SAVING BUFFER HANDLER ------")
    try:
        clip_name, path = save_buffer(mode=VARIABLES.force_mode)
        if obs.obs_data_get_bool(VARIABLES.script_settings, PN.PROP_RESTART_BUFFER):
            # IMPORTANT
            # I don't know why, but it seems like stopping and starting replay buffering should be in the separate thread.
            # Otherwise it can "stuck" on stopping.
            Thread(target=restart_replay_buffering, daemon=True).start()

        if VARIABLES.force_mode:
            VARIABLES.force_mode = 0
            FORCE_MODE_LOCK.release()
        notify(True, str(path))
    except:
        _print("An error occurred while moving file to the new destination.")
        _print(traceback.format_exc())
        notify(False, "")
    _print("-----------------------------------")


def on_video_recording_started_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        return

    VARIABLES.video_exe_history = {}
    obs.timer_add(append_video_exe_history, 1000)


def on_video_recording_stopping_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_RECORDING_STOPPING:
        return

    obs.timer_remove(append_video_exe_history)


def on_video_recording_stopped_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        return

    # todo: save video into new location

    VARIABLES.video_exe_history = None

    _print(obs.obs_frontend_get_last_recording())


# -------------------- other_callbacks.py --------------------
def restart_replay_buffering_callback():
    """
    Restarts replay buffering and adds itself to obs time.

    This callback is only called by the obs timer.
    """
    _print("Restart replay buffering callback.")
    obs.timer_remove(restart_replay_buffering_callback)

    replay_length = get_replay_buffer_max_time()
    last_input_time = get_time_since_last_input()
    if last_input_time < replay_length:
        next_call = int((replay_length - last_input_time) * 1000)
        next_call = next_call if next_call >= 2000 else 2000

        _print(f"Replay length ({replay_length}s) is greater then time since last input ({last_input_time}s). Next call in {next_call / 1000}s.")
        obs.timer_add(restart_replay_buffering_callback, next_call)
        return

    # IMPORTANT
    # I don't know why, but it seems like stopping and starting replay buffering should be in the separate thread.
    # Otherwise it can "stuck" at stopping state.
    Thread(target=restart_replay_buffering, daemon=True).start()
    # I don't re-add this callback to timer again, cz it will be automatically added in on buffering start callback.


def append_clip_exe_history():
    """
    Adds current active executable path in clip exe history.
    """
    pid = get_active_window_pid()
    try:
        exe = get_executable_path(pid)
    except:
        return

    if VARIABLES.clip_exe_history is not None:
        VARIABLES.clip_exe_history.appendleft(Path(exe))
        # _print(f"{exe} added to exe history.")


def append_video_exe_history():
    """
    Adds current active executable path in video exe history.
    """
    pid = get_active_window_pid()
    try:
        exe = get_executable_path(pid)
    except:
        return

    if VARIABLES.video_exe_history is None:
        return

    path = Path(exe)
    if path not in VARIABLES.video_exe_history:
        VARIABLES.video_exe_history[path] = 1
    else:
        VARIABLES.video_exe_history[path] += 1


# -------------------- hotkeys.py --------------------
def load_hotkeys():
    hk1_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_1,
                                              "[Smart Replays] Save buffer (force mode 1)",
                                              lambda pressed: save_buffer_with_force_mode(1) if pressed else None)

    hk2_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_2,
                                              "[Smart Replays] Save buffer (force mode 2)",
                                              lambda pressed: save_buffer_with_force_mode(2) if pressed else None)

    hk3_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_3,
                                              "[Smart Replays] Save buffer (force mode 3)",
                                              lambda pressed: save_buffer_with_force_mode(3) if pressed else None)

    VARIABLES.hotkey_ids.update({PN.HK_SAVE_BUFFER_MODE_1: hk1_id,
                                 PN.HK_SAVE_BUFFER_MODE_2: hk2_id,
                                 PN.HK_SAVE_BUFFER_MODE_3: hk3_id})

    for key_name in VARIABLES.hotkey_ids:
        key_data = obs.obs_data_get_array(VARIABLES.script_settings, key_name)
        obs.obs_hotkey_load(VARIABLES.hotkey_ids[key_name], key_data)
        obs.obs_data_array_release(key_data)


# -------------------- obs_script_other.py --------------------
def script_defaults(s):
    _print("Loading default values...")
    obs.obs_data_set_default_string(s, PN.PROP_CLIPS_BASE_PATH, get_obs_config("SimpleOutput", "FilePath"))
    obs.obs_data_set_default_int(s, PN.PROP_CLIPS_FILENAME_CONDITION, 1)
    obs.obs_data_set_default_string(s, PN.PROP_CLIPS_FILENAME_FORMAT, DEFAULT_FILENAME_FORMAT)
    obs.obs_data_set_default_bool(s, PN.PROP_CLIPS_SAVE_TO_FOLDER, True)
    obs.obs_data_set_default_bool(s, PN.PROP_NOTIFICATION_ON_SUCCESS, False)
    obs.obs_data_set_default_bool(s, PN.PROP_NOTIFICATION_ON_FAILURE, False)
    obs.obs_data_set_default_int(s, PN.PROP_RESTART_BUFFER_LOOP, 3600)
    obs.obs_data_set_default_bool(s, PN.PROP_RESTART_BUFFER, True)

    arr = obs.obs_data_array_create()
    for index, i in enumerate(DEFAULT_CUSTOM_NAMES):
        data = obs.obs_data_create_from_json(json.dumps(i))
        obs.obs_data_array_insert(arr, index, data)

    obs.obs_data_set_default_array( s, PN.PROP_CUSTOM_NAMES_LIST, arr )
    _print("The default values are set.")


def script_update(settings):
    _print("Updating script...")

    VARIABLES.script_settings = settings
    _print(obs.obs_data_get_json(VARIABLES.script_settings))
    _print("Script updated")


def script_save(settings):
    _print("Saving script...")

    for key_name in VARIABLES.hotkey_ids:
        k = obs.obs_hotkey_save(VARIABLES.hotkey_ids[key_name])
        obs.obs_data_set_array(settings, key_name, k)
    _print("Script saved")


def script_load(script_settings):
    _print("Loading script...")
    VARIABLES.script_settings = script_settings
    VARIABLES.update_available = check_updates(VERSION)

    json_settings = json.loads(obs.obs_data_get_json(script_settings))
    load_custom_names(json_settings)

    obs.obs_frontend_add_event_callback(on_buffer_save_callback)
    obs.obs_frontend_add_event_callback(on_buffer_recording_started_callback)
    obs.obs_frontend_add_event_callback(on_buffer_recording_stopped_callback)

    obs.obs_frontend_add_event_callback(on_video_recording_started_callback)
    obs.obs_frontend_add_event_callback(on_video_recording_stopping_callback)
    obs.obs_frontend_add_event_callback(on_video_recording_stopped_callback)
    load_hotkeys()

    if obs.obs_frontend_replay_buffer_active():
        on_buffer_recording_started_callback(obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED)

    _print("Script loaded.")


def script_unload():
    obs.timer_remove(append_clip_exe_history)
    obs.timer_remove(restart_replay_buffering_callback)

    _print("Script unloaded.")


def script_description():
    return f"""
<div style="font-size: 60pt; text-align: center;">
Smart Replays 
</div>

<div style="font-size: 12pt; text-align: left;">
Smart Replays is an OBS script whose main purpose is to save clips with different names and to separate folders depending on the application being recorded (imitating NVIDIA Shadow Play functionality). This script also has additional functionality, such as sound and pop-up notifications, auto-restart of the replay buffer, etc.
</div>

<div style="font-size: 10pt; text-align: left; margin-top: 20px;">
Version: {VERSION}<br/>
Developed by: Qvvonk<br/>
</div>
"""