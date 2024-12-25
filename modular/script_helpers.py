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

from .globals import (script_settings,
                      clip_exe_history,
                      DEFAULT_CUSTOM_NAMES,
                      PATH_PROHIBITED_CHARS,
                      FILENAME_PROHIBITED_CHARS,
                      PN)

from .exceptions import CustomNameInvalidFormat, CustomNameInvalidCharacters, CustomNamePathAlreadyExists
from .obs_related import get_obs_config
from .tech import play_sound, _print

from pathlib import Path
import os
import obspython as obs
import subprocess


def notify(success: bool, clip_path: str):
    """
    Plays and shows success / failure notification if it's enabled in notifications settings.
    """
    sound_notifications = obs.obs_data_get_bool(script_settings, PN.GR_NOTIFICATIONS)
    popup_notifications = obs.obs_data_get_bool(script_settings, PN.GR_POPUP)
    python_exe = os.path.join(get_obs_config("Python", "Path64bit", str, True), "pythonw.exe")

    if success:
        if sound_notifications and obs.obs_data_get_bool(script_settings, PN.PROP_NOTIFICATION_ON_SUCCESS):
            path = obs.obs_data_get_string(script_settings, PN.PROP_NOTIFICATION_ON_SUCCESS_PATH)
            play_sound(path)

        if popup_notifications and obs.obs_data_get_bool(script_settings, PN.PROP_POPUP_ON_SUCCESS):
            subprocess.Popen([python_exe, __file__, "Clip saved", f"Clip saved to {clip_path}"])
    else:
        if sound_notifications and obs.obs_data_get_bool(script_settings, PN.PROP_NOTIFICATION_ON_FAILURE):
            path = obs.obs_data_get_string(script_settings, PN.PROP_NOTIFICATION_ON_FAILURE_PATH)
            play_sound(path)

        if popup_notifications and obs.obs_data_get_bool(script_settings, PN.PROP_POPUP_ON_FAILURE):
            subprocess.Popen([python_exe, __file__, "Clip not saved", f"More in the logs.", "#C00000"])


def load_custom_names(data_dict: dict):
    """
    Loads custom names to global custom_name variable.
    Raises exception if path or name are invalid.

    :param data_dict: Script settings as dict.
    """
    _print("Loading custom names...")

    global custom_names
    new_custom_names = {}
    custom_names_list = data_dict.get(PN.PROP_CUSTOM_NAMES_LIST)
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

    custom_names = new_custom_names
    _print(f"{len(custom_names)} custom names are loaded.")
