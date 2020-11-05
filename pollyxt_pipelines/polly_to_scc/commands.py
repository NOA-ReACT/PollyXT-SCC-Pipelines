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

        # Open input netCDF
        input_path = Path(self.argument('input'))
        measurement_start, measurement_end = pollyxt.get_measurement_period(input_path)

        # Parse arguments
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
