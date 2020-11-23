'''
Commands for creating SCC files
'''

from datetime import timedelta
from pathlib import Path

from cleo import Command

from pollyxt_pipelines.console import console
from pollyxt_pipelines.polly_to_scc import pollyxt, scc_netcdf
from pollyxt_pipelines import locations, radiosondes
from pollyxt_pipelines.config import Config


class CreateSCC(Command):
    '''
    Creates SCC files from a PollyXT netCDF file.

    create-scc
        {input : Path to input PollyXT netCDF file}
        {location : Location name (i.e. where did the Polly measurement take place)}
        {output-path : Directory to store output (will be created if it doesn't exist)}
        {--interval= : Time interval (in minutes) to split the file. Default is one hour.}
        {--round : When set, output files will start on rounded down hours if possible (e.g. from 00:12 to 00:00, 01:42 to 01:00, etc)}
        {--no-radiosonde : If set, no radiosonde files will be created}
        {--no-calibration : Do not create calibration file}
    '''

    help = '''
    If you try to create an SCC file and it includes of one of the following periods, a calibration file will be created:
    - 02:31 to 02:41
    - 17:31 to 17:41
    - 21:31 to 21:41
    You can disable this with the `--no-calibration` option.
    '''

    def handle(self):
        # Create output directory
        output_path = Path(self.argument('output-path'))
        output_path.mkdir(parents=True, exist_ok=True)

        # Parse arguments
        input_path = Path(self.argument('input'))
        should_round = self.option('round')
        interval = self.option('interval')
        if interval is None:
            interval = 60  # Default duration is 1 hour/60 minutes
        interval = timedelta(minutes=interval)

        # Try to get location
        location_name = self.argument('location')
        location = locations.get_location_by_name(location_name)
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Check for radiosonde files
        config = Config()
        profiles = None
        if not self.option('no-radiosonde'):
            day = pollyxt.get_measurement_period(input_path)[0].date()
            try:
                profiles = radiosondes.wrf.read_wrf_daily_profile(config, location, day)
            except FileNotFoundError as ex:
                self.line_error(
                    f'<error>No radiosonde file found for </error>{location.name}<error> at </error>{day.isoformat()}')
                self.line_error('<error>Use the --no-radiosonde option to skip this.')
                return 1

        # Convert files
        skip_calibration = self.option('no-calibration')
        converter = scc_netcdf.convert_pollyxt_file(
            input_path, output_path, location, interval, should_round, calibration=(not skip_calibration))
        for id, path, timestamp in converter:
            self.line('<info>Created file with measurement ID </info>' +
                      id + '<info> at </info>' + str(path))

            # Attempt to write radiosonde for this profile
            if profiles is not None:
                p = profiles[profiles['timestamp'] == timestamp.replace(minute=0, second=0)]
                if len(p) > 0:
                    path = output_path / f'rs_{id[:-2]}.nc'
                    radiosondes.create_radiosonde_netcdf(p, location, path)
                    self.line(f'<info>Created radiosonde file at</info> {path}')
                else:
                    self.line_error(f'<error>No radiosonde profile found for </error>{id}')


class CreateSCCBatch(Command):
    '''
    Converts a whole directory tree of PollyXT files to SCC format.

    create-scc-batch
        {input : Path to PollyXT files. Will try to convert all netCDF files in this directory}
        {--recursive : If set, the input directory will be searched recursively (i.e. in subdirectories) }
        {location : Where did the measurement take place for *all* input files }
        {output-path : Where to write output files (will create this directory if it doesn't exist)}
        {--interval= : Time interval (in minutes) to split each file. Default is one hour.}
        {--round : When set, output files will start on rounded down hours if possible (e.g. from 00:12 to 00:00, 01:42 to 01:00, etc)}
        {--no-radiosonde : If set, no radiosonde files will be created}
        {--no-calibration : Do not create calibration files}
    '''

    def handle(self):
        # Check output directory
        output_path = Path(self.argument('output-path'))
        output_path.mkdir(parents=True, exist_ok=True)

        # Parse other arguments
        should_round = self.option('round')
        interval = self.option('interval')
        if interval is None:
            interval = 60  # Default duration is 1 hour/60 minutes
        interval = timedelta(minutes=interval)

        # Try to get location
        location_name = self.argument('location')
        location = locations.get_location_by_name(location_name)
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Get list of input files
        input_path = Path(self.argument('input'))
        if self.option('recursive'):
            pattern = '**/*.nc'
        else:
            pattern = '*.nc'

        file_list = list(input_path.glob(pattern))
        if len(file_list) == 0:
            self.line_error(f'<error>No netCDF files found in </error>{input_path}')
            return 1

        progress = self.progress_bar(len(file_list))

        # Iterate over list and convert files
        skip_calibration = self.option('no-calibration')
        for file in file_list:
            progress.clear()
            self.line(f'\r-> <comment>Converting</comment> {file} <comment>...</comment>')
            progress.display()

            # Try to find profiles
            # Check for radiosonde files
            config = Config()
            profiles = None
            if not self.option('no-radiosonde'):
                day = pollyxt.get_measurement_period(file)[0].date()
                try:
                    profiles = radiosondes.wrf.read_wrf_daily_profile(config, location, day)
                except FileNotFoundError as ex:
                    self.line_error(
                        f'<error>No radiosonde file found for </error>{location.name}<error> at </error>{day.isoformat()}')
                    self.line_error('<error>Use the --no-radiosonde option to skip this.')
                    return 1

            converter = scc_netcdf.convert_pollyxt_file(
                file, output_path, location, interval, should_round, calibration=(not skip_calibration))
            for id, path, timestamp in converter:
                progress.clear()
                self.line('\r<info>Created file with measurement ID </info>' +
                          id + '<info> at </info>' + str(path))

                # Attempt to write radiosonde for this profile
                if profiles is not None:
                    p = profiles[profiles['timestamp'] == timestamp.replace(minute=0, second=0)]
                    if len(p) > 0:
                        path = output_path / f'rs_{id[:-2]}.nc'
                        radiosondes.create_radiosonde_netcdf(p, location, path)
                        self.line(f'<info>Created radiosonde file at</info> {path}')
                    else:
                        self.line_error(f'<error>No radiosonde profile found for </error>{id}')

                progress.display()
            progress.advance()
        progress.finish()
        self.line('\n<comment>Done!</comment>')
