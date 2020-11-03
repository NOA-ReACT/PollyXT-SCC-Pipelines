'''
Entry point for the application, mainly contains cleo setup
Author: Thanasis Georgiou <ageorgiou@noa.gr>
'''

from cleo import Application

from pollyxt_pipelines.radiosondes.commands import WRFProfileToCSVs


def prepare_cli_application() -> Application:
    '''
    Entry point, setup the cleo Application and add all commands
    '''

    application = Application()
    application.add(WRFProfileToCSVs())

    return application
