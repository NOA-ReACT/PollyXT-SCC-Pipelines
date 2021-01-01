from datetime import datetime
from typing import Union
from pathlib import Path

from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.console import console


class RadiosondeNotFound(Exception):
    """
    Raised when a provider fails to find the requested radiosonde
    """

    location: Location
    providerName: str
    time: datetime
    timeIso: str
    expectedFilename: Union[Path, str]

    def __init__(
        self,
        location: Location,
        providerName: str,
        time: datetime,
        expectedFilename: Union[Path, str],
    ):
        super().__init__()
        self.location = location
        self.providerName = providerName
        self.time = time
        self.time
        self.timeIso = self.time.isoformat()
        self.expectedFilename = expectedFilename

    def __str__(self) -> str:
        return f"Could not find radiosonde for {self.location.name} at {self.timeIso} using provider {self.providerName}"

    def print_error(self):
        """Creates a markdown error message for printing"""
        console.print(
            f"[error]Could not find radiosonde for[/error] {self.location.name} [error]at[/error] [info]{self.timeIso}[/info]."
        )
        console.print(
            f"[error]Using provider[/error] {self.providerName}[error], radiosonde file should have been:[/error] {self.expectedFilename}"
        )
