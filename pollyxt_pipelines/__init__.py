'''
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
'''

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import WRFProfileToCSVs
from pollyxt_pipelines.polly_to_scc.commands import CreateSCCBatch, CreateSCC
from pollyxt_pipelines.config import ConfigCommand
from pollyxt_pipelines.scc_access.commands import DownloadFiles, SearchDownloadSCC, SearchSCC, UploadFiles


def prepare_cli_application() -> Application:
    '''
    Entry point, setup the cleo Application and add all commands
    '''

    application = Application()
    application.add(WRFProfileToCSVs())
    application.add(CreateSCC())
    application.add(CreateSCCBatch())
    application.add(ConfigCommand())
    application.add(UploadFiles())
    application.add(DownloadFiles())
    application.add(SearchSCC())
    application.add(SearchDownloadSCC())

    return application


def main():
    app = prepare_cli_application()
    app.run()
