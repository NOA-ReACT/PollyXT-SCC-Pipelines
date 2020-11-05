'''
Contains information about common locations
'''

from typing import NamedTuple


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


'''Location at PANGEA observatory - Antikythera'''
LOCATION_ANTIKYTHERA = Location(
    name="Antikythera",
    profile_name="ANTIKYTHERA",
    scc_code="aky",
    lat=23.3100,  # TODO Verify with lidar team
    lon=35.8612
)

'''Location at Finokalia (UoC)'''
LOCATION_FINOKALIA = Location(
    name="Finokalia",
    profile_name="FINOKALIA",
    scc_code='fik',
    lat=25.6698,
    lon=35.3377
)
