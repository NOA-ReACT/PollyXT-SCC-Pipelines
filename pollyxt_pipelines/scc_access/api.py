import urllib.parse as urlparse
import datetime
import os
import re
import logging
from io import BytesIO
import sys
import time
from zipfile import ZipFile

import requests

from pollyxt_pipelines.config import Config


BASE_URL = 'https://scc.imaa.cnr.it/'
logger = logging.getLogger(__name__)


# The regex to find the measurement id from the measurement page
# This should be read from the uploaded file, but would require an extra NetCDF module.
# {12, 15} to handle both old- and new-style measurement ids.
regex = "<h3>Measurement (?P<measurement_id>.{12,15}) <small>"


class WrongCredentialsException(Exception):
    '''Raised when login() fails due to wrong credentials'''
    pass


class SCC:
    """A simple class that will attempt to upload a file on the SCC server.

    The uploading is done by simulating a normal browser session. In the current
    version no check is performed, and no feedback is given if the upload
    was successful. If everything is setup correctly, it will work.
    """

    credentials: SCC_Credentials

    def __init__(self, credentials: SCC_Credentials, output_dir: str):
        self.credentials = credentials
        self.output_dir = output_dir

        # Create session
        self.session = requests.Session()
        self.session.auth = (credentials.http_auth_user, credentials.http_auth_password)
        self.session.verify = True

        # Generate URLs and patterns
        self.login_url = urlparse.urljoin(BASE_URL, 'accounts/login/')
        self.logout_url = urlparse.urljoin(BASE_URL, 'accounts/logout/')
        self.list_measurements_url = urlparse.urljoin(
            BASE_URL, 'data_processing/measurements/')

        self.upload_url = urlparse.urljoin(BASE_URL, 'data_processing/measurements/quick/')
        self.download_hirelpp_pattern = urlparse.urljoin(BASE_URL,
                                                         'data_processing/measurements/{0}/download-hirelpp/')
        self.download_cloudmask_pattern = urlparse.urljoin(BASE_URL,
                                                           'data_processing/measurements/{0}/download-cloudmask/')

        self.download_preprocessed_pattern = urlparse.urljoin(BASE_URL,
                                                              'data_processing/measurements/{0}/download-preprocessed/')
        self.download_optical_pattern = urlparse.urljoin(BASE_URL,
                                                         'data_processing/measurements/{0}/download-optical/')
        self.download_graph_pattern = urlparse.urljoin(BASE_URL,
                                                       'data_processing/measurements/{0}/download-plots/')
        self.download_elic_pattern = urlparse.urljoin(BASE_URL,
                                                      'data_processing/measurements/{0}/download-elic/')
        self.delete_measurement_pattern = urlparse.urljoin(
            BASE_URL, 'admin/database/measurements/{0}/delete/')

        self.api_base_url = urlparse.urljoin(BASE_URL, 'api/v1/')
        self.api_measurement_pattern = urlparse.urljoin(self.api_base_url, 'measurements/{0}/')
        self.api_measurements_url = urlparse.urljoin(self.api_base_url, 'measurements')
        self.api_sounding_search_pattern = urlparse.urljoin(
            self.api_base_url, 'sounding_files/?filename={0}')
        self.api_lidarratio_search_pattern = urlparse.urljoin(
            self.api_base_url, 'lidarratio_files/?filename={0}')
        self.api_overlap_search_pattern = urlparse.urljoin(
            self.api_base_url, 'overlap_files/?filename={0}')

    def login(self):
        """ Login to SCC. """
        login_credentials = {'username': self.credentials.username,
                             'password': self.credentials.password}

        logger.debug("Accessing login page at %s." % self.login_url)

        # Get upload form
        login_page = self.session.get(self.login_url)

        if not login_page.ok:
            raise self.PageNotAccessibleError(
                'Could not access login pages. Status code %s' % login_page.status_code)

        logger.debug("Submitting credentials.")
        # Submit the login data
        login_submit = self.session.post(self.login_url,
                                         data=login_credentials,
                                         headers={'X-CSRFToken': login_page.cookies['csrftoken'],
                                                  'referer': self.login_url})

        if 'Wrong username or password' in login_submit.text:
            raise WrongCredentialsException()

        return login_submit

    def logout(self):
        """ Logout from SCC """
        return self.session.get(self.logout_url, stream=True)

    def upload_file(self, filename, system_id, rs_filename=None, ov_filename=None, lr_filename=None):
        """ Upload a filename for processing with a specific system. If the
        upload is successful, it returns the measurement id. """
        # Get submit page
        upload_page = self.session.get(self.upload_url)

        # Submit the data
        upload_data = {'system': system_id}
        files = {'data': open(filename, 'rb')}

        if rs_filename is not None:
            ancillary_file, _ = self.get_ancillary(rs_filename, 'sounding')

            if ancillary_file.already_on_scc:
                logger.warning(
                    "Sounding file {0.filename} already on the SCC with id {0.id}. Ignoring it.".format(ancillary_file))
            else:
                logger.debug('Adding sounding file %s' % rs_filename)
                files['sounding_file'] = open(rs_filename, 'rb')

        if ov_filename is not None:
            ancillary_file, _ = self.get_ancillary(ov_filename, 'overlap')

            if ancillary_file.already_on_scc:
                logger.warning(
                    "Overlap file {0.filename} already on the SCC with id {0.id}. Ignoring it.".format(ancillary_file))
            else:
                logger.debug('Adding overlap file %s' % ov_filename)
                files['overlap_file'] = open(ov_filename, 'rb')

        if lr_filename is not None:
            ancillary_file, _ = self.get_ancillary(lr_filename, 'lidarratio')

            if ancillary_file.already_on_scc:
                logger.warning(
                    "Lidar ratio file {0.filename} already on the SCC with id {0.id}. Ignoring it.".format(ancillary_file))
            else:
                logger.debug('Adding lidar ratio file %s' % lr_filename)
                files['lidar_ratio_file'] = open(lr_filename, 'rb')

        logger.info("Uploading of file(s) %s started." % filename)

        upload_submit = self.session.post(self.upload_url,
                                          data=upload_data,
                                          files=files,
                                          headers={'X-CSRFToken': upload_page.cookies['csrftoken'],
                                                   'referer': self.upload_url})

        if upload_submit.status_code != 200:
            logger.warning("Connection error. Status code: %s" % upload_submit.status_code)
            return False

        # Check if there was a redirect to a new page.
        if upload_submit.url == self.upload_url:
            measurement_id = False
            logger.error(upload_submit.text)
            logger.error("Uploaded file(s) rejected! Try to upload manually to see the error.")
        else:
            measurement_id = re.findall(regex, upload_submit.text)[0]
            logger.info("Successfully uploaded measurement with id %s." % measurement_id)

        return measurement_id

    def download_files(self, measurement_id, subdir, download_url):
        """ Downloads some files from the download_url to the specified
        subdir. This method is used to download preprocessed file, optical
        files etc.
        """
        # TODO: Make downloading more robust (e.g. in case that files do not exist on server).
        # Get the file
        request = self.session.get(download_url, stream=True)

        if not request.ok:
            raise Exception("Could not download files for measurement '%s'" % measurement_id)

        # Create the dir if it does not exist
        local_dir = os.path.join(self.output_dir, measurement_id, subdir)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # Save the file by chunk, needed if the file is big.
        memory_file = BytesIO()

        for chunk in request.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                memory_file.write(chunk)
                memory_file.flush()

        zip_file = ZipFile(memory_file)

        for ziped_name in zip_file.namelist():
            basename = os.path.basename(ziped_name)

            local_file = os.path.join(local_dir, basename)

            with open(local_file, 'wb') as f:
                f.write(zip_file.read(ziped_name))

    def download_hirelpp(self, measurement_id):
        """ Download HiRElPP files for the measurement id. """
        # Construct the download url
        download_url = self.download_hirelpp_pattern.format(measurement_id)
        self.download_files(measurement_id, 'hirelpp', download_url)

    def download_cloudmask(self, measurement_id):
        """ Download preprocessed files for the measurement id. """
        # Construct the download url
        download_url = self.download_cloudmask_pattern.format(measurement_id)
        self.download_files(measurement_id, 'cloudmask', download_url)

    def download_preprocessed(self, measurement_id):
        """ Download preprocessed files for the measurement id. """
        # Construct the download url
        download_url = self.download_preprocessed_pattern.format(measurement_id)
        self.download_files(measurement_id, 'scc_preprocessed', download_url)

    def download_optical(self, measurement_id):
        """ Download optical files for the measurement id. """
        # Construct the download url
        download_url = self.download_optical_pattern.format(measurement_id)
        self.download_files(measurement_id, 'scc_optical', download_url)

    def download_graphs(self, measurement_id):
        """ Download profile graphs for the measurement id. """
        # Construct the download url
        download_url = self.download_graph_pattern.format(measurement_id)
        self.download_files(measurement_id, 'scc_plots', download_url)

    def download_elic(self, measurement_id):
        """ Download profile graphs for the measurement id. """
        # Construct the download url
        download_url = self.download_elic_pattern.format(measurement_id)
        self.download_files(measurement_id, 'elic', download_url)

    def rerun_processing(self, measurement_id, monitor=True):
        measurement, status = self.get_measurement(measurement_id)

        if measurement:
            request = self.session.get(measurement.rerun_processing_url, stream=True)

            if request.status_code != 200:
                logger.error(
                    "Could not rerun processing for %s. Status code: %s" % (measurement_id, request.status_code))
                return

            if monitor:
                self.monitor_processing(measurement_id)

    def rerun_all(self, measurement_id, monitor=True):
        logger.debug("Started rerun_all procedure.")

        logger.debug("Getting measurement %s" % measurement_id)
        measurement, status = self.get_measurement(measurement_id)

        if measurement:
            logger.debug("Attempting to rerun all processing through %s." %
                         measurement.rerun_all_url)

            request = self.session.get(measurement.rerun_all_url, stream=True)

            if request.status_code != 200:
                logger.error("Could not rerun pre processing for %s. Status code: %s" %
                             (measurement_id, request.status_code))
                return

            if monitor:
                self.monitor_processing(measurement_id)

    def process(self, filename, system_id, monitor, rs_filename=None, lr_filename=None, ov_filename=None):
        """ Upload a file for processing and wait for the processing to finish.
        If the processing is successful, it will download all produced files.
        """
        logger.info("--- Processing started on %s. ---" % datetime.datetime.now())
        # Upload file
        logger.info("--- Uploading file")
        measurement_id = self.upload_file(filename, system_id,
                                          rs_filename=rs_filename,
                                          lr_filename=lr_filename,
                                          ov_filename=ov_filename)

        if measurement_id and monitor:
            logger.info("--- Monitoring processing")
            return self.monitor_processing(measurement_id)

        return None

    def monitor_processing(self, measurement_id):
        """ Monitor the processing progress of a measurement id"""

        # try to deal with error 404
        error_count = 0
        error_max = 6
        time_sleep = 10

        # try to wait for measurement to appear in API
        measurement = None
        logger.info("Looking for measurement %s in SCC", measurement_id)
        while error_count < error_max:
            time.sleep(time_sleep)
            measurement, status = self.get_measurement(measurement_id)
            if status != 200 and error_count < error_max:
                logger.error("Measurement not found. waiting %ds", time_sleep)
                error_count += 1
            else:
                break

        if error_count == error_max:
            logger.critical("Measurement %s doesn't seem to exist", measurement_id)
            sys.exit(1)

        logger.info('Measurement %s found', measurement_id)

        if measurement is not None:
            while measurement.is_running:
                logger.info("Measurement is being processed. Please wait.")
                time.sleep(10)
                measurement, status = self.get_measurement(measurement_id)

            logger.info("Measurement processing finished.")
            if measurement.hirelpp == 127:
                logger.info("Downloading hirelpp files.")
                self.download_hirelpp(measurement_id)
            if measurement.cloudmask == 127:
                logger.info("Downloading cloudmask files.")
                self.download_cloudmask(measurement_id)
            if measurement.elpp == 127:
                logger.info("Downloading preprocessed files.")
                self.download_preprocessed(measurement_id)
            if measurement.elda == 127:
                logger.info("Downloading optical files.")
                self.download_optical(measurement_id)
                logger.info("Downloading graphs.")
                self.download_graphs(measurement_id)
            if measurement.elic == 127:
                logger.info("Downloading preprocessed files.")
                self.download_elic(measurement_id)
            logger.info("--- Processing finished. ---")
        return measurement

    def get_measurement(self, measurement_id):
        measurement_url = self.api_measurement_pattern.format(measurement_id)
        logger.debug("Measurement API URL: %s" % measurement_url)

        response = self.session.get(measurement_url)

        if not response.ok:
            logger.error('Could not access API. Status code %s.' % response.status_code)
            return None, response.status_code

        response_dict = response.json()

        if response_dict:
            measurement = Measurement(BASE_URL, response_dict)
            return measurement, response.status_code
        else:
            logger.error("No measurement with id %s found on the SCC." % measurement_id)
            return None, response.status_code

    def delete_measurement(self, measurement_id):
        """ Deletes a measurement with the provided measurement id. The user
        should have the appropriate permissions.

        The procedures is performed directly through the web interface and
        NOT through the API.
        """
        # Get the measurement object
        measurement, _ = self.get_measurement(measurement_id)

        # Check that it exists
        if measurement is None:
            logger.warning("Nothing to delete.")
            return None

        # Go the the page confirming the deletion
        delete_url = self.delete_measurement_pattern.format(measurement_id)

        confirm_page = self.session.get(delete_url)

        # Check that the page opened properly
        if confirm_page.status_code != 200:
            logger.warning("Could not open delete page. Status: {0}".format(
                confirm_page.status_code))
            return None

        # Delete the measurement
        delete_page = self.session.post(delete_url,
                                        data={'post': 'yes'},
                                        headers={'X-CSRFToken': confirm_page.cookies['csrftoken'],
                                                 'referer': delete_url}
                                        )
        if not delete_page.ok:
            logger.warning("Something went wrong. Delete page status: {0}".format(
                delete_page.status_code))
            return None

        logger.info("Deleted measurement {0}".format(measurement_id))
        return True

    def available_measurements(self):
        """ Get a list of available measurement on the SCC. """
        response = self.session.get(self.api_measurements_url)
        response_dict = response.json()

        if response_dict:
            measurement_list = response_dict['objects']
            measurements = [Measurement(BASE_URL, measurement_dict)
                            for measurement_dict in measurement_list]
            logger.info("Found %s measurements on the SCC." % len(measurements))
        else:
            logger.warning(
                "No response received from the SCC when asked for available measurements.")
            measurements = None

        return measurements

    def list_measurements(self, station=None, system=None, start=None, stop=None, upload_status=None,
                          processing_status=None, optical_processing=None):

        # TODO: Change this to work through the API

        # Need to set to empty string if not specified, we won't get any results
        params = {
            "station": station if station is not None else "",
            "system": system if system is not None else "",
            "stop": stop if stop is not None else "",
            "start": start if start is not None else "",
            "upload_status": upload_status if upload_status is not None else "",
            "preprocessing_status": processing_status if processing_status is not None else "",
            "optical_processing_status": optical_processing if optical_processing is not None else ""
        }

        response_txt = self.session.get(self.list_measurements_url, params=params).text
        tbl_rgx = re.compile(r'<table id="measurements">(.*?)</table>', re.DOTALL)
        entry_rgx = re.compile(r'<tr>(.*?)</tr>', re.DOTALL)
        measurement_rgx = re.compile(
            r'.*?<td><a[^>]*>(\w+)</a>.*?<td>.*?<td>([\w-]+ [\w:]+)</td>.*<td data-order="([-]?\d+),([-]?\d+),([-]?\d+)".*',
            re.DOTALL)
        matches = tbl_rgx.findall(response_txt)
        if len(matches) != 1:
            return []

        ret = []
        for entry in entry_rgx.finditer(matches[0]):
            m = measurement_rgx.match(entry.string[entry.start(0):entry.end(0)])
            if m:
                name, date, upload, preproc, optical = m.groups()
                ret.append(
                    Measurement(BASE_URL, {"id": name, "upload": int(upload), "pre_processing": int(preproc),
                                           "processing": int(optical)}))

        return ret

    def measurement_id_for_date(self, t1, call_sign, base_number=0):
        """ Give the first available measurement id on the SCC for the specific
        date.
        """
        date_str = t1.strftime('%Y%m%d')
        base_id = "%s%s" % (date_str, call_sign)
        search_url = urlparse.urljoin(
            self.api_base_url, 'measurements/?id__startswith=%s' % base_id)

        response = self.session.get(search_url)

        response_dict = response.json()

        measurement_id = None

        if response_dict:
            measurement_list = response_dict['objects']

            if len(measurement_list) == 100:
                raise ValueError('No available measurement id found.')

            existing_ids = [measurement_dict['id'] for measurement_dict in measurement_list]

            measurement_number = base_number
            measurement_id = "%s%02i" % (base_id, measurement_number)

            while measurement_id in existing_ids:
                measurement_number = measurement_number + 1
                measurement_id = "%s%02i" % (base_id, measurement_number)

        return measurement_id

    def get_ancillary(self, file_path, file_type):
        """
        Try to get the ancillary file data from the SCC API.

        The result will always be an API object. If the file does not exist, the .exists property is set to False.

        Parameters
        ----------
        file_path : str
           Path  of the uploaded file.
        file_type : str
           Type of ancillary file. One of 'sounding', 'overlap', 'lidarratio'.

        Returns
        : AncillaryFile
           The api object.
        """
        assert file_type in ['sounding', 'overlap', 'lidarratio']

        filename = os.path.basename(file_path)

        if file_type == 'sounding':
            file_url = self.api_sounding_search_pattern.format(filename)
        elif file_type == 'overlap':
            file_url = self.api_overlap_search_pattern.format(filename)
        else:
            file_url = self.api_lidarratio_search_pattern.format(filename)

        response = self.session.get(file_url)

        if not response.ok:
            logger.error('Could not access API. Status code %s.' % response.status_code)
            return None, response.status_code

        response_dict = response.json()
        object_list = response_dict['objects']

        logger.debug("Ancillary file JSON: {0}".format(object_list))

        if object_list:
            # Assume only one file is returned
            ancillary_file = AncillaryFile(self.api_base_url, object_list[0])
        else:
            ancillary_file = AncillaryFile(self.api_base_url, None)  # Create an empty object

        return ancillary_file, response.status_code

    class PageNotAccessibleError(RuntimeError):
        pass


class ApiObject(object):
    """ A generic class object. """

    def __init__(self, base_url, dict_response):
        BASE_URL = base_url

        if dict_response:
            # Add the dictionary key value pairs as object properties
            for key, value in dict_response.items():
                # logger.debug('Setting key {0} to value {1}'.format(key, value))
                try:
                    setattr(self, key, value)
                except:
                    logger.warning('Could not set attribute {0} to value {1}'.format(key, value))
            self.exists = True
        else:
            self.exists = False


class Measurement(ApiObject):
    """ This class represents the measurement object as returned in the SCC API.
    """

    @property
    def rerun_processing_url(self):
        url_pattern = urlparse.urljoin(
            BASE_URL, 'data_processing/measurements/{0}/rerun-elda/')
        return url_pattern.format(self.id)

    @property
    def rerun_all_url(self):
        ulr_pattern = urlparse.urljoin(BASE_URL, 'data_processing/measurements/{0}/rerun-all/')
        return ulr_pattern.format(self.id)

    def __str__(self):
        return "%s: %s, %s, %s" % (self.id,
                                   self.upload,
                                   self.pre_processing,
                                   self.processing)


class AncillaryFile(ApiObject):
    """ This class represents the ancilalry file object as returned in the SCC API.
    """
    @property
    def already_on_scc(self):
        if self.exists is False:
            return False

        return not self.status == 'missing'

    def __str__(self):
        return "%s: %s, %s" % (self.id,
                               self.filename,
                               self.status)
