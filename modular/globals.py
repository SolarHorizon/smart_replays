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
CLIPS_FORCE_MODE_LOCK = Lock()
VIDEOS_FORCE_MODE_LOCK = Lock()
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
    exe_path_on_video_sopping: Path | None = None
    custom_names: dict[Path, str] = {}
    script_settings = None
    hotkey_ids: dict = {}
    force_mode = 0


class ConfigTypes(Enum):
    PROFILE = 0
    APP = 1
    USER = 2


class ClipNamingModes(Enum):
    CURRENT_PROCESS = 1
    MOST_RECORDED_PROCESS = 2
    CURRENT_SCENE = 3


class VideoNamingModes(Enum):
    CURRENT_PROCESS = 1
    MOST_RECORDED_PROCESS = 2
    CURRENT_SCENE = 3


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
    PROP_CLIPS_NAMING_MODE = "clips_naming_mode"
    TXT_CLIPS_HOTKEY_TIP = "clips_hotkey_tip"
    PROP_CLIPS_FILENAME_FORMAT = "clips_filename_format"
    TXT_CLIPS_FILENAME_FORMAT_ERR = "clips_filename_format_err"
    PROP_CLIPS_SAVE_TO_FOLDER = "clips_save_to_folder"

    # Videos path settings
    PROP_VIDEOS_NAMING_MODE = "video_naming_mode"
    TXT_VIDEOS_HOTKEY_TIP = "videos_hotkey_tip"
    PROP_VIDEOS_FILENAME_FORMAT = "videos_filename_format"
    TXT_VIDEOS_FILENAME_FORMAT_ERR = "videos_filename_format_err"
    PROP_VIDEOS_SAVE_TO_FOLDER = "videos_save_to_folder"
    PROP_VIDEOS_ONLY_FORCE_MODE = "videos_only_force_mode"

    # Sound notification settings
    PROP_NOTIFY_CLIPS_ON_SUCCESS = "notify_clips_on_success"
    PROP_NOTIFY_CLIPS_ON_SUCCESS_PATH = "notify_clips_on_success_file"
    PROP_NOTIFY_CLIPS_ON_FAILURE = "notify_clips_on_failure"
    PROP_NOTIFY_CLIPS_ON_FAILURE_PATH = "notify_clips_on_failure_file"
    PROP_NOTIFY_VIDEOS_ON_SUCCESS = "notify_videos_on_success"
    PROP_NOTIFY_VIDEOS_ON_SUCCESS_PATH = "notify_videos_on_success_file"
    PROP_NOTIFY_VIDEOS_ON_FAILURE = "notify_videos_on_failure"
    PROP_NOTIFY_VIDEOS_ON_FAILURE_PATH = "notify_videos_on_failure_file"

    # Popup notification settings
    PROP_POPUP_CLIPS_ON_SUCCESS = "popup_clips_on_success"
    PROP_POPUP_CLIPS_ON_FAILURE = "popup_clips_on_failure"
    PROP_POPUP_VIDEOS_ON_SUCCESS = "popup_videos_on_success"
    PROP_POPUP_VIDEOS_ON_FAILURE = "popup_videos_on_failure"

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
