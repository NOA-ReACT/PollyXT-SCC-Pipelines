"""
Routines to create SCC radiosonde files.
"""

from datetime import datetime
from pathlib import Path

from netCDF4 import Dataset
import pandas as pd

from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.radiosondes.noa_wrf import read_wrf_daily_profile


RadiosondeProviders = {"wrf_noa": read_wrf_daily_profile}
"""
Set of functions that can provide Radiosonde data. The call signature should be:

    provider(location: Location, time_start: datetime, time_end: datetime) -> Tuple[datetime, pd.DataFrame]

This means your function will receive the application's confg, the current station/location
and the time period of the file being created and should return the timestamp of the
sounding and a pandas Dataframe with the following columns:
- Altitude
- Temperature
- Pressure
- RelativeHumidity
"""


def write_radiosonde_netcdf(
    profile: pd.DataFrame, location: Location, sounding_start: datetime, path: Path
):
    """
    Write a profile to a SCC-formatted netCDF file

    Parameters:
        profile: The profile to write as a pandas DataFrame
        location: Location of the station, used for metadata
        path: Where to save the file
    """

    nc = Dataset(path, "w")
    nc.createDimension("points", profile.shape[0])

    for name in ["Altitude", "Temperature", "Pressure", "RelativeHumidity"]:
        v = nc.createVariable(name, "f8", dimensions=("points"), zlib=True)
        v[:] = profile[name]

    # Add global attributes
    nc.Latitude_degrees_north = location.lat
    nc.Longitude_degrees_east = location.lon
    nc.Altitude_meter_asl = location.altitude_asl
    nc.Sounding_Start_Date = sounding_start.strftime("%Y%m%d")
    nc.Sounding_Start_Time_UT = sounding_start.strftime("%H%M%S")

    nc.close()


def create_radiosonde_netcdf(
    provider_name: str,
    location: Location,
    time_start: datetime,
    time_end: datetime,
    netcdf_path: Path,
):
    """
    Creates a netCDF dataset in the SCC radiosonde format from a given profile.
    The variable names of SCC radiosonde files are matched to WRF profile columns using the
    `scc_to_wrf` dicitonary defined above.

    Parameters:
        provider_name: The name of the provider function to fetch radiosonde data. Check
                       the `RadiosondeProviders` dictionary to see what is available.
        location: Location/station to create
        time_start: First timestamp of the corresponding data netCDF
        time_end: Last timestamp of the corresponding data netCDF
        netcdf_path: Where to store the netCDF file
    """

    # Grab the profile from the providers
    provider = RadiosondeProviders.get(provider_name, None)
    if provider is None:
        raise ValueError(f"Unknown radiosonde provider {provider_name}")

    sounding_start, profile = provider(location, time_start, time_end)

    write_radiosonde_netcdf(profile, location, sounding_start, netcdf_path)
