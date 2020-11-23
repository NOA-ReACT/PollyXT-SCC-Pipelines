'''
Routines related to PollyXT files
'''

from pathlib import Path
from typing import Tuple, Union
from datetime import datetime, timedelta

import numpy as np
from netCDF4 import Dataset


def get_measurement_period(input: Union[Path, Dataset, np.ndarray]) -> Tuple[datetime, datetime]:
    '''
    Return the measurement time (i.e. start and end times) from a PollyXT file.

    Parameters:
        input: Either a path to a PollyXT netCDF file, an opened netCDF dataset or the
            `measurement_time` variable.

    Returns:
        A tuple containing the start and end dates.
    '''

    # Read `measurement_time` variable, a bit different for each source
    if isinstance(input, Path):
        nc = Dataset(input, 'r')
        measurement_time = nc['measurement_time'][:]
        nc.close()
    elif isinstance(input, Dataset):
        measurement_time = input['measurement_time'][:]
    elif isinstance(input, np.ndarray):
        measurement_time = input
    else:
        raise ValueError(
            f'Parameter `input` must be a Path, a Dataset (netCDF) or a numpy array, not {type(input)}')

    # Do some sanity checks on its shape
    shape = measurement_time.shape
    assert(len(shape) == 2)
    assert(shape[1] == 2)

    # Parse start/end times
    day_str = str(measurement_time[0, 0])
    date = datetime.strptime(day_str, '%Y%m%d')
    start = date + timedelta(seconds=int(measurement_time[0, 1]))
    end = date + timedelta(seconds=int(measurement_time[-1, 1]))

    return start, end


def find_time_indices(
        measurement_time: np.ndarray, start: datetime, end: datetime) -> Tuple[int, int]:
    '''
    Given the `measurement_time` array from a PollyXT netCDF file and a time period (`start` and
    `end` in HH:MM format), this function returns the indices of the time period in the array.

    The `measurement_time` array has two columns, the first contains the date in YYYYMMDD format
    and the second column contains each measurement's delta from the date, in seconds (!).
    '''

    measurement_start, measurement_end = get_measurement_period(measurement_time)

    # Do some validation on the dates
    if start > end:
        raise ValueError(f'Selected start ({start}) is after selected end ({end})!')
    if start < measurement_start:
        mstart = measurement_start.strftime('%H:%M')
        raise ValueError(f'Selected start ({start}) is before file start ({mstart})!')
    if start > measurement_end:
        mend = measurement_end.strftime('%H:%M')
        raise ValueError(f'Selected end ({end}) is after file end ({mend})!')

    # Find indices
    dt1 = (start - measurement_start).seconds
    dt2 = (end - measurement_start).seconds

    index_start = (dt1 // 30)
    index_end = (dt2 // 30)

    return (index_start, index_end)


class PollyXTFile():
    '''
    Reads the variables of interest from a PollyXT netCDF file.
    '''

    path: Path
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
    depol_cal_angle:  np.ndarray

    def __init__(self, input_path: Path, start: datetime, end: datetime, nan_calibration=True):
        '''
        Read a PollyXT netcdf file

        Parameters
            input_path: Which file to read
            start: Trim file from this time and onwards (HH:MM)
            end: Trim file until this time (HH:MM)
            nan_calibration: If true, at calibration times the raw signal will be set to `np.nan`
        '''
        self.path = input_path

        # Read the file
        nc = Dataset(self.path, 'r')

        # Read measurement time and trim accoarding to the user provided time period
        self.measurement_time = nc['measurement_time'][:]
        index_start, index_end = find_time_indices(
            self.measurement_time, start, end)
        self.measurement_time = self.measurement_time[index_start:index_end]

        # Read the rest of the variables
        self.raw_signal = nc['raw_signal'][index_start:index_end, :, :]
        self.raw_signal_swap = np.swapaxes(self.raw_signal, 1, 2)

        self.measurement_shots = nc['measurement_shots'][index_start:index_end, :]
        self.zenith_angle = nc['zenithangle'][:]
        self.location_coordinates = nc['location_coordinates'][:]
        self.depol_cal_angle = nc['depol_cal_angle'][:]

        nc.close()

        # Optionally set calibration times to nan
        if nan_calibration:
            depol_cal_time = np.where(self.depol_cal_angle != 0.0)[0]
            if depol_cal_time.size != 0:
                self.raw_signal[depol_cal_time[0]:depol_cal_time[-1], :, :] == np.nan

        # Store some variables for easy access
        self.start_index = index_start
        self.end_index = index_end
        self.start_date = start
        self.end_date = end
