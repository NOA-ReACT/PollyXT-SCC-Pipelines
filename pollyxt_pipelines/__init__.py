"""
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
"""

import importlib
import importlib.metadata

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import GetRadiosonde
from pollyxt_pipelines.polly_to_scc.commands import CreateSCC
from pollyxt_pipelines.config import ConfigCommand
from pollyxt_pipelines.scc_access.commands import (
    AutoUploadCalibration,
    DeleteSCC,
    DownloadFiles,
    Login,
    RerunSCC,
    SearchDownloadSCC,
    SearchSCC,
    UploadFiles,
    LidarConstantsSCC,
)
from pollyxt_pipelines.locations.commands import LocationPath, ShowLocations
from pollyxt_pipelines.qc_eldec.commands import QCEldec, QCEldecDeleteHistory


def get_package_version():
    """Returns the package version."""
    return importlib.metadata.version("pollyxt_pipelines")


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
    application.add(LidarConstantsSCC())
    application.add(ShowLocations())
    application.add(LocationPath())
    application.add(QCEldec())
    application.add(QCEldecDeleteHistory())
    application.add(AutoUploadCalibration())

    return application


def main():
    app = prepare_cli_application()
    app.run()
