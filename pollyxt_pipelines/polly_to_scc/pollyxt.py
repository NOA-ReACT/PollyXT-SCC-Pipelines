"""
Routines related to PollyXT files
"""

from pathlib import Path
from typing import Tuple, Union
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from netCDF4 import Dataset

from pollyxt_pipelines.polly_to_scc.exceptions import (
    NoFilesFound,
    NoMeasurementsInTimePeriod,
    BadMeasurementTime,
)


def polly_date_to_datetime(timestamp: Tuple[int, int]) -> datetime:
    """
    Converts a PollyXT Date to a Python object.

    Parameters:
        timestamp: PollyXT timestamp in two-integer format: 1) date as YYYYMMDD 2) seconds since start of day

    Returns:
        A datetime object
    """
    day, seconds = timestamp
    day_str = str(day)

    date = datetime.strptime(day_str, "%Y%m%d")
    return date + timedelta(seconds=int(seconds))


def get_measurement_period(input: Union[Path, Dataset, np.ndarray]) -> Tuple[datetime, datetime]:
    """
    Return the measurement time (i.e. start and end times) from a PollyXT file.

    Parameters:
        input: Either a path to a PollyXT netCDF file, an opened netCDF dataset or the
            `measurement_time` variable.

    Returns:
        A tuple containing the start and end dates.
    """

    # Read `measurement_time` variable, a bit different for each source
    if isinstance(input, Path):
        nc = Dataset(input, "r")
        measurement_time = nc["measurement_time"][:]
        nc.close()
    elif isinstance(input, Dataset):
        measurement_time = input["measurement_time"][:]
    elif isinstance(input, np.ndarray):
        measurement_time = input
    else:
        raise ValueError(
            f"Parameter `input` must be a Path, a Dataset (netCDF) or a numpy array, not {type(input)}"
        )

    # Do some sanity checks on its shape
    shape = measurement_time.shape
    assert len(shape) == 2
    assert shape[1] == 2

    # Parse start/end times
    day_str = str(measurement_time[0, 0])
    date = datetime.strptime(day_str, "%Y%m%d")
    start = date + timedelta(seconds=int(measurement_time[0, 1]))
    end = date + timedelta(seconds=int(measurement_time[-1, 1]))

    return start, end


def find_time_indices(
    measurement_time: np.ndarray, start: datetime, end: datetime
) -> Tuple[int, int]:
    """
    Given the `measurement_time` array from a PollyXT netCDF file and a time period (`start` and
    `end` in HH:MM format), this function returns the indices of the time period in the array.

    The `measurement_time` array has two columns, the first contains the date in YYYYMMDD format
    and the second column contains each measurement's delta from the date, in seconds (!).
    """

    measurement_start, measurement_end = get_measurement_period(measurement_time)

    # Do some validation on the dates
    if start > end:
        raise ValueError(f"Selected start ({start}) is after selected end ({end})!")
    if start < measurement_start:
        mstart = measurement_start.strftime("%H:%M")
        raise ValueError(f"Selected start ({start}) is before file start ({mstart})!")
    if start > measurement_end:
        mend = measurement_end.strftime("%H:%M")
        raise ValueError(f"Selected end ({end}) is after file end ({mend})!")

    # Find indices
    dt1 = (start - measurement_start).seconds
    dt2 = (end - measurement_start).seconds

    index_start = dt1 // 30
    index_end = dt2 // 30

    return (index_start, index_end)


class PollyXTRepository:
    """
    Represents a collection of PollyXT netCDF files. Provides facilities for reading data from such
    files, even across single-file boundaries.
    """

    def __init__(self, path: Path):
        """
        Create a repository

        Parameters
            path: Where are the PollyXT netCDF files stored. Can either be a directory of a single file
        """

        # Create a list of files to include in the repository
        self.path = path

        if self.path.is_dir():
            self.files = list(self.path.glob("*.nc"))
        elif self.path.is_file():
            self.files = [self.path]
        else:
            raise ValueError(f"Path {self.path} doesn't seem to be either a file or a directory")

        if len(self.files) == 0:
            raise NoFilesFound(self.path)

        # Create the index table
        rows = []
        for path in self.files:
            with Dataset(path, "r") as nc:
                measurement_time = nc["measurement_time"][:]
                for i, timestamp in enumerate(measurement_time):
                    # Parse date
                    try:
                        timestamp = polly_date_to_datetime(timestamp)
                    except ValueError:
                        raise BadMeasurementTime(path, timestamp)

                    rows.append({"timestamp": timestamp, "index": i, "path": path})

        self.index = pd.DataFrame(rows)
        self.index = self.index.sort_values("timestamp", ascending=True)

    def get_time_period(self) -> Tuple[datetime, datetime]:
        """
        Returns the time period available in this repository

        Returns:
            A tuple containing the first and last available timestamps
        """

        start = self.index.iloc[0]["timestamp"]
        end = self.index.iloc[-1]["timestamp"]

        return start, end

    def get_pollyxt_file(self, time_start: datetime, time_end: datetime):
        """
        Create a PollyXTFile for the given time range.

        Parameters:
            time_start: First measurement to include
            time_end: Last measurement to include

        Returns:
            The PollyXTFile file for the requested period.
        """

        # Filter index for given time range
        mask = (self.index["timestamp"] >= time_start) & (self.index["timestamp"] <= time_end)
        targets = self.index[mask]
        if targets.shape[0] == 0:
            raise NoMeasurementsInTimePeriod()

        # Read all files and concat into the requested
        polly_files = []
        for path in targets["path"].unique():
            targets_filtered = targets[targets["path"] == path]

            start_index = targets_filtered["index"].min()
            end_index = targets_filtered["index"].max()

            polly_files.append(PollyXTFile(path, start=start_index, end=end_index))

        # Concatenate data into one file
        pollyxt_file = polly_files[0]
        pollyxt_file.raw_signal = np.concatenate([x.raw_signal for x in polly_files])
        pollyxt_file.raw_signal_swap = np.concatenate([x.raw_signal_swap for x in polly_files])
        pollyxt_file.measurement_time = np.concatenate([x.measurement_time for x in polly_files])
        pollyxt_file.measurement_shots = np.concatenate([x.measurement_shots for x in polly_files])
        try:
            pollyxt_file.zenith_angle = np.concatenate([x.zenith_angle for x in polly_files])
        except ValueError:
            # Sometimes these arrays are empty, this is not a problem
            pass
        pollyxt_file.depol_cal_angle = np.concatenate([x.depol_cal_angle for x in polly_files])

        pollyxt_file.end_date = polly_files[-1].end_date

        return pollyxt_file


class PollyXTFile:
    """
    Reads the variables of interest from a PollyXT netCDF file.
    """

    start_date: datetime
    start_index: int
    end_index: int
    end_date: datetime

    raw_signal: np.ndarray
    raw_signal_swap: np.ndarray

    measurement_time: np.ndarray
    measurement_shots: np.ndarray
    zenith_angle: np.ndarray
    location_coordinates: np.ndarray
    depol_cal_angle: np.ndarray

    def __init__(self, input_path: Path, start: int = None, end: int = None, nan_calibration=True):
        """
        Read a PollyXT netcdf file

        Parameters
            input_path: Which file to read
            start: Optionally, trim the file from this index
            end: Optionally, trim file until this index
            nan_calibration: If true, at calibration times the raw signal will be set to `np.nan`
        """

        # Read the file
        nc = Dataset(input_path, "r")

        # Read measurement time and trim accoarding to the user provided indices
        self.measurement_time = nc["measurement_time"][:]
        if start is None:
            start = 0
        if end is None:
            end = self.measurement_time.shape[0]

        self.measurement_time = self.measurement_time[start : end + 1]

        # Read the rest of the variables
        self.raw_signal = nc["raw_signal"][start : end + 1, :, :]
        self.raw_signal_swap = np.swapaxes(self.raw_signal, 1, 2)

        self.measurement_shots = nc["measurement_shots"][start : end + 1, :]
        self.zenith_angle = nc["zenithangle"][:]
        self.location_coordinates = nc["location_coordinates"][:]
        self.depol_cal_angle = nc["depol_cal_angle"][:]

        nc.close()

        # Optionally set calibration times to nan
        if nan_calibration:
            depol_cal_time = np.where(self.depol_cal_angle != 0.0)[0]
            if depol_cal_time.size != 0:
                self.raw_signal[depol_cal_time[0] : depol_cal_time[-1], :, :] == np.nan

        # Store some variables for easy access
        self.start_index = start
        self.end_index = end
        self.start_date = polly_date_to_datetime(self.measurement_time[0, :])
        self.end_date = polly_date_to_datetime(self.measurement_time[-1, :])
