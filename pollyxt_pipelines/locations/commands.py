"""
Commands to manage locations (show, add, remove)
"""

from cleo import Command
from rich.markdown import Markdown

from pollyxt_pipelines.console import console
from pollyxt_pipelines import locations, config


class ShowLocations(Command):
    """
    Print all locations to the terminal

    locations-show
        {--details : Show all variables for each location}
    """

    def handle(self):

        if not self.option("details"):
            output = ""
            for name in locations.LOCATIONS.keys():
                output += f"* {name}\n"
            console.print(Markdown(output))
        else:
            for location in locations.LOCATIONS.values():
                location.print()


class LocationPath(Command):
    """
    Prints the path to the file(s) where you can input a custom location

    locations-path
        {--user : Show only the user's config file (ignore the system file). This only makes sense on Linux.}
    """

    def handle(self):
        config_paths = config.config_paths()

        if self.option("user"):
            console.print(config_paths[-1].parent / "locations.ini")
        else:
            for path in config_paths:
                console.print(path.parent / "locations.ini")
