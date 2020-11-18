from cleo import Command
import coloredlogs


class LoggerCommand(Command):
    '''
    Extends the cleo command to integrate verbosity level with python's logging and coloredlogs
    '''

    def handle(self):
        if self.io.is_verbose():
            coloredlogs.install(level='DEBUG', fmt='%(asctime)s %(message)s')
        else:
            coloredlogs.install(level='INFO', fmt='%(message)s')
