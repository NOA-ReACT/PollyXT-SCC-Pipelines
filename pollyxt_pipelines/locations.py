'''
Contains information about common locations
'''

from typing import NamedTuple, Union

from pollyxt_pipelines.console import console


class Location(NamedTuple):
    '''
    Represents a physical location of PollyXT installation.
    '''

    name: str
    '''Location friendly name'''

    profile_name: str
    '''How are the WRF profile names prefixed'''

    scc_code: str
    '''SCC Station code'''

    lat: float
    '''Latitude of station'''

    lon: float
    '''Longitude of station'''

    altitude: float
    '''Altitude of station'''

    system_id_day: int
    '''SCC Lidar Configuration ID - Daytime'''

    system_id_night: int
    '''SCC Lidar Configuration ID - Nightime'''


LOCATION_ANTIKYTHERA = Location(
    name="Antikythera",
    profile_name="ANTIKYTHERA",
    scc_code="aky",
    lat=23.3100,
    lon=35.8600,
    altitude=0.1,
    system_id_day=437,
    system_id_night=438
)
'''Location at PANGEA observatory - Antikythera'''

LOCATION_FINOKALIA = Location(
    name="Finokalia",
    profile_name="FINOKALIA",
    scc_code='fik',
    lat=25.6698,
    lon=35.3377,
    altitude=0.1,
    system_id_day=186,
    system_id_night=302
)
'''Location at Finokalia (UoC)'''

LOCATIONS = [LOCATION_ANTIKYTHERA, LOCATION_FINOKALIA]
'''List of all known locations'''


def get_location_by_name(name: str) -> Union[Location, None]:
    '''
    Returns a location by its friendly name or `None` if it doesn't exist.
    '''

    for loc in LOCATIONS:
        if loc.name == name:
            return loc
    return None


def get_location_by_scc_code(code: str) -> Union[Location, None]:
    '''
    Returns a location by its SCC code or `None` if it doesn't exist.
    '''

    for loc in LOCATIONS:
        if loc.scc_code == code:
            return loc
    return None


def unknown_location_error(name: str):
    '''
    Prints an error message that the given location is not found, along with a
    list of known locations
    '''
    console.print(f'[error]Could not find location [/error]{name}[error].')
    console.print('Known locations:')
    for l in LOCATIONS:
        console.print(f'- {l.name}')
