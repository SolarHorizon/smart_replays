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

from .globals import (_print,
                      script_settings,
                      exe_history,
                      custom_names,
                      DEFAULT_FILENAME_FORMAT,
                      FILENAME_PROHIBITED_CHARS, PN)

from .tech import get_active_window_pid, get_executable_path
from .obs_related import get_current_scene_name

import obspython as obs
from pathlib import Path
from datetime import datetime
import traceback
import os


def gen_clip_name(mode: int) -> str:
    """
    Generates clip name based on script settings.
    It's NOT generates new path for clip.
    """
    _print("Generating clip name...")
    mode = obs.obs_data_get_int(script_settings, PN.PROP_FILENAME_CONDITION) if not mode else mode

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
            if exe_history:
                executable_path = max(exe_history, key=exe_history.count)
            else:
                executable_path = get_executable_path(get_active_window_pid())
            executable_path_obj = Path(executable_path)


        if clip_name := get_name_from_custom_names(executable_path):
            return clip_name
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
    for i in custom_names:
        if last_result is None and any([executable_path == i, i in executable_path.parents]):
            last_result = i
            continue

        if last_result in i.parents:
            last_result = i

    if last_result is None:
        _print(f"{executable_path} or its parents are not in custom names.")
        return None

    _print(f"{executable_path} or its parent was found on the list: {last_result} > {custom_names[last_result]}.")
    return custom_names[last_result]


def format_filename(clip_name: str, dt: datetime | None = None,
                    force_default_template: bool = False, raise_exception: bool = False) -> str:
    """
    Formats the clip file name based on the template.
    If the template is invalid, uses the default template.

    :param clip_name: clip name.
    :param dt: datetime obj.
    :param force_default_template: use the default template even if the template in the settings is valid.
    :param raise_exception: raise exception if template is invalid instead of using default template.
    """
    if dt is None:
        dt = datetime.now()

    template = obs.obs_data_get_string(script_settings, PN.PROP_FILENAME_FORMAT)

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
    if isinstance(path, Path):
        path = str(path)

    filename, ext = os.path.splitext(path)
    num = 1
    while os.path.exists(path):
        path = filename + f" ({num})" + ext
        num += 1

    return Path(path)