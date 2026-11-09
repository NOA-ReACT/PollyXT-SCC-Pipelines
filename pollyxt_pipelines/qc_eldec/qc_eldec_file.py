"""
Calibration QC with a history file kept in the config directory, for the CLI.

This is a wrapper around `pollyxt_pipelines.qc_eldec.qc`; library users should use that
module directly and keep the history themselves.

Original code by Ina Mattis (@imattis on GitLab): https://gitlab.com/imattis/qc_eldec_file
Original code unlicensed but used with permission
"""

import logging
from pathlib import Path

from pollyxt_pipelines import config
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.qc_eldec import qc

logger = logging.getLogger(__name__)


def history_path(location: Location, wavelength: int) -> Path:
    """Path of the CLI's QC history file for a location and wavelength"""
    return config.config_paths()[-1] / "qc_eldec" / f"{location.name}_{wavelength}nm.nc"


class ELDECfile:
    """
    Reads an ELDEC file, checks it against the location's history file in the config
    directory, adds it to that history if it passes, and optionally plots it.

    The following criteria are checked:
        * is relative error of the gain factor below threshold?
        * is relative standard deviation of ratio profiles below threshold?
        * is there an overlap between uncertainty range of gain factor and standard
          deviation of time series * factor? Only with enough points in the history.

    Use `calibration_ok()` for the result.
    """

    def __init__(self, filename, location: Location, plot_path=None):
        """
        Parameters
            filename: path of the ELDEC file
            location: the station; each station has its own history
            plot_path: optionally, where to save the plot
        """

        self.path = Path(filename)
        self.plot_path = plot_path

        self.eldec = qc.read_eldec(self.path)
        self.timeseries_path = history_path(location, self.eldec.wavelength)
        self.timeseries_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.timeseries_path.exists():
            logger.info(
                "History of past calibrations not found at %s. Creating a new file...",
                self.timeseries_path,
            )
            qc.create_history_file(self.timeseries_path)

        self.history = qc.read_history_file(
            self.timeseries_path, wavelength=self.eldec.wavelength
        )
        self.result = qc.check_calibration(self.eldec, self.history)
        self.is_ok = self.result.ok
        for reason in self.result.reasons:
            logger.warning("%s: %s", self.path.name, reason)

        if self.is_ok:
            qc.append_to_history_file(self.timeseries_path, self.result.point)

        if self.plot_path is not None:
            qc.plot_calibration(self.eldec, self.history, self.result, self.plot_path)

    # Kept for compatibility with code using the old attributes
    @property
    def measurement_ID(self) -> str:
        return self.eldec.measurement_id

    @property
    def wavelength(self) -> int:
        return self.eldec.wavelength

    @property
    def calvalue(self) -> float:
        return self.eldec.value

    @property
    def calvalue_error(self) -> float:
        return self.eldec.error

    @property
    def start_time(self):
        return self.eldec.start_time

    def calibration_ok(self) -> bool:
        """Whether the calibration passed the QC check"""
        return self.is_ok
