'''
Contains information about common locations
'''

from typing import NamedTuple, Union


class Location(NamedTuple):
    '''
    Represents a physical location of PollyXT installation.
    '''

    '''Location friendly name'''
    name: str
    '''How are the WRF profile names prefixed'''
    profile_name: str
    '''SCC Station code'''
    scc_code: str
    '''Latitude of station'''
    lat: float
    '''Longitude of station'''
    lon: float
    '''Altitude of station'''
    altitude: float


'''Location at PANGEA observatory - Antikythera'''
LOCATION_ANTIKYTHERA = Location(
    name="Antikythera",
    profile_name="ANTIKYTHERA",
    scc_code="aky",
    lat=23.3100,
    lon=35.8600,
    altitude=0.1
)

'''Location at Finokalia (UoC)'''
LOCATION_FINOKALIA = Location(
    name="Finokalia",
    profile_name="FINOKALIA",
    scc_code='fik',
    lat=25.6698,
    lon=35.3377,
    altitude=0.1
)

LOCATIONS = [LOCATION_ANTIKYTHERA, LOCATION_FINOKALIA]


def get_location_by_name(name: str) -> Union[Location, None]:
    '''
    Returns a location by it's friendly name or `None` if it doesn't exist.
    '''

    for loc in LOCATIONS:
        if loc.name == name:
            return loc
    return None
