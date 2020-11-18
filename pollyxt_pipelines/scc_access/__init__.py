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


def upload_files(
    filenames: List[Path], credentials: api.SCC_Credentials
):
    '''
    Batch upload of files to SCC

    Parameters
    ---
    - filenames (List[Path]): Which files to upload. Files must be accompanied by radiosonde
                              netCDF files (rs_%ID.nc). The radiosonde filename will be read
                              from the 'Sounding_File_name` attribute. To upload only one file,
                              provide a list with only one item.
    - credentials (SCC_Credentials): The authentication credentials to use

    Returns
    ---
    This is a generator, yielding each filename and the corresponding measurement ID. You can store these IDs to download
    the processing results later using `download_products()`.

    ```
    for filename, id in upload_files(names, credenials):
        # Do something with id
    ```
    '''

    # Login to the API
    # TODO Remove output_dir from here
    scc = api.SCC(credentials, output_dir='./')
    scc.login()

    for filename in filenames:
        # Determine radiosonde filename and system configuration ID from netCDF attributes
        with Dataset(filename, 'r') as nc:
            rs_name: str = nc.Sounding_File_Name
            configuration_id: int = nc.NOAReACT_Configuration_ID

        # Check radiosonde file existance
        rs_filename = filename.parent / rs_name
        if not rs_filename.is_file():
            scc.logout()  # Logout before raising exception
            raise FileNotFoundError(
                f'Dataset {filename} required radiosonde {rs_name} but it is not found at {rs_filename}')

        # Upload file
        measurement_id = scc.upload_file(filename, configuration_id,
                                         rs_filename=rs_filename)
        if measurement_id == False:
            print(f'Could not upload file {filename}!')
        else:
            yield filename, measurement_id

    scc.logout()


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


def process_file(
        filename: Path, download_path: Path,
        credentials: api.SCC_Credentials):
    '''
    Upload a file to SCC, wait for processing and download the results.
    Only auxilary radiosonde files are supported currently.

    Parameters
    - filename (Path): Which file to upload. It will check the attributes inside this file to upload
                       auxilary files (e.g. radiosondes).
    - download_path (Path): Where to store the results
    - credentials (SCC_Credentials): The authentication credentials to use
    '''
    # Determine radiosonde filename and check if it exists
    with Dataset(filename, 'r') as nc:
        rs_name: str = nc.Sounding_File_Name
        configuration_id: int = nc.NOAReACT_Configuration_ID
    rs_filename = filename.parent / rs_name

    if not rs_filename.is_file():
        raise FileNotFoundError(
            f'Dataset {filename} required radiosonde {rs_name} but it is not found at {rs_filename}')

    # Create output directory if required
    download_path.mkdir(parents=True, exist_ok=True)

    # Login to the API
    scc = api.SCC(credentials, output_dir=download_path)
    scc.login()

    # Determine day/night
    # TODO

    # Process file
    print(configuration_id)
    measurement = scc.process(filename, configuration_id,
                              monitor=True,
                              rs_filename=rs_filename,
                              lr_filename=None,
                              ov_filename=None)
    scc.logout()
    return measurement


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


def delete_measurements(measurement_ids, settings):
    """ Shortcut function to delete measurements from the SCC. """
    scc = SCC(settings['basic_credentials'], settings['output_dir'], settings['base_url'])
    scc.login(settings['website_credentials'])
    for m_id in measurement_ids:
        logger.info("Deleting %s" % m_id)
        scc.delete_measurement(m_id)
    scc.logout()


def rerun_all(measurement_ids, monitor, settings):
    """ Shortcut function to rerun measurements from the SCC. """

    scc = SCC(settings['basic_credentials'], settings['output_dir'], settings['base_url'])
    scc.login(settings['website_credentials'])
    for m_id in measurement_ids:
        logger.info("Rerunning all products for %s" % m_id)
        scc.rerun_all(m_id, monitor)
    scc.logout()


def rerun_processing(measurement_ids, monitor, settings):
    """ Shortcut function to delete a measurement from the SCC. """

    scc = SCC(settings['basic_credentials'], settings['output_dir'], settings['base_url'])
    scc.login(settings['website_credentials'])
    for m_id in measurement_ids:
        logger.info("Rerunning (optical) processing for %s" % m_id)
        scc.rerun_processing(m_id, monitor)
    scc.logout()


def list_measurements(settings, station=None, system=None, start=None, stop=None, upload_status=None,
                      preprocessing_status=None,
                      optical_processing=None):
    """List all available measurements"""
    scc = SCC(settings['basic_credentials'], settings['output_dir'], settings['base_url'])
    scc.login(settings['website_credentials'])
    ret = scc.list_measurements(station=station, system=system, start=start, stop=stop, upload_status=upload_status,
                                processing_status=preprocessing_status, optical_processing=optical_processing)
    for entry in ret:
        print("%s" % entry.id)
    scc.logout()


def download_measurements(measurement_ids, download_preproc, download_optical, download_graph, settings):
    """Download all measurements for the specified IDs"""
    scc = SCC(settings['basic_credentials'], settings['output_dir'], settings['base_url'])
    scc.login(settings['website_credentials'])
    for m_id in measurement_ids:
        if download_preproc:
            logger.info("Downloading preprocessed files for '%s'" % m_id)
            scc.download_preprocessed(m_id)
            logger.info("Complete")
        if download_optical:
            logger.info("Downloading optical files for '%s'" % m_id)
            scc.download_optical(m_id)
            logger.info("Complete")
        if download_graph:
            logger.info("Downloading profile graph files for '%s'" % m_id)
            scc.download_graphs(m_id)
            logger.info("Complete")
