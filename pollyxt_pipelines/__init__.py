"""
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
"""

import pkg_resources

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import GetRadiosonde
from pollyxt_pipelines.polly_to_scc.commands import CreateSCC
from pollyxt_pipelines.config import ConfigCommand
from pollyxt_pipelines.scc_access.commands import (
    DeleteSCC,
    DownloadFiles,
    Login,
    RerunSCC,
    SearchDownloadSCC,
    SearchSCC,
    UploadFiles,
)
from pollyxt_pipelines.locations.commands import LocationPath, ShowLocations


def get_package_version():
    """
    Returns the package version. If the package is not installed, it will
    return "Development Version".
    """
    try:
        version = pkg_resources.get_distribution("sodust").version
    except pkg_resources.DistributionNotFound:
        version = "Development Version (not installed!)"
    return version


def prepare_cli_application() -> Application:
    """
    Entry point, setup the cleo Application and add all commands
    """

    application = Application("pollyxt_pipelines", get_package_version())
    application.add(GetRadiosonde())
    application.add(CreateSCC())
    application.add(ConfigCommand())
    application.add(Login())
    application.add(UploadFiles())
    application.add(DownloadFiles())
    application.add(DeleteSCC())
    application.add(RerunSCC())
    application.add(SearchSCC())
    application.add(SearchDownloadSCC())
    application.add(ShowLocations())
    application.add(LocationPath())

    return application


def main():
    app = prepare_cli_application()
    app.run()
