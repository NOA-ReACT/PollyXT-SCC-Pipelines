'''
Routines to create SCC radiosonde files.
'''

from typing import Tuple
from pathlib import Path

import pandas as pd
from netCDF4 import Dataset

from pollyxt_pipelines.locations import Location

'''
This dictionary contains the mapping from SCC variable names to WRF profile column names, as they
are returned by `read_wrf_daily_profile()`. The keys are SCC names and the values are WRF names.
'''
scc_to_wrf = {
    'Altitude': 'altitude',
    'Temperature': 'temperature',
    'Pressure': 'pressure',
    'RelativeHumidity': 'rh'
}


def create_radiosonde_netcdf(
        profile: pd.DataFrame,
        location: Location,
        netcdf_path: Path):
    '''
    Creates a netCDF dataset in the SCC radiosonde format from a given profile.
    The variable names of SCC radiosonde files are matched to WRF profile columns using the
    `scc_to_wrf` dicitonary defined above.

    Parameters
    ---
    - profile (DataFrame): The profile to convert into a netCDF. You should use
                           `read_wrf_daily_profile()` to read these files and then split into profiles
                           using `groupby()`.
    - location (Location): Profile location
    - netcdf_path (Path): Where to store the netCDF file
    '''

    # Ensure only one profile is inside the dataframe
    if len(profile['timestamp'].unique()) > 1:
        raise ValueError(
            'Profile dataframe contains more than one profiles (more than one unique timestamps)!')

    timestamp = profile.iloc[0, 0]

    # Create the netCDF file and add variables from the dataframe
    nc = Dataset(netcdf_path, 'w', format='NETCDF3_CLASSIC')
    nc.createDimension('points', profile.shape[0])

    for name in scc_to_wrf.keys():
        v = nc.createVariable(name, 'f8', dimensions=('points'))
        v[:] = profile[scc_to_wrf[name]]

    # Add global attributes
    nc.Latitude_degrees_north = location.lat
    nc.Longitude_degrees_east = location.lon
    nc.Altitude_meter_asl = location.altitude_asl
    nc.Sounding_Start_Date = timestamp.strftime('%Y%m%d')
    nc.Sounding_Start_Time_UT = timestamp.strftime('%H%M%S')

    nc.close()
