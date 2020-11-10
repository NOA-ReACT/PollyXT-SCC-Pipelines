'''
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

'''

from datetime import date
import errno
from pathlib import Path
import os

import pandas as pd

from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.config import Config


def folder_provider(config: Config, location: str, date: date) -> Path:
    '''
    Provides radiosonde files from a directory. The storage directory is
    provided by the wrf.path config variable.

    Parameters
    ---
    - config (Config): The application's config
    - location (str): The location (i.e. city) to lookup
    - date (date): Which day to look for radiosonde files
    '''

    # Get radiosonde storage location
    try:
        radiosonde_storage = config['wrf']['path']
    except KeyError:
        raise ValueError(
            f'Config variable wrf.path is undefined. Can\'t locate radiosonde files')
    radiosonde_storage = Path(radiosonde_storage)

    # Calculate file path and check if it exists
    filename = f'{location.upper()}_{date.strftime("%d%m%Y")}'
    file_path = radiosonde_storage / filename

    if not file_path.is_file():
        raise FileNotFoundError(
            errno.ENOENT,
            f'WRF Profile file not found!',
            file_path)

    return file_path


def read_wrf_daily_profile(
        config: Config, location: Location, date: date, provider=folder_provider) -> pd.DataFrame:
    '''
        Reads a WRF radiosonde/profile file for the given location and date and returns all
        profiles for that day in a DataFrame.

        Parameters
        ---
        - config (Config): The application's configuration
        - location (Locatiion): The location (i.e. station/city) to lookup
        - date (date): Which day to look for radiosonde files
        - provider: This function, also accepting location and date, will be used to resolve the
                    location of the radiosonde files. The default provider simply looks them up
                    in a directory but others can be used to fetch files from servers, etc.

        Returns
        ---
        The radiosondes for the day in one DataFrame. The index is the timestamp, use it to get
        the different profiles from the dataframe.
        '''

    # Resolve the filename using the provider
    path = provider(config, location.profile_name, date)

    # Read the file and do some simple parsing
    columns = ['timestamp', 'pressure',
               'temperature', 'dew point', 'rh', 'altitude']
    dtype = {col: float for col in columns}
    dtype['timestamp'] = str

    rs = pd.read_csv(path, header=0, names=columns, dtype=dtype)
    rs['timestamp'] = pd.to_datetime(rs['timestamp'].str.strip(), format="%Y-%m-%d_%H:%M:%S")

    return rs
