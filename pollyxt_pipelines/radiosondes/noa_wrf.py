"""
Functions related to reading and parsing of WRF radiosonde/profile files
Author: Thanasis Georgiou <ageorgiou@noa.gr>

The main function here is `read_wrf_daily_profile()` which you can use to read WRF profile files
into dataframes. The physical files are located using a *file provider*, a function which accepts
a location and a date to return the profile filepath. As of now, the only provider is
`folder_provider()`, which looks for profile files in the directory defined by the `WRF_PROFILES`
environmental variable.

Example usage
-------------
Make sure you set the environmental variable `WRF_PROFILES` to the directory containing the
profiles. For example, on Linux:

```
export WRF_PROFILES=/path/to/profiles
```

Then you can simply use `read_wrf_daily_profile()`:

```
rs = read_wrf_daily_profile('ANTIKYTHERA', date.fromisoformat('2020-01-01'))
```
"""

from datetime import date, datetime
from typing import Tuple, Union
from pathlib import Path

import pandas as pd
from rich.markdown import Markdown

from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.config import Config
from pollyxt_pipelines.radiosondes.exceptions import RadiosondeNotFound


def calculate_wrf_path(location: str, date: date) -> Path:
    """
    Provides radiosonde files from a directory. The storage directory is
    provided by the wrf.path config variable.

    Parameters
    ---
    - config (Config): The application's config
    - location (str): The location (i.e. city) to lookup
    - date (date): Which day to look for radiosonde files
    """

    # Get radiosonde storage location
    try:
        config = Config()
        radiosonde_storage = config["wrf"]["path"]
    except KeyError:
        raise ValueError(f"Config variable wrf.path is undefined. Can't locate radiosonde files")
    radiosonde_storage = Path(radiosonde_storage)

    # Calculate file path
    filename = f'{location.upper()}_{date.strftime("%d%m%Y")}'
    file_path = radiosonde_storage / filename

    return file_path


def read_wrf_daily_profile(
    location: Location, time_start: datetime, time_end: datetime
) -> Tuple[datetime, pd.DataFrame]:
    """
    Reads a WRF radiosonde/profile file for the given location and date and returns all
    profiles for that day in a DataFrame.

    Parameters:
        location: The location (i.e. station/city)
        time_start: Start of the data file
        time_end: End of the data file

    Returns:
        The timestamp of sounding, and the vertical profile in a DataFrame
    """

    # Floor minutes and seconds
    time_start = time_start.replace(minute=0, second=0)

    # Resolve the filename using the provider
    path = calculate_wrf_path(location.profile_name, time_start.date())
    if not path.is_file():
        raise RadiosondeNotFound(location, "noa_wrf", time_start, path)

    # Read the file and do some simple parsing
    columns = ["timestamp", "pressure", "temperature", "dew point", "rh", "altitude"]
    dtype = {col: float for col in columns}
    dtype["timestamp"] = str

    rs = pd.read_csv(path, header=0, names=columns, dtype=dtype)

    rs["timestamp"] = pd.to_datetime(rs["timestamp"].str.strip(), format="%Y-%m-%d_%H:%M:%S")
    rs = rs.rename(
        columns={
            "altitude": "Altitude",
            "temperature": "Temperature",
            "pressure": "Pressure",
            "rh": "RelativeHumidity",
        }
    )

    # Filter for the correct time
    mask = (rs["timestamp"] >= time_start) & (rs["timestamp"] < time_end)
    rs = rs.loc[mask]

    rs_timestamp = rs["timestamp"].iloc[0]
    return rs_timestamp, rs.loc[:, ["Altitude", "Temperature", "Pressure", "RelativeHumidity"]]
