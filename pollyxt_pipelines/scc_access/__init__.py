'''
Based on SCC-Access by Ioannis Binietoglou licensed under MIT
https://repositories.imaa.cnr.it/public/scc_access/file
'''

from datetime import date
import logging
from pathlib import Path
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.scc_access.api import Measurement
from typing import List, Union

from netCDF4 import Dataset

from pollyxt_pipelines.scc_access import api, new_api

BASE_URL = 'https://scc.imaa.cnr.it/'
logger = logging.getLogger(__name__)


def download_files(ids: List[str], output_path: Path, credentials: api.SCC_Credentials):
    '''
    Batch download of processing products from SCC

    Parameters
    ---
    ids (List[str]): List of IDs to check. If processing is completed for each file, the products
                     are downloaded.
    output_path (Path): Where to store the downloaded products
    '''

    # Login to the API
    scc = api.SCC(credentials, output_dir=output_path)
    scc.login()

    # Check each ID
    for id in ids:
        measurement, _ = scc.get_measurement(id)
        if measurement is None or measurement.is_running:
            yield id, False
            continue

        # Download any available products
        if measurement.hirelpp == 127:
            scc.download_hirelpp(id)
        if measurement.cloudmask == 127:
            scc.download_cloudmask(id)
        if measurement.elpp == 127:
            scc.download_preprocessed(id)
        if measurement.elda == 127:
            scc.download_optical(id)
            scc.download_graphs(id)
        if measurement.elic == 127:
            scc.download_elic(id)

        yield id, True


def search_measurements(date_start: date, date_end: date,
                        location: Union[Location, None],
                        credentials: api.SCC_Credentials) -> List[Measurement]:
    '''
    Searches SCC for measurement files

    Parameters
    ---
    date_start (date): First day of files to return
    date_end (date): Last day of files to return
    location (Location): Optionally, search files only from this station

    Returns
    ---
    A list of measurements
    '''

    # Login to the API
    with new_api.scc_session(credentials) as scc:
        # Search for files
        if location is not None:
            station = location.scc_code
        else:
            station = None
        measurements = scc.query_measurements(date_start, date_end, location)

        return measurements
