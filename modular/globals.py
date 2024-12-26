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
from enum import Enum
import ctypes
from threading import Lock
from pathlib import Path
from collections import deque
import obspython as obs


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
