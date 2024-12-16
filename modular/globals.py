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

import sys
import ctypes
from ctypes import wintypes
from datetime import datetime
from threading import Lock
from pathlib import Path
from collections import deque


VERSION = "1.0.1"  # Script version
FORCE_MODE_LOCK = Lock()
FILENAME_PROHIBITED_CHARS = r'/\:"<>*?|%'
PATH_PROHIBITED_CHARS = r'"<>*?|%'
DEFAULT_FILENAME_FORMAT = "%NAME_%d.%m.%Y_%H-%M-%S"
DEFAULT_CUSTOM_NAMES = [
    {"value": "C:\\Windows\\explorer.exe > Desktop", "selected": False, "hidden": False},
    {"value": f"{sys.executable} > OBS", "selected": False, "hidden": False}
]

user32 = ctypes.windll.user32
exe_history: deque | None = None
custom_names: dict[Path, str] = {}
script_settings = None
hotkey_ids: dict = {}
force_mode = 0


class PropertiesNames:
    GR_PATHS = "paths"
    GR_NOTIFICATIONS = "notifications"
    GR_POPUP = "popup"
    GR_CUSTOM_NAMES = "custom_names"
    GR_OTHER = "other"

    PROP_BASE_PATH = "base_path"
    TEXT_BASE_PATH_INFO = "base_path_info"
    PROP_FILENAME_CONDITION = "filename_condition"
    TXT_HOTKEY_TIP = "hotkey_tip"
    PROP_FILENAME_FORMAT = "filename_format"
    TXT_FILENAME_FORMAT_ERR = "filename_format_err"
    PROP_SAVE_TO_FOLDER = "save_to_folder"

    PROP_NOTIFICATION_ON_SUCCESS = "notification_on_success"
    PROP_NOTIFICATION_ON_SUCCESS_PATH = "notification_on_success_file"
    PROP_NOTIFICATION_ON_FAILURE = "notification_on_failure"
    PROP_NOTIFICATION_ON_FAILURE_PATH = "notification_on_failure_file"

    PROP_POPUP_ON_SUCCESS = "prop_popup_on_success"
    PROP_POPUP_ON_FAILURE = "prop_popup_on_failure"

    PROP_CUSTOM_NAMES_LIST = "custom_names_list"
    TXT_CUSTOM_NAME_DESC = "custom_names_desc"

    TXT_CUSTOM_NAMES_PATH_EXISTS = "custom_names_path_exists_err"
    TXT_CUSTOM_NAMES_INVALID_FORMAT = "custom_names_invalid_format_err"
    TXT_CUSTOM_NAMES_INVALID_CHARACTERS = "custom_names_invalid_characters_err"

    PROP_CUSTOM_NAMES_EXPORT_PATH = "custom_names_export_path"
    BTN_CUSTOM_NAMES_EXPORT = "btn_custom_names_export"
    PROP_CUSTOM_NAMES_IMPORT_PATH = "custom_names_import_path"
    BTN_CUSTOM_NAMES_IMPORT = "btn_custom_names_import"

    PROP_RESTART_BUFFER = "restart_buffer"
    PROP_RESTART_BUFFER_LOOP = "restart_buffer_loop"
    TXT_RESTART_BUFFER_LOOP = "txt_restart_buffer_loop"

    HK_SAVE_BUFFER_MODE_1 = "obssmartreplayshk1"
    HK_SAVE_BUFFER_MODE_2 = "obssmartreplayshk2"
    HK_SAVE_BUFFER_MODE_3 = "obssmartreplayshk3"

PN = PropertiesNames


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT),
                ("dwTime", wintypes.DWORD)]


def _print(*values, sep: str | None = None, end: str | None = None, file=None, flush: bool = False):
    time_ = datetime.now()
    str_time = time_.strftime(f"%d.%m.%Y %H:%M:%S")
    prefix = f"[{str_time}]"
    print(prefix, *values, sep=sep, end=end, file=file, flush=flush)