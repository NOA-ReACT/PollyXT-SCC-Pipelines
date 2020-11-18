from datetime import date
import contextlib
from typing import Union, List, Tuple

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
        '''Login to SCC'''

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


@contextlib.contextmanager
def scc_session(credentials: SCC_Credentials):
    '''
    An SCC session as a context, to use with `with:`
    '''
    try:
        scc = SCC(credentials)
        scc.login()
        yield scc
    finally:
        scc.logout()
