'''
Based on SCC-Access by Ioannis Binietoglou licensed under MIT
https://repositories.imaa.cnr.it/public/scc_access/file
'''

import logging
from pathlib import Path

from netCDF4 import Dataset

from pollyxt_pipelines.scc_access import api

BASE_URL = 'https://scc.imaa.cnr.it/'
logger = logging.getLogger(__name__)


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

    # Process file
    print(configuration_id)
    measurement = scc.process(filename, configuration_id,
                              monitor=True,
                              rs_filename=rs_filename,
                              lr_filename=None,
                              ov_filename=None)
    scc.logout()
    return measurement


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
