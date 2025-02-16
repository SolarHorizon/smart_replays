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

class CustomNameParsingError(Exception):
    """
    Base exception for all custom names related exceptions.
    """
    def __init__(self, index):
        """
        :param index: custom name index.
        """
        super(Exception).__init__()
        self.index = index


class CustomNamePathAlreadyExists(CustomNameParsingError):
    """
    Exception raised when a custom name is already exists.
    """


class CustomNameInvalidCharacters(CustomNameParsingError):
    """
    Exception raised when a custom name has invalid characters.
    """


class CustomNameInvalidFormat(CustomNameParsingError):
    """
    Exception raised when a custom name is invalid format.
    """
