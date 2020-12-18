'''
Contains information about locations

Each location (i.e. SCC station) is defined in an .ini file. For some stations,
the .ini files are included with the software but custom locations can be defined.
'''

import io
from pathlib import Path
from importlib.resources import read_text
from configparser import ConfigParser, SectionProxy
from typing import NamedTuple, Union, Dict

from rich.markdown import Markdown
from rich.table import Table

from pollyxt_pipelines.console import console
from pollyxt_pipelines import config


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

    def print(self):
        '''
        Prints this location as a Table in the terminal
        '''

        table = Table(title=self.name)
        table.add_column("Key")
        table.add_column("Value")

        table.add_row("profile_name", self.profile_name)
        table.add_row("scc_code", self.scc_code)
        table.add_row("lat", str(self.lat))
        table.add_row("lon", str(self.lon))
        table.add_row("system_id_day", str(self.system_id_day))
        table.add_row("system_id_night", str(self.system_id_night))

        console.print(table)


def location_from_section(name: str, section: SectionProxy) -> Location:
    '''
    Create a Location from a ConfigParser Section (SectionProxy)
    '''

    return Location(
        name=name,
        profile_name=section["profile_name"],
        scc_code=section["scc_code"],
        lat=section.getfloat("lat"),
        lon=section.getfloat("lon"),
        altitude=section.getfloat("altitude"),
        system_id_day=section.getint("system_id_day"),
        system_id_night=section.getint("system_id_night")
    )


def read_locations() -> Dict[str, Location]:
    '''
    Reads all built-in and custom locations into a dictionary: name -> Location
    '''

    locations = {}

    # Read built-in locations
    locations_buffer = io.StringIO(
        read_text("pollyxt_pipelines.locations", "locations.ini"))
    locations_config = ConfigParser()
    locations_config.read_file(locations_buffer)

    for name in locations_config.sections():
        section = locations_config[name]
        locations[name] = location_from_section(name, section)

    # Read custom locations
    location_path = Path(config.config_paths()[-1]) / 'locations.ini'
    locations_config = ConfigParser()
    locations_config.read(location_path)

    for name in locations_config.sections():
        section = locations_config[name]
        locations[name] = location_from_section(name, section)

    return locations


LOCATIONS = read_locations()
'''List of all known locations'''


def get_location_by_scc_code(code: str) -> Union[Location, None]:
    '''
    Returns a location by its SCC code or `None` if it doesn't exist.
    '''

    for loc in LOCATIONS.items():
        if loc.scc_code == code:
            return loc
    return None


def unknown_location_error(name: str):
    '''
    Prints an error message that the given location is not found, along with a
    list of known locations
    '''
    error = f'[error]Could not find location[/error]{name}[error]\nKnown locations:\n\n.'
    for l in LOCATIONS:
        error += f'* {l.name}'

    console.print(Markdown(error))
