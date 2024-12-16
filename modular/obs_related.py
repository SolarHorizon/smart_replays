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

from .globals import script_settings, PN
from .tech import _print

import obspython as obs
import time


def get_obs_config(section_name: str | None = None,
                   param_name: str | None = None,
                   value_type: type[str, int, bool, float] = str,
                   global_config: bool = False):
    """
    Gets a value from OBS config.
    If the value is not set, it will use the default value. If there is no default value, it will return NULL.
    If section_name or param_name are not specified, returns OBS config obj.

    :param section_name: Section name. If not specified, returns the OBS config.
    :param param_name: Parameter name. If not specified, returns the OBS config.
    :param value_type: Type of value (str, int, bool, float).
    :param global_config: Search in global config or profile config?
    """
    cfg = obs.obs_frontend_get_global_config() if global_config else obs.obs_frontend_get_profile_config()

    if not (section_name and param_name):
        return cfg

    functions = {
        str: obs.config_get_string,
        int: obs.config_get_int,
        bool: obs.config_get_bool,
        float: obs.config_get_double
    }

    if value_type not in functions.keys():
        raise ValueError(f'Can\'t get value of {param_name} from section {section_name}: '
                         f'unsupported value type {value_type.__class__.__name__}')

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
        script_path = obs.obs_data_get_string(script_settings, PN.PROP_BASE_PATH)
        # If PN.PROP_BASE_PATH is not saved in the script config, then it has a default value,
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
