"""Wrapper around `astral` for sun info"""

from dataclasses import dataclass
from typing import Optional
import datetime as dt

from astral import LocationInfo
from astral.sun import sunrise, sunset

from pollyxt_pipelines.locations import Location


@dataclass
class SunInfo:
    """Information about sun position on a given day"""

    sunrise_time: Optional[dt.datetime]
    """The sunrise time, none if the sun never rises"""

    sunset_time: Optional[dt.datetime]
    """The sunset time, none if the sun never sets"""

    always_up: bool
    """True if the sun is always up"""

    always_down: bool
    """True if the sun is always down"""


def get_sun_times(loc: Location, date: dt.datetime) -> SunInfo:
    """
    For the given location and date, get the sunrise and sunset times for today.
    """

    always_up = False
    always_down = False

    sun_locinfo = LocationInfo(
        loc.name, "", timezone="UTC", latitude=loc.lat, longitude=loc.lon
    )

    # Get sunrise and sunset times
    try:
        sunrise_time = sunrise(sun_locinfo.observer, date)
        sunset_time = sunset(sun_locinfo.observer, date)
    except ValueError as ex:
        sunrise_time = None
        sunset_time = None
        if "Sun is always above the horizon on this day" in ex.args[0]:
            always_up = True
        elif "Sun is always below the horizon on this day" in ex.args[0]:
            always_down = True
        else:
            raise ex

    return SunInfo(sunrise_time, sunset_time, always_up, always_down)
