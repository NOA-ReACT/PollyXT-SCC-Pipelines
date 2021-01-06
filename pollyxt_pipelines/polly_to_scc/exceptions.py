from pathlib import Path
from datetime import datetime
from typing import Tuple


class TimeOutsideFile(Exception):
    """
    Raised when the requested time is outside the file
    """

    def __init__(self, start: datetime, end: datetime, requested: datetime):
        super().__init__(start, end, requested)

        self.start = start
        self.end = end
        self.requested = requested

    def __str__(self) -> str:
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        requested = self.requested.strftime("%H:%M")
        return f"The requested time {requested} is outside the file's range ({start}-{end})"


class NoMeasurementsInTimePeriod(Exception):
    """
    Raised when there are no measurements inside the requested time period
    """


class NoFilesFound(Exception):
    """
    Raised when no files are found at the given path
    """

    def __init__(self, path: Path):
        super(self)
        self.path = path

    def __str__(self) -> str:
        return f"No netCDF files found at {self.path}"


class BadMeasurementTime(Exception):
    """
    Raised when a bad measurement time value is encountered in a raw PollyXT file
    """

    def __init__(self, filename: str, value: Tuple[int, int]) -> None:
        super().__init__(filename, value)

        self.filename = filename
        self.value = value

    def __str__(self) -> str:
        return (
            f"Bad measurement time value was encountered in file {self.filename}: {str(self.value)}"
        )
