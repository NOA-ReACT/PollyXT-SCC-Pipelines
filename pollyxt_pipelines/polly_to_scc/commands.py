"""
Commands for creating SCC files
"""

from datetime import timedelta
from pathlib import Path

from rich.progress import track
from cleo import Command

from pollyxt_pipelines.console import console
from pollyxt_pipelines.polly_to_scc import pollyxt, scc_netcdf
from pollyxt_pipelines import locations, radiosondes
from pollyxt_pipelines.polly_to_scc.exceptions import BadMeasurementTime


class CreateSCC(Command):
    """
    Convert PollyXT files to SCC format

    create-scc
        {input : Path to PollyXT files. Can be a single file or a directory of files.}
        {--recursive : If set, the input directory will be searched recursively (i.e. in subdirectories). Ignored for files}
        {location : Where did the measurement take place for *all* input files }
        {output-path : Where to write output files (will create this directory if it doesn't exist)}
        {--interval= : Time interval (in minutes) to split each file. Default is one hour.}
        {--start-time= : When to start the first file (see description below for format). If `end-hour` is defined, a file of the chosen length will be created. Otherwise the intervals will start from this time.}
        {--end-time= : Set when the output file should end. This option MUST be used with `--start-hour`.}
        {--round : When set, output files will start on rounded down hours if possible (e.g. from 00:12 to 00:00, 01:42 to 01:00, etc)}
        {--no-radiosonde : If set, no radiosonde files will be created}
        {--no-calibration : Do not create calibration files}
    """

    help = """
    The `--start-time=` and `--end-time=` options support the following datetime formats:

    - XX:MM (Only minutes, eg. XX:30)
    - HH:MM (Time of day, eg. 20:30)
    - YYYY-mm-DD_HH:MM (Timestamp, 2021-01-29_20:30)

    When the only minutes option is used (XX:30), the first generated file will begin at the first available time for the
    given minutes. For example, if the raw files begin at 2021-01-01 01:50 and the option is set to `--start-time=XX:30`,
    the first output file will start at 02:30 (01:30 is outside the file's range!).

    The time of day option will use the first day which contains the given time. For example, if the raw files begin at
    2021-01-01 01:50 and `--start-time=02:00` is used, the first output file will start at 2021-01-01 02:00.

    Finally, the timestamp option will use the exact time provided. This is useful if the input directory contains many days
    of data.

    If you try to create an SCC file and it includes of one of the following periods, a calibration file will be created:
    - 02:31 to 02:41
    - 17:31 to 17:41
    - 21:31 to 21:41
    You can disable this with the `--no-calibration` option.
    """

    def handle(self):
        # Check output directory
        output_path = Path(self.argument("output-path"))
        output_path.mkdir(parents=True, exist_ok=True)

        # Parse other arguments
        should_round = self.option("round")
        interval = self.option("interval")
        use_sounding = not self.option("no-radiosonde")
        if interval is None:
            interval = 60  # Default duration is 1 hour/60 minutes
        interval = timedelta(minutes=int(interval))
        start_time = self.option("start-time")
        end_time = self.option("end-time")
        if start_time is None and end_time is not None:
            console.print("`--end-time` [error]can't be used without[/error] `--start-time`.")
            return 1

        # Try to get location
        location_name = self.argument("location")
        location = locations.LOCATIONS[location_name]
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Create a repository for the given path
        try:
            console.print("Building repository...")
            repository = pollyxt.PollyXTRepository(Path(self.argument("input")))
        except BadMeasurementTime as ex:
            console.print(
                f"[error]While reading file[/error] {ex.filename} [error]an invalid measurement_time value was encountered:[/error] {ex.value}"
            )
            console.print("[error]Remove this file and try again[/error]")
            return 1

        # Iterate over list and convert files
        skip_calibration = self.option("no-calibration")

        converter = scc_netcdf.convert_pollyxt_file(
            repository,
            output_path,
            location,
            interval,
            should_round=should_round,
            calibration=(not skip_calibration),
            use_sounding=use_sounding,
            start_time=start_time,
            end_time=end_time,
        )
        for id, path, timestamp_start, timestamp_end in converter:
            start_str = timestamp_start.strftime("%Y-%m-%d %H:%M")
            end_str = timestamp_end.strftime("%Y-%m-%d %H:%M")
            console.print(
                f"[info]Created file with measurement ID[/info] {id} [info]at[/info] {str(path)} [info]({start_str} - {end_str})[/info]"
            )

            if use_sounding:
                radiosondes.create_radiosonde_netcdf(
                    "wrf_noa",
                    location,
                    timestamp_start,
                    timestamp_start + interval,
                    netcdf_path=output_path / f"rs{id[:-2]}.nc",
                )

        console.print("\n[info]Done![/info]")
