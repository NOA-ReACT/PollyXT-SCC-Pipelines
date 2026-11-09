"""
Contains information about locations

Each location (i.e. SCC station) is defined in an .ini file. For some stations,
the .ini files are included with the software but custom locations can be defined.
"""

import io
import sys
from configparser import ConfigParser, Error as ConfigParserError, SectionProxy
from importlib.resources import read_text
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Union

from rich.markdown import Markdown
from rich.table import Table

from pollyxt_pipelines import config
from pollyxt_pipelines.console import console
from pollyxt_pipelines.enums import Wavelength
from pollyxt_pipelines.utils import ints_to_csv, parse_into_string_or_integer_list


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

    calibration_configuration_355nm: Optional[int]
    """SCC Lidar Configuration ID - Calibration (355 nm)"""

    calibration_configuration_532nm: Optional[int]
    """SCC Lidar Configuration ID - Calibration (532 nm)"""

    calibration_configuration_1064nm: Optional[int]
    """SCC Lidar Configuration ID - Calibration (532 nm)"""

    depol_calibration_zero_state: int
    """Value of `depol_cal_angle` when there is *no* calibration taking place"""

    channel_id: Union[List[int], List[str]]
    """Mapping of PollyXT Channels to SCC Channels
    Comma-separated list. The order of the list is the order of the channels in the
    PollyXT netCDF file.
    """

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

    total_channel_355_nm_idx: Optional[int]
    """Index in Polly netCDF file for the total channel (355nm)"""

    cross_channel_355_nm_idx: Optional[int]
    """Index in Polly netCDF file for the cross channel (355nm)"""

    total_channel_532_nm_idx: Optional[int]
    """Index in Polly netCDF file for the total channel (532nm)"""

    cross_channel_532_nm_idx: Optional[int]
    """Index in Polly netCDF file for the cross channel (532nm)"""

    total_channel_1064_nm_idx: Optional[int]
    """Index in Polly netCDF file for the total channel (1064nm)"""

    cross_channel_1064_nm_idx: Optional[int]
    """Index in Polly netCDF file for the cross channel (1064nm)"""

    calibration_355nm_total_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 355nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """

    calibration_355nm_cross_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 355nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """

    calibration_532nm_total_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 532nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """

    calibration_532nm_cross_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 532nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """
    calibration_1064nm_total_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 1064nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """

    calibration_1064nm_cross_channel_ids: Union[List[int], List[str]]
    """
    Calibration channel SCC IDs for 1064nm. Comma separated list. First value must be the
    +45° channel, second value must be the -45° channel.
    """

    sunrise_time: str
    """
    Sunrise time (HH:MM) or offset (minutes from calculated sunrise in +X or -X format,
    where X an integer)
    """

    sunset_time: str
    """
    Sunrise time (HH:MM) or offset (minutes from calculated sunrise in +X or -X format,
    where X an integer)
    """

    def print(self):
        """
        Prints this location as a Table in the terminal
        """

        table = Table(title=self.name)
        table.add_column("Key")
        table.add_column("Value")

        for key, value in self._asdict().items():
            if isinstance(value, list):
                value = ints_to_csv(value)
            table.add_row(key, str(value))

        console.print(table)

    def has_depol_channels(self) -> Dict[Wavelength, bool]:
        """
        Returns a dictionary of wavelengths to booleans, true if that corresponding
        wavelength has depolarization channels.
        """

        return {
            Wavelength.NM_355: self.calibration_configuration_355nm is not None
            and self.total_channel_355_nm_idx is not None
            and self.cross_channel_355_nm_idx is not None
            and self.calibration_355nm_total_channel_ids
            and self.calibration_355nm_cross_channel_ids,
            Wavelength.NM_532: self.calibration_configuration_532nm is not None
            and self.total_channel_532_nm_idx is not None
            and self.cross_channel_532_nm_idx is not None
            and self.calibration_532nm_total_channel_ids
            and self.calibration_532nm_cross_channel_ids,
            Wavelength.NM_1064: self.calibration_configuration_1064nm is not None
            and self.total_channel_1064_nm_idx is not None
            and self.cross_channel_1064_nm_idx is not None
            and self.calibration_1064nm_total_channel_ids
            and self.calibration_1064nm_cross_channel_ids,
        }


class InvalidLocationError(ValueError):
    """
    Raised when a section of a locations file cannot be turned into a `Location`.
    """

    def __init__(self, path: Optional[Path], section: str, reason: str):
        self.path = path
        self.section = section
        self.reason = reason
        where = f"{path}, " if path is not None else ""
        super().__init__(f"Invalid location ({where}section [{section}]): {reason}")


REQUIRED_LOCATION_KEYS = (
    "scc_code",
    "lat",
    "lon",
    "altitude_asl",
    "daytime_configuration",
    "nighttime_configuration",
    "depol_calibration_zero_state",
    "channel_id",
    "background_low",
    "background_high",
    "lr_input",
    "temperature",
    "pressure",
    "profile_name",
    "sounding_provider",
)
"""Keys that every location section must define"""


def location_from_section(name: str, section: SectionProxy) -> Location:
    """
    Create a Location from a ConfigParser Section (SectionProxy)

    Raises:
        InvalidLocationError: A required key is missing or a value cannot be parsed.
    """

    missing = [key for key in REQUIRED_LOCATION_KEYS if not section.get(key)]
    if missing:
        raise InvalidLocationError(
            None, name, f"missing required key(s): {', '.join(missing)}"
        )

    try:
        return _location_from_section(name, section)
    except (ValueError, TypeError, AttributeError, KeyError) as ex:
        raise InvalidLocationError(None, name, str(ex)) from ex


def _location_from_section(name: str, section: SectionProxy) -> Location:
    channel_id = parse_into_string_or_integer_list(section.get("channel_id"))
    background_low = [int(x.strip()) for x in section.get("background_low").split(",")]
    background_high = [
        int(x.strip()) for x in section.get("background_high").split(",")
    ]
    lr_input = [int(x.strip()) for x in section.get("lr_input").split(",")]

    calibration_355nm_total_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_355nm_total_channel_ids")
    )
    calibration_355nm_cross_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_355nm_cross_channel_ids")
    )

    calibration_532nm_total_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_532nm_total_channel_ids")
    )
    calibration_532nm_cross_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_532nm_cross_channel_ids")
    )

    calibration_1064nm_total_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_1064nm_total_channel_ids")
    )
    calibration_1064nm_cross_channel_ids = parse_into_string_or_integer_list(
        section.get("calibration_1064nm_cross_channel_ids")
    )

    return Location(
        name=name,
        scc_code=section["scc_code"],
        lat=section.getfloat("lat"),
        lon=section.getfloat("lon"),
        altitude_asl=section.getfloat("altitude_asl"),
        daytime_configuration=section.getint("daytime_configuration"),
        nighttime_configuration=section.getint("nighttime_configuration"),
        calibration_configuration_355nm=section.getint(
            "calibration_configuration_355nm", None
        ),
        calibration_configuration_532nm=section.getint(
            "calibration_configuration_532nm", None
        ),
        calibration_configuration_1064nm=section.getint(
            "calibration_configuration_1064nm", None
        ),
        depol_calibration_zero_state=section.getint(
            "depol_calibration_zero_state",
        ),
        channel_id=channel_id,
        background_low=background_low,
        background_high=background_high,
        lr_input=lr_input,
        temperature=section.getint("temperature"),
        pressure=section.getint("pressure"),
        total_channel_355_nm_idx=section.getint("total_channel_355_nm_idx", None),
        cross_channel_355_nm_idx=section.getint("cross_channel_355_nm_idx", None),
        total_channel_532_nm_idx=section.getint("total_channel_532_nm_idx", None),
        cross_channel_532_nm_idx=section.getint("cross_channel_532_nm_idx", None),
        total_channel_1064_nm_idx=section.getint("total_channel_1064_nm_idx", None),
        cross_channel_1064_nm_idx=section.getint("cross_channel_1064_nm_idx", None),
        calibration_355nm_total_channel_ids=calibration_355nm_total_channel_ids,
        calibration_355nm_cross_channel_ids=calibration_355nm_cross_channel_ids,
        calibration_532nm_total_channel_ids=calibration_532nm_total_channel_ids,
        calibration_532nm_cross_channel_ids=calibration_532nm_cross_channel_ids,
        calibration_1064nm_total_channel_ids=calibration_1064nm_total_channel_ids,
        calibration_1064nm_cross_channel_ids=calibration_1064nm_cross_channel_ids,
        sounding_provider=section["sounding_provider"],
        profile_name=section["profile_name"],
        sunrise_time=section.get("sunrise_time", "0"),
        sunset_time=section.get("sunset_time", "0"),
    )


def _locations_from_parser(
    parser: ConfigParser, path: Optional[Path]
) -> Dict[str, Location]:
    locations = {}
    for name in parser.sections():
        try:
            locations[name] = location_from_section(name, parser[name])
        except InvalidLocationError as ex:
            raise InvalidLocationError(path, ex.section, ex.reason) from ex
    return locations


def read_locations_file(path: Path) -> Dict[str, Location]:
    """
    Reads the locations defined in one `.ini` file, and only that file.

    Parameters:
        path: The locations file

    Returns:
        A dictionary of location name to `Location`

    Raises:
        FileNotFoundError: The file does not exist
        InvalidLocationError: A section is not a valid location. Sections are never skipped.
    """

    path = Path(path)
    parser = ConfigParser()
    try:
        with open(path, "r") as file:
            parser.read_file(file)
    except ConfigParserError as ex:
        raise InvalidLocationError(path, "?", f"could not parse file: {ex}") from ex

    return _locations_from_parser(parser, path)


def _builtin_locations() -> Dict[str, Location]:
    parser = ConfigParser()
    parser.read_file(
        io.StringIO(read_text("pollyxt_pipelines.locations", "locations.ini"))
    )
    return _locations_from_parser(parser, Path("<built-in locations.ini>"))


def _config_locations() -> Dict[str, Location]:
    # The config files are read together, so a later file can override single keys
    # of a section from an earlier one.
    paths = [path / "locations.ini" for path in config.config_paths()]
    existing = [path for path in paths if path.is_file()]
    parser = ConfigParser()
    parser.read(existing)
    return _locations_from_parser(parser, existing[-1] if len(existing) == 1 else None)


def read_locations(extra_paths: Sequence[Path] = ()) -> Dict[str, Location]:
    """
    Reads all known locations into a dictionary: name -> Location

    The sources are read in this order, and a later definition of a location replaces an
    earlier one:

    1. The built-in `locations.ini`
    2. `locations.ini` in each config directory (see `config.config_paths()`)
    3. Each file in `extra_paths`, in order. These must exist.

    Raises:
        InvalidLocationError: Any section in any of the files is not a valid location
    """

    locations = _builtin_locations()
    locations.update(_config_locations())
    for path in extra_paths:
        locations.update(read_locations_file(path))

    return locations


def _read_cli_locations() -> Dict[str, Location]:
    try:
        return read_locations()
    except InvalidLocationError as ex:
        console.print(f"Could not load locations: {ex}")
        console.print("Check the following files:")
        for path in config.config_paths():
            if (path / "locations.ini").is_file():
                console.print(f"\t-{path / 'locations.ini'}")
        sys.exit(1)


LOCATIONS = _read_cli_locations()
"""All known locations (built-in and config directories), read at import. Used by the CLI."""


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
    error = (
        f"[error]Could not find location[/error]{name}[error]\nKnown locations:\n\n."
    )
    for l in LOCATIONS:
        error += f"* {l.name}"

    console.print(Markdown(error))
