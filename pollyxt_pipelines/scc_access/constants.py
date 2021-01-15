"""
This file contains the endpoint paths of SCC
Author: Iannis Binietoglou <i.binietoglou@impworks.gr> for `scc-access` project
"""

import urllib.parse as urlparse

# Base URL for SCC
BASE_URL = "https://scc.imaa.cnr.it/"

# Session management (login/logout)
login_url = urlparse.urljoin(BASE_URL, "accounts/login/")
logout_url = urlparse.urljoin(BASE_URL, "accounts/logout/")

# Measurement mnagement
list_measurements_url = urlparse.urljoin(BASE_URL, "admin/database/measurements/")
upload_url = urlparse.urljoin(BASE_URL, "data_processing/measurements/quick/")
delete_measurement_pattern = urlparse.urljoin(BASE_URL, "admin/database/measurements/{0}/delete/")
rerun_measurement_url = urlparse.urljoin(BASE_URL, "/admin/database/measurements/")

# Downloading of products
download_hirelpp_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-hirelpp/"
)
download_cloudmask_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-cloudmask/"
)

download_preprocessed_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-preprocessed/"
)
download_optical_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-optical/"
)
download_graph_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-plots/"
)
download_elic_pattern = urlparse.urljoin(
    BASE_URL, "data_processing/measurements/{0}/download-elic/"
)

# API calls
api_base_url = urlparse.urljoin(BASE_URL, "api/v1/")
api_measurement_pattern = urlparse.urljoin(api_base_url, "measurements/{0}/")
api_measurements_url = urlparse.urljoin(api_base_url, "measurements")
api_sounding_search_pattern = urlparse.urljoin(api_base_url, "sounding_files/?filename={0}")
api_lidarratio_search_pattern = urlparse.urljoin(api_base_url, "lidarratio_files/?filename={0}")
api_overlap_search_pattern = urlparse.urljoin(api_base_url, "overlap_files/?filename={0}")
