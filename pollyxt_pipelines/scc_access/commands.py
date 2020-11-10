from pathlib import Path

from cleo import Command
import pandas as pd

from pollyxt_pipelines import scc_access
from pollyxt_pipelines.config import Config


class UploadFiles(Command):
    '''
    Batch upload files to SCC

    scc-upload
        {path : Path to SCC files. If it is a directory, all netCDF files inside will be uploaded.}
        {list? : Optionally, store the uploaded file IDs in order to later download the products using scc-download}
    '''

    def handle(self):
        # Parse arguments
        path = Path(self.argument('path'))
        if path.is_dir:
            files = path.glob('*.nc')
            files = filter(lambda x: not x.name.startswith('rs_'), files)
            files = filter(lambda x: not x.name.startswith('calibration_'),
                           files)  # TODO Handle calibration files
        else:
            files = [path]

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

        # Upload files
        successful_files = []
        successful_ids = []
        for file, id in scc_access.upload_files(files, credentials):
            self.line(f'<info>Uploaded</info> {file} <info>, got ID = </info>{id}')
            successful_files.append(successful_files)
            successful_ids.append(id)

        # Write list file if requested
        list_file = self.argument('list')
        if list_file is not None:
            list_file = Path(list_file)

            df = pd.DataFrame()
            df['Filename'] = successful_files
            df['Measurement_ID'] = successful_ids
            df['Products_Downloaded'] = False

            df.to_csv(list_file, index=False)
            self.line(f'<comment>Wrote IDs to </comment>{list_file}')


class DownloadFiles(Command):
    '''
    Batch download files from SCC

    scc-download
        {output-directory : Where to store the processing products}
        {list? : Path to list file generated by `scc-upload`. Checks all files and downloads all available products}
        {--id=* : Optionally, instead of a list file, you can write IDs manually.}
    '''

    def handle(self):
        # Check output directory
        output_directory = Path(self.argument('output-directory'))
        output_directory.mkdir(parents=True, exist_ok=True)

        # Check if list or IDs are defined
        id_frame = None
        id_list_file = self.argument('list')
        if id_list_file is None:
            ids = self.option('id')
            if ids is None or len(ids) == 0:
                self.line_error('Either a list file or some measurement IDs must be provided!')
                return 1
        else:
            id_frame = pd.read_csv(id_list_file, index_col='Measurement_ID')
            ids = id_frame.index

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

        # Download files for each ID
        for id, success in scc_access.download_files(ids, output_directory, credentials):
            if success:
                self.line(f'<info>Downloaded products for </info>{id}')
            else:
                self.line(f'<comment>Processing not finished for </comment>{id}')

            if id_frame is not None:
                id_frame.loc[id, 'Products_Downloaded'] = success


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
