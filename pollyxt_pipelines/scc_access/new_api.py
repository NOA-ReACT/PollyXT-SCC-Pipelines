'''
Tools for communicating with the SCC backend

Author: Thanasis Georgiou <ageorgiou@noa.gr>
Based on `scc-access` by Iannis Binietoglou <i.binietoglou@impworks.gr>: https://repositories.imaa.cnr.it/public/scc_access
'''

from datetime import date
import contextlib
from typing import Union, List, Tuple
from pathlib import Path
import shutil

import requests
from bs4 import BeautifulSoup

from pollyxt_pipelines.console import console
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.scc_access.api import SCC_Credentials
from pollyxt_pipelines.scc_access import constants, exceptions
from pollyxt_pipelines.scc_access.types import Measurement


class SCC:
    '''
    Represents a session with SCC.
    Before making any calls, the user should login using `login()`!

    It's recommended to use the `scc_session()` context manager, which handles logging in and out.
    '''

    def __init__(self, credentials: SCC_Credentials):
        self.credentials = credentials

        # Create requests session
        self.session = requests.Session()
        self.session.auth = (
            credentials.http_auth_user, credentials.http_auth_password
        )
        self.session.verify = True

    def login(self):
        '''
        Login to SCC

        This function starts a session with the SCC backend, storing the authentication
        cookies so they can be used by the rest of the methods. Remember to call `logout()`!
        '''

        # Get login form (for csrf token)
        login_page = self.session.get(constants.login_url)
        if not login_page.ok:
            raise exceptions.PageNotAccessible(constants.login_url, login_page.status_code)

        # Submit login form
        body = {
            'username': self.credentials.username,
            'password': self.credentials.password
        }
        headers = {
            'X-CSRFToken': login_page.cookies['csrftoken'],
            'referer': constants.login_url
        }
        logon_request = self.session.post(
            constants.login_url, data=body, headers=headers)

        # Do some basic checking on the response
        if 'Wrong username or password' in logon_request.text:
            raise exceptions.WrongCredentialsException()

    def logout(self):
        '''Logout of SCC'''
        self.session.get(constants.login_url)

    def download_file(self, url: str, path: Path):
        '''
        Downloads a single file from SCC to the given path

        Parameters
        ---
        - url (str): Which URL to download the file from
        - path (Path): Where to store the downloaded file
        '''

        with requests.get(url, stream=True) as r:
            with open(path, 'wb') as file:
                shutil.copyfileobj(r.raw, file)

    def query_measurements(self, date_start: date, date_end: date,
                           location: Union[Location, None], page=0) -> Tuple[int, List[Measurement]]:
        '''
        Searches SCC for uploaded measurements

        Parameters
        ---
        date_start (date): First day of results
        date_end (date): Last day of results
        location (Location): Optionally, filter results by a location
        page (int): Which page to return (starts from 1, default value is 1)

        Returns
        ---
        The number of pages and the list of measurements
        '''

        params = {
            'start__gte': date_start.strftime('%Y-%m-%d %H:%M:%S'),
            'start__lt': date_end.strftime('%Y-%m-%d %H:%M:%S')
        }
        if location is not None:
            params['station_id'] = location.scc_code

        results = self.session.get(constants.list_measurements_url, params=params)
        if not results.ok:
            raise exceptions.UnexpectedResponse

        # Parse body to find measurements and page count
        body = BeautifulSoup(results.text, 'html.parser')

        pagination = body.find('nav', class_='grp-pagination')
        last_page = pagination.find('a', class_='end')
        if last_page is None:
            pages = 1
        else:
            pages = int(last_page.text)

        measurements = [Measurement.from_table_row(tr)
                        for tr in body.findAll('tr', {'class': 'grp-row'})]

        return pages, measurements

    def download_products(self, measurement_id: str, download_path: Path,
                          hirelpp=True,
                          cloudmask=True,
                          elpp=True,
                          optical=True,
                          elic=True):
        '''
        Downloads products for a given measurement (ID) to the given path.
        This function is a generator, yielding the filename of each downloaded file.

        Parameters
        ---
        - measurement_id (str): Which measurement to download products for
        - download_path (Path): Where to store the downloaded products
        - hirelpp (bool, default=True): Whether to download HiRELPP files
        - cloudmask (bool, default=True): Whether to download Cloudmask files
        - elpp (bool, default=True): Whether to download ELPP files
        - optical (bool, default=True): Whether to download optical (ELDA or ELDEC) files
        - elic (bool, default=True): Whether to download ELIC files
        '''

        # Determine URLs to download
        to_download = []
        if hirelpp:
            to_download.append({
                'url': constants.download_hirelpp_pattern.format(measurement_id),
                'path': download_path / f'hirelpp_{measurement_id}.zip'
            })
        if cloudmask:
            to_download.append({
                'url': constants.download_cloudmask_pattern.format(measurement_id),
                'path': download_path / f'cloudmask_{measurement_id}.zip'
            })
        if elpp:
            to_download.append({
                'url': constants.download_preprocessed_pattern.format(measurement_id),
                'path': download_path / f'preprocessed_{measurement_id}.zip'
            })
        if optical:
            to_download.append({
                'url': constants.download_optical_pattern.format(measurement_id),
                'path': download_path / f'optical_{measurement_id}.zip'
            })
        if elic:
            to_download.append({
                'url': constants.download_elic_pattern.format(measurement_id),
                'path': download_path / f'elic_{measurement_id}.zip'
            })

        if len(to_download) == 0:
            raise ValueError('At least one product must be downloaded!')

        # Download each file
        for download in to_download:
            try:
                self.download_file(**download)
                yield download['path']
            except Exception as ex:
                console.print('[error]Error while downloading file from SCC[/error]')
                console.print(f'[error]URL:[/error] {download["url"]}')
                console.print(f'[error]Path:[/error] {download["path"]}')
                console.print('[error]Exception:[/error]')
                console.print_exception()
                continue


@contextlib.contextmanager
def scc_session(credentials: SCC_Credentials):
    '''
    An SCC session as a context, to use with `with:`

    Example
    ---
    ```python
    with scc_access(credentials) as scc:
        # Use scc
        # ...
    ```
    '''
    try:
        scc = SCC(credentials)
        scc.login()
        yield scc
    finally:
        scc.logout()
