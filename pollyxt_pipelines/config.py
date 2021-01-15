"""
Helper functions and command for the app's config
Import the `Config` function to use it.
"""

import logging
from configparser import ConfigParser
from pathlib import Path
from typing import List
import platform

from cleo import Command

from pollyxt_pipelines.console import console


def config_paths() -> List[str]:
    """
    Returns the config path for each platform.
    The last one returned is the user config path and should be
    used for writing.
    """

    os_name = platform.system()
    if os_name == "Windows":
        paths = [Path("%APPDATA%/PollyXT_Pipelines/pollyxt_pipelines.ini").resolve()]
    elif os_name == "Linux":
        paths = [
            Path("/etc/pollyxt_pipelines/pollyxt_pipelines.ini"),
            Path("~/.config/pollyxt_pipelines/pollyxt_pipelines.ini").expanduser(),
        ]
    else:
        print("Unknown operating system! Using `./pollyxt_pipelines.ini` as config!")
        paths = [Path("./pollyxt_pipelines.ini").expanduser()]
    return paths


class Config:
    """
    Represents the application config. Can be used to read and write from config files.
    """

    def __init__(self):
        self.paths = config_paths()
        self.parser = ConfigParser()
        self.parser.read(self.paths)

    def __getitem__(self, name) -> str:
        if name not in self.parser:
            self.parser[name] = {}
        return self.parser[name]

    def __setitem__(self, name, value):
        if name not in self.parser:
            self.parser[name] = {}
        self.parser[name] = value

    def write(self):
        """Write config to disk, persisting any changes"""
        Path(self.paths[-1]).parent.mkdir(exist_ok=True, parents=True)
        with open(self.paths[-1], "w") as file:
            self.parser.write(file)


class ConfigCommand(Command):
    """
    Sets or reads a config value.

    config
        {name : Which variable to read/write}
        {value? : If given, this value will be stored}
    """

    def handle(self):
        # Parse arguments
        try:
            group, name = self.argument("name").split(".")
        except ValueError:
            console.print(
                "[error]Variable names should be in the[/error] GROUP.NAME [error]format. For example,[/error] `auth.username`"
            )
            return 1
        value = self.argument("value")

        config = Config()
        if value is None:
            # Read variable
            try:
                value = config[group][name]
                console.print(value)
            except KeyError:
                console.print(f"[error]No config value with name[/error] {group}.{name}")
                console.print("Did you forget to define it?")
                return 1
        else:
            config[group][name] = value
            config.write()

        return 0


def print_login_error():
    """
    Use this to print an error when the user needs to login.
    """

    console.print("[error]Credentials not found in config![/error]")
    console.print(
        "Use `pollyxt_pipelines login` to provide your SCC credentials and run this command again."
    )
