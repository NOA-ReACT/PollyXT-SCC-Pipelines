'''
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
'''

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import WRFProfileToCSVs
from pollyxt_pipelines.polly_to_scc.commands import CreateSCCBatch, CreateSCCFile


def prepare_cli_application() -> Application:
    '''
    Entry point, setup the cleo Application and add all commands
    '''

    application = Application()
    application.add(WRFProfileToCSVs())
    application.add(CreateSCCFile())
    application.add(CreateSCCBatch())

    return application


def main():
    app = prepare_cli_application()
    app.run()
