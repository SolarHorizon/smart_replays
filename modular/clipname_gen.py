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

from .globals import VARIABLES, CONSTANTS, PN

from .tech import get_active_window_pid, get_executable_path, _print
from .obs_related import get_current_scene_name

import obspython as obs
from pathlib import Path
from datetime import datetime
import traceback


def gen_clip_base_name(mode: int) -> str:
    """
    Generates clip base name based on clip naming mode.
    It's NOT generates new path for clip.

    :param mode: Clip naming mode. If 0 - gets mode from script config.
    """
    _print("Generating clip base name...")
    mode = obs.obs_data_get_int(VARIABLES.script_settings, PN.PROP_CLIPS_NAMING_MODE) if not mode else mode

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


def get_exe_alias(executable_path: str | Path, aliases_dict: dict[Path, str]) -> str | None:
    """
    Retrieves a custom alias for the given executable path from the provided dictionary.

    The function first checks if the exact `executable_path` exists in `aliases_dict`.
    If not, it searches for the closest parent directory that is present in the dictionary.

    :param executable_path: A file path or string representing the executable.
    :param aliases_dict: A dictionary where keys are `Path` objects representing executable file paths
                         or directories, and values are their corresponding custom aliases.
    :return: The corresponding alias if found, otherwise `None`.
    """
    exe_path = Path(executable_path)
    if exe_path in aliases_dict:
        return aliases_dict[exe_path]

    for parent in exe_path.parents:
        if parent in aliases_dict:
            return aliases_dict[parent]



def format_filename(name: str, dt: datetime | None = None,
                    force_default_template: bool = False, raise_exception: bool = False) -> str:
    """
    Formats the clip file name based on the template.
    If the template is invalid, uses the default template.

    :param name: base name.
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
        template = CONSTANTS.DEFAULT_FILENAME_FORMAT

    if force_default_template:
        template = CONSTANTS.DEFAULT_FILENAME_FORMAT

    filename = template.replace("%NAME", name)

    try:
        filename = dt.strftime(filename)
    except:
        _print("An error occurred while formatting filename.")
        _print(traceback.format_exc())
        if raise_exception:
            raise ValueError

        _print("Using default filename format.")
        return format_filename(name, dt, force_default_template=True)

    for i in CONSTANTS.FILENAME_PROHIBITED_CHARS:
        if i in filename:
            if raise_exception:
                raise SyntaxError
            filename = filename.replace(i, "")

    return filename


def gen_unique_filename(file_path: str | Path) -> Path:
    """
    Generates a unique filename by adding a numerical suffix if the file already exists.

    :param file_path: A string or Path object representing the target file.
    :return: A unique Path object with a modified name if necessary.
    """
    file_path = Path(file_path)
    folder, stem, suffix = file_path.parent, file_path.stem, file_path.suffix

    new_path = file_path
    counter = 1

    while new_path.exists():
        new_path = folder / f"{stem} ({counter}){suffix}"
        counter += 1

    return new_path
