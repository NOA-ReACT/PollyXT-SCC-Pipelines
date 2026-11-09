"""
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
"""

import importlib
import importlib.metadata
import logging

from cleo import Application
from rich.logging import RichHandler

from pollyxt_pipelines.console import console

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


def setup_cli_logging(level: int = logging.INFO):
    """
    Show the library's log messages in the terminal, through the `rich` console.
    Library users configure logging themselves.
    """

    handler = RichHandler(
        console=console, show_time=False, show_path=False, markup=False
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    package_logger = logging.getLogger("pollyxt_pipelines")
    package_logger.addHandler(handler)
    package_logger.setLevel(level)


def main():
    setup_cli_logging()
    app = prepare_cli_application()
    app.run()
