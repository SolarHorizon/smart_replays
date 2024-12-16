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

from .globals import script_settings, FORCE_MODE_LOCK, PN
from .obs_related import get_last_replay_file_name, get_base_path
from .clipname_gen import gen_clip_base_name, format_filename, add_duplicate_suffix
from .tech import _print

from datetime import datetime
from pathlib import Path
import obspython as obs
import os


def save_buffer(mode: int = 0) -> tuple[str, Path]:
    dt = datetime.now()

    old_file_path = get_last_replay_file_name()
    _print(f"Old clip file path: {old_file_path}")

    clip_name = gen_clip_base_name(mode)
    ext = old_file_path.split(".")[-1]
    filename = format_filename(clip_name, dt) + f".{ext}"

    new_folder = Path(get_base_path())
    if obs.obs_data_get_bool(script_settings, PN.PROP_SAVE_TO_FOLDER):
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
    global force_mode
    force_mode = mode
    obs.obs_frontend_replay_buffer_save()