from datetime import date
import sys
from pathlib import Path

from cleo import Command

from pollyxt_pipelines.radiosondes import wrf
from pollyxt_pipelines.config import Config


class WRFProfileToCSVs(Command):
    '''
    Convert a WRF profile file to CSV files, each containing an individual profile.

    wrf-to-csv
        {location : Profile location (i.e. city name)}
        {profile-date : Profile date in ISO Format (YYYY-MM-DD)}
        {csv-path : Where to write the CSV files}
    '''

    help = '''
    Examples
    ---

    Read a WRF file and write all profiles into the 'profiles' directory:
    \t pollyxt_pipelines wrf-to-csv ANTIKYTHERA 2020-01-02 ./profiles
    '''

    def handle(self):
        # Parse date and path
        profile_date = date.fromisoformat(self.argument('profile-date'))
        csv_path = Path(self.argument('csv-path'))
        csv_path.mkdir(parents=True, exist_ok=True)

        location = self.argument('location')

        config = Config()

        # Read the WRF profile file
        try:
            df = wrf.read_wrf_daily_profile(config,
                                            self.argument('location'),
                                            profile_date)
        except FileNotFoundError as ex:
            self.line_error('<error>WRF Profile file not found!</error>')
            self.line_error(f'(Path: {ex.filename})')
            sys.exit(1)

        # Split into days and write each into a file
        for _, group in df.groupby('timestamp'):
            group_timestamp = group.iloc[0, 0].strftime('%Y%m%d_%H%M')
            filename = csv_path / f'{location}_{group_timestamp}.csv'

            self.line(f'<info>Writing</info> {filename}')
            group.iloc[:, 1:].to_csv(filename, index=False)
