'''
Routines related to PollyXT files
'''

from pathlib import Path
from typing import Tuple
from datetime import datetime, timedelta

import numpy as np
from netCDF4 import Dataset
from numpy.core.defchararray import split
from numpy.lib.arraypad import pad


def find_time_indices(
        measurement_time: np.ndarray, start: str, end: str) -> Tuple[int, int]:
    '''
    Given the `measurement_time` array from a PollyXT netCDF file and a time period (`start` and
    `end` in HH:MM format), this function returns the indices of the time period in the array.

    The `measurement_time` array has two columns, the first contains the date in YYYYMMDD format
    and the second column contains each measurement's delta from the date, in seconds (!).
    '''

    # Some assertions regrading `measurement_time`'s shape
    shape = measurement_time.shape
    assert(len(shape) == 2)
    assert(shape[1] == 2)

    # Parse the file's first and last timestamp into datetimes
    day_str = str(measurement_time[0, 0])
    date = datetime.strptime(day_str, '%Y%m%d')
    measurement_start = date + timedelta(seconds=int(measurement_time[0, 1]))
    measurement_end = date + timedelta(seconds=int(measurement_time[-1, 1]))

    # Convert user provided start/end times to datetimes
    selected_start = datetime.strptime(f'{day_str} {start}', '%Y%m%d %H:%M')
    selected_end = datetime.strptime(f'{day_str} {start}', '%Y%m%d %H:%M')

    # Do some validation on the dates
    if selected_start > selected_end:
        raise ValueError(f'Selected start ({start}) is after selected end ({end})!')
    if selected_start < measurement_start:
        mstart = measurement_start.strftime('%H:%M')
        raise ValueError(f'Selected start ({start}) is before file start ({mstart})!')
    if selected_end > measurement_end:
        mend = measurement_end.strftime('%H:%M')
        raise ValueError(f'Selected end ({end}) is after file end ({mend})!')

    # Find indices
    dt1 = (selected_start - measurement_start).seconds
    dt2 = (selected_end - measurement_start).seconds

    index_start = (dt1 // 30)
    index_end = (dt2 // 30)

    return (index_start, measurement_start, index_end, measurement_end)


class PollyXTFile():
    '''
    Reads the variables of interest from a PollyXT netCDF file.
    '''

    path: Path
    start_str: str
    start_date: datetime
    start_index: int
    end_str: str
    end_index: int
    end_date: datetime

    raw_signal: np.ndarray
    raw_signal_swap: np.ndarray

    measurement_time: np.ndarray
    measurement_shots: np.ndarray
    zenith_angle: np.ndarray
    location_coordinates: np.ndarray
    depol_cal_angle:  np.ndarray

    def __init__(self, input_path: Path, start: str, end: str):
        '''
        Read a PollyXT netcdf file

        Parameters
        ---
        input_path (str): Which file to read
        start (str): Trim file from this time and onwards (HH:MM)
        end (str): Trim file until this time (HH:MM)
        '''
        self.path = input_path
        self.start_str = start
        self.end_str = end

        # Read the file
        nc = Dataset(self.path, 'r')

        # Read measurement time and trim accoarding to the user provided time period
        self.measurement_time = nc['measurement_time'][:]
        index_start, start_date, index_end, date_end = find_time_indices(
            self.measurement_time, self.start_time_str, self.end_time_str)
        self.measurement_time = self.measurement_time[index_start:index_end]

        # Read the rest of the variables
        self.raw_signal = nc['raw_signal'][index_start:index_end, :, :]
        self.raw_signal_swap = np.swapaxes(self.raw_signal, 1, 2)

        self.measurement_shots = nc['measurement_shots'][index_start:index_end, :]
        self.zenith_angle = nc['zenithangle'][:]
        self.location_coordinates = nc['location_coordinates'][:]
        self.depol_cal_angle = nc['depol_cal_angle'][:]

        nc.close()

        # Store some variables for easy access
        self.start_index = index_start
        self.end_index = index_end
        self.start_date = start_date
        self.date_end = date_end
