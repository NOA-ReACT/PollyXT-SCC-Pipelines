'''
Commands to manage locations (show, add, remove)
'''

from cleo import Command
from rich.markdown import Markdown

from pollyxt_pipelines.console import console
from pollyxt_pipelines import locations


class ShowLocations(Command):
    '''
    Print all locations to the terminal

    locations-show
        {--details : Show all variables for each location}
    '''

    def handle(self):

        if not self.option("details"):
            output = ""
            for name in locations.LOCATIONS.keys():
                output += f"* {name}\n"
            console.print(Markdown(output))
        else:
            for location in locations.LOCATIONS.values():
                location.print()
