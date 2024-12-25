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

from .globals import clip_exe_history, video_exe_history, script_settings, PN, FORCE_MODE_LOCK
from .tech import _print
from .obs_related import get_replay_buffer_max_time, restart_replay_buffering
from .script_helpers import notify
from .other_callbacks import restart_replay_buffering_callback, append_clip_exe_history, append_video_exe_history
from .save_buffer import save_buffer

import obspython as obs
from collections import deque
from threading import Thread
import traceback


def on_buffer_recording_started_callback(event):
    """
    Resets and starts recording executables history.
    Starts replay buffer auto restart loop.
    """
    if event is not obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        return

    # Reset and restart exe history
    global clip_exe_history
    replay_max_size = get_replay_buffer_max_time()
    clip_exe_history = deque([], maxlen=replay_max_size)
    _print(f"Exe history deque created. Maxlen={clip_exe_history.maxlen}.")
    obs.timer_add(append_clip_exe_history, 1000)

    # Start replay buffer auto restart loop.
    if restart_loop_time := obs.obs_data_get_int(script_settings, PN.PROP_RESTART_BUFFER_LOOP):
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
    clip_exe_history.clear()


def on_buffer_save_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        return

    global force_mode
    _print("------ SAVING BUFFER HANDLER ------")
    try:
        clip_name, path = save_buffer(mode=force_mode)
        if obs.obs_data_get_bool(script_settings, PN.PROP_RESTART_BUFFER):
            # IMPORTANT
            # I don't know why, but it seems like stopping and starting replay buffering should be in the separate thread.
            # Otherwise it can "stuck" on stopping.
            Thread(target=restart_replay_buffering, daemon=True).start()

        if force_mode:
            force_mode = 0
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

    global video_exe_history
    video_exe_history = {}
    obs.timer_add(append_video_exe_history, 1000)


def on_video_recording_stopping_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_RECORDING_STOPPING:
        return

    obs.timer_remove(append_video_exe_history)


def on_video_recording_stopped_callback(event):
    if event is not obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        return

    # todo: save video into new location

    global video_exe_history
    video_exe_history = None

    _print(obs.obs_frontend_get_last_recording())
