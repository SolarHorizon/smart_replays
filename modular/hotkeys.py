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


from .globals import PN, VARIABLES
from .save_buffer import save_buffer_with_force_mode

import obspython as obs


def load_hotkeys():
    hk1_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_1,
                                              "[Smart Replays] Save buffer (force mode 1)",
                                              lambda pressed: save_buffer_with_force_mode(1) if pressed else None)

    hk2_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_2,
                                              "[Smart Replays] Save buffer (force mode 2)",
                                              lambda pressed: save_buffer_with_force_mode(2) if pressed else None)

    hk3_id = obs.obs_hotkey_register_frontend(PN.HK_SAVE_BUFFER_MODE_3,
                                              "[Smart Replays] Save buffer (force mode 3)",
                                              lambda pressed: save_buffer_with_force_mode(3) if pressed else None)

    VARIABLES.hotkey_ids.update({PN.HK_SAVE_BUFFER_MODE_1: hk1_id,
                                 PN.HK_SAVE_BUFFER_MODE_2: hk2_id,
                                 PN.HK_SAVE_BUFFER_MODE_3: hk3_id})

    for key_name in VARIABLES.hotkey_ids:
        key_data = obs.obs_data_get_array(VARIABLES.script_settings, key_name)
        obs.obs_hotkey_load(VARIABLES.hotkey_ids[key_name], key_data)
        obs.obs_data_array_release(key_data)
