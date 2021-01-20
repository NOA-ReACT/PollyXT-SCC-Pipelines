"""
Tools for communicating with the SCC backend

Author: Thanasis Georgiou <ageorgiou@noa.gr>

Based on `scc-access` by Iannis Binietoglou <i.binietoglou@impworks.gr>: https://repositories.imaa.cnr.it/public/scc_access
"""

from datetime import date
import contextlib
from typing import Union, List, Tuple
from pathlib import Path
import shutil

import requests
from bs4 import BeautifulSoup

from pollyxt_pipelines.console import console
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.config import Config
from pollyxt_pipelines.scc_access import constants, exceptions
from pollyxt_pipelines.scc_access.types import APIObject, Measurement


class SCC_Credentials:
    """
    Contains all required credentials to authenticate with SCC
    """

    http_auth_user: str
    http_auth_password: str
    username: str
    password: str

    def __init__(self, config: Config):
        self.http_auth_user = config["http"]["username"]
        self.http_auth_password = config["http"]["password"]
        self.username = config["auth"]["username"]
        self.password = config["auth"]["password"]


class SCC:
    """
    Represents a session with SCC.
    Before making any calls, the user should login using `login()`!

    It's recommended to use the `scc_session()` context manager, which handles logging in and out.
    """

    def __init__(self, credentials: SCC_Credentials):
        self.credentials = credentials

        # Create requests session
        self.session = requests.Session()
        self.session.auth = (credentials.http_auth_user, credentials.http_auth_password)
        self.session.verify = True

    def login(self):
        """
        Login to SCC

        This function starts a session with the SCC backend, storing the authentication
        cookies so they can be used by the rest of the methods. Remember to call `logout()`!
        """

        # Get login form (for csrf token)
        login_page = self.session.get(constants.login_url)
        if not login_page.ok:
            raise exceptions.PageNotAccessible(constants.login_url, login_page.status_code)

        # Submit login form
        body = {"username": self.credentials.username, "password": self.credentials.password}
        headers = {"X-CSRFToken": login_page.cookies["csrftoken"], "referer": constants.login_url}
        logon_request = self.session.post(constants.login_url, data=body, headers=headers)

        # Do some basic checking on the response
        if "Wrong username or password" in logon_request.text:
            raise exceptions.WrongCredentialsException()

    def logout(self):
        """Logout of SCC"""
        self.session.get(constants.login_url)

    def download_file(self, url: str, path: Path):
        """
        Downloads a single file from SCC to the given path

        Parameters:
            url: Which URL to download the file from
            path: Where to store the downloaded file
        """

        with self.session.get(url, stream=True) as r:
            with open(path, "wb") as file:
                shutil.copyfileobj(r.raw, file)

    def query_measurements(
        self, date_start: date, date_end: date, location: Union[Location, None], page=1
    ) -> Tuple[int, List[Measurement]]:
        """
        Searches SCC for uploaded measurements

        Parameters:
            date_start: First day of results
            date_end: Last day of results
            location: Optionally, filter results by a location
            page: Which page to return (starts from 1, default value is 1)

        Returns:
            The number of pages and the list of measurements
        """

        if page - 1 < 0:
            raise ValueError("Page numbers start at 1!")

        params = {
            "start__gte": date_start.strftime("%Y-%m-%d %H:%M:%S"),
            "start__lt": date_end.strftime("%Y-%m-%d %H:%M:%S"),
            "p": page - 1,
        }
        if location is not None:
            params["station_id"] = location.scc_code

        results = self.session.get(constants.list_measurements_url, params=params)
        if not results.ok:
            raise exceptions.UnexpectedResponse

        # Parse body to find measurements and page count
        body = BeautifulSoup(results.text, "html.parser")

        pagination = body.find("nav", class_="grp-pagination")
        last_page = pagination.find("a", class_="end")
        if last_page is None:
            pages = 1
        else:
            pages = int(last_page.text)

        measurements = [
            Measurement.from_table_row(tr) for tr in body.findAll("tr", {"class": "grp-row"})
        ]

        return pages, measurements

    def download_products(
        self,
        measurement_id: str,
        download_path: Path,
        hirelpp=True,
        cloudmask=True,
        elpp=True,
        optical=True,
        elic=True,
    ):
        """
        Downloads products for a given measurement (ID) to the given path.
        This function is a generator, yielding the filename of each downloaded file.

        Parameters:
            measurement_id: Which measurement to download products for
            download_path: Where to store the downloaded products
            hirelpp: Whether to download HiRELPP files
            cloudmask: Whether to download Cloudmask files
            elpp: Whether to download ELPP files
            optical: Whether to download optical (ELDA or ELDEC) files
            elic: Whether to download ELIC files
        """

        # Determine URLs to download
        to_download = []
        if hirelpp:
            to_download.append(
                {
                    "url": constants.download_hirelpp_pattern.format(measurement_id),
                    "path": download_path / f"hirelpp_{measurement_id}.zip",
                }
            )
        if cloudmask:
            to_download.append(
                {
                    "url": constants.download_cloudmask_pattern.format(measurement_id),
                    "path": download_path / f"cloudmask_{measurement_id}.zip",
                }
            )
        if elpp:
            to_download.append(
                {
                    "url": constants.download_preprocessed_pattern.format(measurement_id),
                    "path": download_path / f"preprocessed_{measurement_id}.zip",
                }
            )
        if optical:
            to_download.append(
                {
                    "url": constants.download_optical_pattern.format(measurement_id),
                    "path": download_path / f"optical_{measurement_id}.zip",
                }
            )
        if elic:
            to_download.append(
                {
                    "url": constants.download_elic_pattern.format(measurement_id),
                    "path": download_path / f"elic_{measurement_id}.zip",
                }
            )

        if len(to_download) == 0:
            raise ValueError("At least one product must be downloaded!")

        # Download each file
        for download in to_download:
            try:
                self.download_file(**download)
                yield download["path"]
            except Exception as ex:
                console.print("[error]Error while downloading file from SCC[/error]")
                console.print(f'[error]URL:[/error] {download["url"]}')
                console.print(f'[error]Path:[/error] {download["path"]}')
                console.print("[error]Exception:[/error]")
                console.print_exception()
                continue

    def get_anchillary(self, file_id: str, file_type: str) -> Union[APIObject, None]:
        """
        Uses the SCC API to fetch information about anchillary files.

        Parameters:
            file_id: File ID to lookup
            file_type: What kind of file to lookup ('sounding', 'overlap' or 'lidarratio')

        Returns:
            The API response about the file
        """

        # Determine correct endpoint
        if file_type == "sounding":
            url = constants.api_sounding_search_pattern.format(file_id)
        elif file_type == "overlap":
            url = constants.api_overlap_search_pattern.format(file_id)
        elif file_type == "lidarratio":
            url = constants.api_lidarratio_search_pattern.format(file_id)
        else:
            raise ValueError(f"File type should be one of: sounding, overlap, lidarratio")

        # Make request
        response = self.session.get(url)
        if not response.ok:
            raise exceptions.UnexpectedResponse("Could not get anchillary file info")

        # Parse body
        # It should have an 'objects' dictionary containing one entry, if it is found
        response_body = response.json()
        objects = response_body["objects"]

        if objects:
            return APIObject(objects[0])
        else:
            return None

    def upload_file(
        self,
        filename: Path,
        system_id: str,
        rs_filename: Union[Path, None] = None,
        ov_filename: Union[Path, None] = None,
        lr_filename: Union[Path, None] = None,
    ):
        """
        Uploads a file to SCC, together with the auxilary files. There is no return value, but it will
        throw for potential errors.

        Parameters:
            filename: Path to the SCC netCDF file
            system_id: SCC Lidar System ID for the system that made the measurement
            rs_filename: Path to the radiosonde netCDF file
            ov_filename: Path to the overlap netCDF file
            lr_filename: Path to the lidar ratio netCDF file
        """

        # Check if the given anchillary files already exist before adding them to the request body
        files = {}
        if rs_filename is not None:
            info = self.get_anchillary(rs_filename.name, "sounding")
            if info is not None and info.exists:
                console.print(
                    f"[warn]Radiosonde file[/warn] {rs_filename.name} [warn]already exists on SCC.[/warn]"
                )
            else:
                files["sounding_file"] = open(rs_filename, "rb")

        if ov_filename is not None:
            info = self.get_anchillary(ov_filename.name, "overlap")
            if info is not None and info.exists:
                console.print(
                    f"[warn]Overlap file[/warn] {ov_filename.name} [warn]already exists on SCC.[/warn]"
                )
            else:
                files["overlap_file"] = open(ov_filename, "rb")

        if lr_filename is not None:
            info = self.get_anchillary(lr_filename.name, "lidarratio")
            if info is not None and info.exists:
                console.print(
                    f"[warn]Lidar ratio file[/warn] {lr_filename.name} [warn]already exists on SCC.[/warn]"
                )
            else:
                files["lidar_ratio_file"] = open(lr_filename, "rb")

        files["data"] = open(filename, "rb")

        # Get the form and submit it
        upload_page = self.session.get(constants.upload_url)

        body = {"system": system_id}
        headers = {"X-CSRFToken": upload_page.cookies["csrftoken"], "referer": constants.upload_url}
        upload_submit = self.session.post(
            constants.upload_url, data=body, files=files, headers=headers
        )

        # Check response
        response_body = BeautifulSoup(upload_submit.text, "html.parser")
        alerts = response_body.find_all("div", class_="alert-box")
        if len(alerts) > 0:
            errors = ", ".join([alert.p.text.strip() for alert in alerts])
            raise exceptions.SCCError(errors)

        # console.print(upload_submit.text)
        if upload_submit.status_code != 200 or upload_submit.url == constants.upload_url:
            raise exceptions.UnexpectedResponse("Upload to SCC failed")

    def get_measurement(self, measurement_id: str) -> Union[Measurement, None]:
        """
        Fetches information about one measurement from SCC.

        Parameters:
            measurement_id: Which measurement to lookup

        Returns:
            The measurement if it exists, None otherwise
        """

        url = constants.api_measurement_pattern.format(measurement_id)

        response = self.session.get(url)

        if response.status_code == 404:
            return None
        elif not response.ok:
            raise exceptions.UnexpectedResponse()

        response_body = response.json()
        if response_body:
            return Measurement.from_json(response_body)
        else:
            raise exceptions.UnexpectedResponse()

    def delete_measurement(self, measurement_id: str):
        """
        Deletes a measurement from SCC

        Parameters:
            measurement_id: Which measurement to delete
        """

        # Submit form
        url = constants.delete_measurement_pattern.format(measurement_id)
        body = {"select_delete_related_measurements": "not_delete_related", "post": "yes"}
        headers = {
            "referer": url,
            "X-CSRFToken": self.session.cookies["csrftoken"],
        }
        response = self.session.post(url, data=body, headers=headers)

        # Look for success banner
        if response.status_code == 404:
            raise exceptions.MeasurementNotFound(measurement_id)
        if response.status_code != 200:
            raise exceptions.UnexpectedResponse("Response code is not 200")

    def rerun_processing(self, measurement_id: str):
        """
        Asks SCC to re-run processing routines for a given measurement ID

        Parameters:
            measurement_id: Which measurement to re-run
        """

        # Submit form
        url = constants.rerun_measurement_url
        body = {
            "_selected_action": measurement_id,
            "action": "rerun_all",
            "selected_across": "0",
            "index": 0,
        }
        headers = {
            "referer": url,
            "X-CSRFToken": self.session.cookies["csrftoken"],
        }
        response = self.session.post(url, data=body, headers=headers, allow_redirects=False)

        # Look for success banner
        if response.status_code == 404:
            raise exceptions.MeasurementNotFound(measurement_id)
        if response.status_code != 302:
            raise exceptions.UnexpectedResponse("Response code is not 302")

        # Check for message in cookie
        messages_cookie = response.cookies["messages"]
        if messages_cookie is None:
            raise exceptions.UnexpectedResponse("`Messages` cookie not found")

        if "The processing chain was restarted" not in messages_cookie:
            raise exceptions.UnexpectedResponse("Could not found restart message in cookie")


@contextlib.contextmanager
def scc_session(credentials: SCC_Credentials):
    """
    An SCC session as a context, to use with `with:`

    Example::

        with scc_access(credentials) as scc:
            # Use scc
            # ...
    """
    try:
        scc = SCC(credentials)
        scc.login()
        yield scc
    finally:
        scc.logout()
