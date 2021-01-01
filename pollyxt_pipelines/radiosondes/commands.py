from datetime import date, datetime
from pollyxt_pipelines import locations
from pollyxt_pipelines.locations import LOCATIONS
from pathlib import Path

from cleo import Command
from rich.markdown import Markdown

from pollyxt_pipelines.radiosondes.exceptions import RadiosondeNotFound
from pollyxt_pipelines.radiosondes import (
    RadiosondeProviders,
    write_radiosonde_netcdf,
)
from pollyxt_pipelines.config import Config
from pollyxt_pipelines.console import console


class GetRadiosonde(Command):
    """
    Fetches sounding information and optionally write to a file. Mainly used to test providers.

    get-radiosonde
        {provider : Which provider to use}
        {timestamp : Find radiosonde for this timestamp (YYYY-MM-DD_HH:mm format)}
        {location : Location (station) name}
        {--to-csv= : Optionally write the radiosonde data to a CSV file}
        {--to-scc= : Optionaly write the radiosonde data to a SCC-formatted netCDF file}
    """

    def handle(self):
        # Get requested provider
        provider = RadiosondeProviders.get(self.argument("provider"), None)
        if provider is None:
            console.print(f"[error]Unknown provider[/error] {self.argument('provider')}")
            known_providers = "List of supported providers:\n\n"
            for key in RadiosondeProviders.keys():
                known_providers += f"- {key}\n"
            console.print(Markdown(known_providers))
            return 1

        # Get location
        location = self.argument("location")
        location = LOCATIONS.get(location, None)
        if location is None:
            locations.unknown_location_error(self.argument("location"))
            return 1

        # Parse timestamp
        timestamp = datetime.strptime(self.argument("timestamp"), "%Y-%m-%d_%H:%M")

        # Get profile from provider
        try:
            profile_time, profile = provider(location, timestamp, timestamp)
        except RadiosondeNotFound as ex:
            ex.print_error()
            return 1
        except Exception as ex:
            console.print(
                f"[error]Got unknown error while using provider[/error] {self.argument('provider')}"
            )
            console.print_exception()
            return 1

        # Print the profile
        console.print(f"Found profile with time {profile_time}")
        console.print(profile)

        # Write to disk if requested
        to_csv = self.option("to-csv")
        if to_csv is not None:
            console.print(f"[info]Writing profile as CSV file:[/info] {to_csv}")
            profile.to_csv(to_csv, index=False)

        to_scc = self.option("to-scc")
        if to_scc is not None:
            console.print(f"[info]Writing profile as SCC radiosonde file:[/info] {to_scc}")
            write_radiosonde_netcdf(profile, location, profile_time, to_scc)
