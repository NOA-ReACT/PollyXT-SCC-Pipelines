'''
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
'''

import pkg_resources

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import WRFProfileToCSVs
from pollyxt_pipelines.polly_to_scc.commands import CreateSCCBatch, CreateSCC
from pollyxt_pipelines.config import ConfigCommand
from pollyxt_pipelines.scc_access.commands import DeleteSCC, DownloadFiles, RerunSCC, SearchDownloadSCC, SearchSCC, UploadFiles


def get_package_version():
    """
    Returns the package version. If the package is not installed, it will
    return "Development Version".
    """
    try:
        version = pkg_resources.get_distribution('sodust').version
    except pkg_resources.DistributionNotFound:
        version = "Development Version (not installed!)"
    return version


def prepare_cli_application() -> Application:
    '''
    Entry point, setup the cleo Application and add all commands
    '''

    application = Application('pollyxt_pipelines', get_package_version())
    application.add(WRFProfileToCSVs())
    application.add(CreateSCC())
    application.add(CreateSCCBatch())
    application.add(ConfigCommand())
    application.add(UploadFiles())
    application.add(DownloadFiles())
    application.add(DeleteSCC())
    application.add(RerunSCC())
    application.add(SearchSCC())
    application.add(SearchDownloadSCC())

    return application


def main():
    app = prepare_cli_application()
    app.run()
