from pathlib import Path

from cleo import Command

from pollyxt_pipelines import scc_access, locations
from pollyxt_pipelines.config import Config


class ProcessFile(Command):
    '''
    Upload a file to SCC, wait for processing and download the results

    scc-process
        {filename : Which file to upload. Must be accompanied by a radiosonde file}
        {download-path : Where to download the results}
    '''

    def handle(self):
        # Parse arguments
        filename = Path(self.argument('filename'))

        download_path = Path(self.argument('download-path'))
        download_path.mkdir(exist_ok=True, parents=True)

        # Read application config
        config = Config()
        try:
            credentials = scc_access.api.SCC_Credentials(config)
        except KeyError:
            self.line('<error>Credentials not found in config</error>')
            self.line('Use `pollyxt_pipelines config` to set the following variables:')
            self.line('- http.username')
            self.line('- http.password')
            self.line('- auth.username')
            self.line('- auth.password')
            self.line('For example, `pollyxt_pipelines config http.username scc_user')
            return 1

        try:
            measurement = scc_access.process_file(filename, download_path, credentials)
        except scc_access.api.WrongCredentialsException:
            self.line_error('<error>Could not authenticate with SCC, verify credentials</error>')
            return 1
        print(measurement)
