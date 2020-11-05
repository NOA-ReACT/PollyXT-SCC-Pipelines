'''
Commands for creating SCC files
Author: Thanasis Georgiou <ageorgiou@noa.gr>
'''

from datetime import timedelta
from pathlib import Path
from pollyxt_pipelines.polly_to_scc.scc_netcdf import convert_pollyxt_file

from cleo import Command

from pollyxt_pipelines.polly_to_scc import pollyxt, scc_netcdf as scc
from pollyxt_pipelines import locations


class CreateSCCFile(Command):
    '''
    Creates SCC files from a PollyXT netCDF file.

    create-scc
        {input : Path to input PollyXT netCDF file}
        {location : Location name (i.e. where did the Polly measurement take place)}
        {output-path : Directory to store output (will be created if it doesn't exist)}
        {--interval= : Time interval (in minutes) to split the file. Default is one hour.}
        {--round : When set, output files will start on rounded down hours if possible (e.g. from 00:12 to 00:00, 01:42 to 01:00, etc)}
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

        # Convert files
        converter = convert_pollyxt_file(
            input_path, output_path, locations.LOCATION_ANTIKYTHERA, interval, should_round)
        for id, path in converter:
            self.line('<info>Created file with measurement ID </info>' +
                      id + '<info> at </info>' + str(path))


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
        for file in file_list:
            progress.clear()
            self.line(f'\r-> <comment>Converting</comment> {file} <comment>...</comment>')
            progress.display()

            converter = convert_pollyxt_file(
                file, output_path, locations.LOCATION_ANTIKYTHERA, interval, should_round)
            for id, path in converter:
                progress.clear()
                self.line('\r<info>Created file with measurement ID </info>' +
                          id + '<info> at </info>' + str(path))
                progress.display()

            progress.advance()

        progress.finish()
        self.line('\n<comment>Done!</comment>')
