'''
Routine for converting PollyXT files to SCC files
Authors:
- Anna Gialitaki <togialitaki@noa.gr>: Initial implementation
- Thanasis Georgiou <ageorgiou@noa.gr>: Polish
'''

from pathlib import Path
from typing import Tuple

from netCDF4 import Dataset
import numpy as np

from pollyxt_pipelines.polly_to_scc.pollyxt import PollyXTFile
from pollyxt_pipelines.locations import Location


def create_scc_netcdf(
    input_path: Path,
    output_path: Path,
    input_start: str,
    input_end: str,
    location: Location
) -> Tuple[str, Path]:
    '''
    Convert a PollyXT netCDF file to a SCC file.
    The time period that will be extracted in the output file can be determined using
    the `input_start` and `input_end` parameters. If the given time period does not
    exist in the file an exception will be thrown.

    Parameters
    ---
    - input_path (Path): Where to find the input file
    - output_path (Path): Where to store the produced netCDF file
    - input_start (str): Start of the output file in HH:MM format
    - input_end (str): End of the output file in HH:MM format

    Returns
    ---
    A tuple containing the measurement ID and the output path
    '''

    first_bin = 251

    # Read polly file and calculate measurement ID
    pf = PollyXTFile(input_path, input_start, input_end)
    measurement_id = pf.start_date.strftime(f'%Y%m%d${location.scc_code}%H')

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f'{measurement_id}.nc'
    nc = Dataset(output_filename, 'w', format='NETCDF3_CLASSIC')

    # Create dimensions (mandatory!)
    points = nc.createDimension('points', np.size(pf.raw_signal, axis=1))
    channels = nc.createDimension('channels', np.size(pf.raw_signal, axis=2))
    time = nc.createDimension('time', None)
    nb_of_time_scales = nc.createDimension('nb_of_time_scales', 1)
    scan_angles = nc.createDimension('scan_angles', 1)

    # Create Global Attributes (mandatory!)
    nc.Measurement_ID = measurement_id
    nc.RawData_Start_Date = pf.start_date.strftime('%Y%m%d')
    nc.RawData_Start_Time_UT = pf.start_date.strftime('%H%M%S')
    nc.RawData_Stop_Time_UT = pf.end_date.strftime('%H%M%S')

    # Create Global Attributes (optional)
    # TODO why are we setting the same values?
    nc.RawBck_Start_Date = nc.RawData_Start_Date
    nc.RawBck_Start_Time_UT = nc.RawData_Start_Time_UT
    nc.RawBck_Stop_Time_UT = nc.RawData_Stop_Time_UT
    nc.Sounding_File_Name = f'rs_{measurement_id}.nc'
    # TODO what is this?
    #nc.Overlap_File_Name = 'ov_' + selected_start.strftime('%Y%m%daky%H') + '.nc'

    # Create Variables. (mandatory)
    raw_data_start_time = nc.createVariable(
        'Raw_Data_Start_Time', 'i4', dimensions=('time', 'nb_of_time_scales'))
    raw_data_stop_time = nc.createVariable(
        'Raw_Data_Stop_Time', 'i4', dimensions=('time', 'nb_of_time_scales'))
    raw_lidar_data = nc.createVariable(
        'Raw_Lidar_Data', 'f8', dimensions=('time', 'channels', 'points'))
    channel_id = nc.createVariable('channel_ID', 'i4', dimensions=('channels'))
    id_timescale = nc.createVariable('id_timescale', 'i4', dimensions=('channels'))
    laser_pointing_angle = nc.createVariable(
        'Laser_Pointing_Angle', 'f8', dimensions=('scan_angles'))
    laser_pointing_angle_of_profiles = nc.createVariable(
        'Laser_Pointing_Angle_of_Profiles', 'i4', dimensions=('time', 'nb_of_time_scales'))
    laser_shots = nc.createVariable('Laser_Shots', 'i4', dimensions=('time', 'channels'))
    background_low = nc.createVariable('Background_Low', 'f8', dimensions=('channels'))
    background_high = nc.createVariable('Background_High', 'f8', dimensions=('channels'))
    molecular_calc = nc.createVariable('Molecular_Calc', 'i4', dimensions=())
    pol_calib_range_min = nc.createVariable('Pol_Calib_Range_Min', 'f8', dimensions=('channels'))
    pol_calib_range_max = nc.createVariable('Pol_Calib_Range_Max', 'f8', dimensions=('channels'))
    pressure_at_lidar_station = nc.createVariable('Pressure_at_Lidar_Station', 'f8', dimensions=())
    temperature_at_lidar_station = nc.createVariable(
        'Temperature_at_Lidar_Station', 'f8', dimensions=())
    lr_input = nc.createVariable('LR_Input', 'i4', dimensions=('channels'))

    # Fill Variables with Data. (mandatory)
    raw_data_start_time[:] = pf.measurement_time[:, 1] - pf.measurement_time[0, 1]
    raw_data_stop_time[:] = (pf.measurement_time[:, 1] - pf.measurement_time[0, 1]) + 30
    raw_lidar_data[:] = np.swapaxes(pf.raw_signal, 1, 2)
    channel_id[:] = np.array([493, 500, 497, 499, 494, 496, 498, 495, 501, 941, 940, 502])
    id_timescale[:] = np.zeros(np.size(pf.raw_signal, axis=2))
    laser_pointing_angle[:] = int(pf.zenith_angle.item(0))
    laser_pointing_angle_of_profiles[:] = np.zeros(np.size(pf.raw_signal, axis=0))
    laser_shots[:] = pf.measurement_shots[:]
    background_low[:] = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    background_high[:] = np.array([249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249])
    molecular_calc[:] = 1
    pol_calib_range_min[:] = []
    pol_calib_range_max[:] = []
    pressure_at_lidar_station[:] = 1008
    temperature_at_lidar_station[:] = 20
    lr_input[:] = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

    # Close the netCDF file.
    nc.close()

    return measurement_id, output_filename
