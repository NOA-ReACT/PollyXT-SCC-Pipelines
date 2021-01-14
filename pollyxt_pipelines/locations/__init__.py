"""
Contains information about locations

Each location (i.e. SCC station) is defined in an .ini file. For some stations,
the .ini files are included with the software but custom locations can be defined.
"""

import io
from pathlib import Path
from importlib.resources import read_text
from configparser import ConfigParser, SectionProxy
from typing import NamedTuple, Union, Dict, List

from rich.markdown import Markdown
from rich.table import Table

from pollyxt_pipelines.console import console
from pollyxt_pipelines import config
from pollyxt_pipelines.utils import ints_to_csv


class Location(NamedTuple):
    """
    Represents a physical location of PollyXT installation.
    """

    name: str
    """Location friendly name"""

    profile_name: str
    """How are the WRF profile names prefixed"""

    sounding_provider: str
    """Which radiosonde provider to use"""

    scc_code: str
    """SCC Station code"""

    lat: float
    """Latitude of station"""

    lon: float
    """Longitude of station"""

    altitude_asl: float
    """Altitude of station"""

    daytime_configuration: int
    """SCC Lidar Configuration ID - Daytime"""

    nighttime_configuration: int
    """SCC Lidar Configuration ID - Nightime"""

    channel_id: List[int]
    """List of channel IDs (for SCC `channel_ID` variable)"""

    background_low: List[int]
    """Value for the `Background_Low` variable"""

    background_high: List[int]
    """Value for the `Background_High` variable"""

    lr_input: List[int]
    """Value for the `lr_input` variable"""

    temperature: int
    """Temperature at the lidar station (`Temperature_at_Lidar_Station` variable)"""

    pressure: int
    """Pressure at the lidar station (`Pressure_at_Lidar_Station` variable)"""

    total_channel_355_nm: int
    """Index for the total channel (355nm)"""

    cross_channel_355_nm: int
    """Index for the cross channel (355nm)"""

    total_channel_532_nm: int
    """Index for the total channel (532nm)"""

    cross_channel_532_nm: int
    """Index for the cross channel (532nm)"""

    calibration_355nm_channel_ids: List[int]
    """
    Calibration channel IDs for 355nm in this order:
    - 355_plus_45_transmitted
    - 355_plus_45_reflected
    - 355_minus_45_transmitted
    - 355_minus_45_reflected
    """

    calibration_532nm_channel_ids: List[int]
    """
    Calibration channel IDs for 532nm in this order:
    - 532_plus_45_transmitted
    - 532_plus_45_reflected
    - 532_minus_45_transmitted
    - 532_minus_45_reflected
    """

    def print(self):
        """
        Prints this location as a Table in the terminal
        """

        table = Table(title=self.name)
        table.add_column("Key")
        table.add_column("Value")

        table.add_row("scc_code", self.scc_code)
        table.add_row("lat", str(self.lat))
        table.add_row("lon", str(self.lon))
        table.add_row("daytime_configuration", str(self.daytime_configuration))
        table.add_row("nighttime_configuration", str(self.nighttime_configuration))
        table.add_row("channel_id", ints_to_csv(self.channel_id))
        table.add_row("background_low", ints_to_csv(self.background_low))
        table.add_row("background_high", ints_to_csv(self.background_high))
        table.add_row("lr_input", ints_to_csv(self.lr_input))
        table.add_row("temperature", str(self.temperature))
        table.add_row("altitude_asl", str(self.altitude_asl))
        table.add_row("total_channel_355_nm", str(self.total_channel_355_nm))
        table.add_row("cross_channel_355_nm", str(self.cross_channel_355_nm))
        table.add_row("total_channel_532_nm", str(self.total_channel_532_nm))
        table.add_row("cross_channel_532_nm", str(self.cross_channel_532_nm))
        table.add_row(
            "calibration_355nm_channel_ids", ints_to_csv(self.calibration_355nm_channel_ids)
        )
        table.add_row(
            "calibration_532nm_channel_ids", ints_to_csv(self.calibration_532nm_channel_ids)
        )
        table.add_row("profile_name", self.profile_name)
        table.add_row("sounding_provider", self.sounding_provider)

        console.print(table)


def location_from_section(name: str, section: SectionProxy) -> Location:
    """
    Create a Location from a ConfigParser Section (SectionProxy)
    """

    channel_id = [int(x.strip()) for x in section.get("channel_id").split(",")]
    background_low = [int(x.strip()) for x in section.get("background_low").split(",")]
    background_high = [int(x.strip()) for x in section.get("background_high").split(",")]
    lr_input = [int(x.strip()) for x in section.get("lr_input").split(",")]

    calibration_355nm_channel_ids = [
        int(x.strip()) for x in section.get("calibration_355nm_channel_ids").split(",")
    ]
    calibration_532nm_channel_ids = [
        int(x.strip()) for x in section.get("calibration_532nm_channel_ids").split(",")
    ]

    return Location(
        name=name,
        scc_code=section["scc_code"],
        lat=section.getfloat("lat"),
        lon=section.getfloat("lon"),
        altitude_asl=section.getfloat("altitude_asl"),
        daytime_configuration=section.getint("daytime_configuration"),
        nighttime_configuration=section.getint("nighttime_configuration"),
        channel_id=channel_id,
        background_low=background_low,
        background_high=background_high,
        lr_input=lr_input,
        temperature=section.getint("temperature"),
        pressure=section.getint("pressure"),
        total_channel_355_nm=section.getint("total_channel_355_nm"),
        cross_channel_355_nm=section.getint("cross_channel_355_nm"),
        total_channel_532_nm=section.getint("total_channel_532_nm"),
        cross_channel_532_nm=section.getint("cross_channel_532_nm"),
        calibration_355nm_channel_ids=calibration_355nm_channel_ids,
        calibration_532nm_channel_ids=calibration_532nm_channel_ids,
        sounding_provider=section["sounding_provider"],
        profile_name=section["profile_name"],
    )


def read_locations() -> Dict[str, Location]:
    """
    Reads all built-in and custom locations into a dictionary: name -> Location
    """

    locations = {}

    # Read built-in locations
    locations_buffer = io.StringIO(read_text("pollyxt_pipelines.locations", "locations.ini"))
    locations_config = ConfigParser()
    locations_config.read_file(locations_buffer)

    for name in locations_config.sections():
        section = locations_config[name]
        locations[name] = location_from_section(name, section)

    # Read custom locations
    location_path = Path(config.config_paths()[-1]) / "locations.ini"
    locations_config = ConfigParser()
    locations_config.read(location_path)

    for name in locations_config.sections():
        section = locations_config[name]
        locations[name] = location_from_section(name, section)

    return locations


LOCATIONS = read_locations()
"""List of all known locations"""


def get_location_by_scc_code(code: str) -> Union[Location, None]:
    """
    Returns a location by its SCC code or `None` if it doesn't exist.
    """

    for loc in LOCATIONS.values():
        if loc.scc_code == code:
            return loc
    return None


def unknown_location_error(name: str):
    """
    Prints an error message that the given location is not found, along with a
    list of known locations
    """
    error = f"[error]Could not find location[/error]{name}[error]\nKnown locations:\n\n."
    for l in LOCATIONS:
        error += f"* {l.name}"

    console.print(Markdown(error))
