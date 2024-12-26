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

from .globals import (VARIABLES,
                      VERSION,
                      DEFAULT_FILENAME_FORMAT,
                      DEFAULT_CUSTOM_NAMES, PN)

from .tech import _print
from .obs_related import get_obs_config
from .other_callbacks import restart_replay_buffering_callback, append_clip_exe_history
from .obs_events_callbacks import (on_buffer_save_callback,
                                   on_buffer_recording_started_callback,
                                   on_buffer_recording_stopped_callback,
                                   on_video_recording_started_callback,
                                   on_video_recording_stopping_callback,
                                   on_video_recording_stopped_callback)
from .updates_check import check_updates
from .globals import VERSION
from .script_helpers import load_custom_names
from .hotkeys import load_hotkeys

import obspython as obs
import json


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