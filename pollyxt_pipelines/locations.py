'''
Contains information about common locations
'''

from typing import NamedTuple


class Location(NamedTuple):
    '''
    Represents a physical location of PollyXT installation.
    '''
    name: str
    profile_name: str
    scc_code: str
    lat: float
    lon: float


LOCATION_ANTIKYTHERA = Location(
    name="Antikythera",
    profile_name="ANTIKYTHERA",
    scc_code="aky",
    lat=23.3100,  # TODO Verify with lidar team
    lon=35.8612
)

LOCATION_FINOKALIA = Location(
    name="Finokalia",
    scc_code='fik',
    lat=25.6698,
    lon=35.3377
)
