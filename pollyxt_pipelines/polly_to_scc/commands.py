'''
Commands for creating SCC files
'''

from datetime import timedelta
from pathlib import Path

from rich.progress import track
from cleo import Command

from pollyxt_pipelines.console import console
from pollyxt_pipelines.polly_to_scc import pollyxt, scc_netcdf
from pollyxt_pipelines import locations, radiosondes
from pollyxt_pipelines.config import Config


class CreateSCC(Command):
    '''
    Convert PollyXT files to SCC format

    create-scc
        {input : Path to PollyXT files. Can be a single file or a directory of files.}
        {--recursive : If set, the input directory will be searched recursively (i.e. in subdirectories). Ignored for files}
        {location : Where did the measurement take place for *all* input files }
        {output-path : Where to write output files (will create this directory if it doesn't exist)}
        {--interval= : Time interval (in minutes) to split each file. Default is one hour.}
        {--start-time= : When to start the first file in HH:MM format. If `end-hour` is defined, a file of the chosen length will be created. Otherwise the intervals will start from this time.}
        {--end-time= : Set when the output file should end. This option MUST be used with `--start-hour`.}
        {--round : When set, output files will start on rounded down hours if possible (e.g. from 00:12 to 00:00, 01:42 to 01:00, etc)}
        {--no-radiosonde : If set, no radiosonde files will be created}
        {--no-calibration : Do not create calibration files}
    '''

    help = '''
    If you try to create an SCC file and it includes of one of the following periods, a calibration file will be created:
    - 02:31 to 02:41
    - 17:31 to 17:41
    - 21:31 to 21:41
    You can disable this with the `--no-calibration` option.
    '''

    def handle(self):
        # Check output directory
        output_path = Path(self.argument('output-path'))
        output_path.mkdir(parents=True, exist_ok=True)

        # Parse other arguments
        should_round = self.option('round')
        interval = self.option('interval')
        use_sounding = not self.option('no-radiosonde')
        if interval is None:
            interval = 60  # Default duration is 1 hour/60 minutes
        interval = timedelta(minutes=interval)
        start_time = self.option("start-time")
        end_time = self.option("end-time")
        if start_time is None and end_time is not None:
            console.print("`--end-time` [error]can't be used without[/error] `--start-time`.")
            return 1

        # Try to get location
        location_name = self.argument('location')
        location = locations.LOCATIONS[location_name]
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Get list of input files
        input_path = Path(self.argument('input'))
        if not input_path.is_dir():
            file_list = [input_path]
        else:
            if self.option('recursive'):
                pattern = '**/*.nc'
            else:
                pattern = '*.nc'
            file_list = list(input_path.glob(pattern))

        if len(file_list) == 0:
            console.print(f'[error]No netCDF files found in[/error] {input_path}')
            return 1

        # Read config for radiosonde path
        config = Config()

        # Iterate over list and convert files
        skip_calibration = self.option('no-calibration')
        for file in track(file_list, description="Converting...", console=console):
            console.print(f'-> [info]Converting[/info] {file} [info]...[/info]', style="bold")

            # Try to find radiosonde profiles
            profiles = None
            if use_sounding:
                day = pollyxt.get_measurement_period(file)[0].date()
                try:
                    profiles = radiosondes.wrf.read_wrf_daily_profile(config, location, day)
                except FileNotFoundError as ex:
                    console.print(
                        f'[error]No radiosonde file found for [/error]{location.name}[error] at [/error]{day.isoformat()}')
                    console.print('[error]Use the --no-radiosonde option to skip this.[/error]')
                    return 1

            converter = scc_netcdf.convert_pollyxt_file(
                file, output_path, location, interval, should_round=should_round, calibration=(not skip_calibration), use_sounding=use_sounding, start_time=start_time, end_time=end_time)
            for id, path, timestamp in converter:
                console.print(
                    f'[info]Created file with measurement ID[/info] {id} [info]at[/info] {str(path)}')

                # Attempt to write radiosonde for this profile
                if profiles is not None:
                    p = profiles[profiles['timestamp'] == timestamp.replace(minute=0, second=0)]
                    if len(p) > 0:
                        path = output_path / f'rs_{id[:-2]}.nc'
                        radiosondes.create_radiosonde_netcdf(p, location, path)
                        console.print(f'[info]Created radiosonde file at[/info] {path}')
                    else:
                        console.print(f'[error]No radiosonde profile found for [/error]{id}')

        console.print('\n[info]Done![/info]')
