'''
Helper functions and command for the app's config
Import the `Config` function to use it.
'''

import logging
from configparser import ConfigParser
from pathlib import Path
from typing import List
import platform

from pollyxt_pipelines.LoggerCommand import LoggerCommand


def config_paths() -> List[str]:
    '''
    Returns the config path for each platform.
    The last one returned is the user config path and should be
    used for writing.
    '''

    os_name = platform.system()
    if os_name == 'Windows':
        paths = [
            Path('%APPDATA%/PollyXT_Pipelines/pollyxt_pipelines.ini').resolve()
        ]
    elif os_name == 'Linux':
        paths = [
            Path('/etc/pollyxt_pipelines.ini'),
            Path('~/.config/pollyxt_pipelines.ini').expanduser()
        ]
    else:
        print('Unknown operating system! Using `./pollyxt_pipelines.ini` as config!')
        paths = [
            Path('./pollyxt_pipelines.ini').expanduser()
        ]
    return paths


class Config():
    '''
    Represents the application config. Can be used to read and write from config files.
    '''

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
        '''Write config to disk, persisting any changes'''
        with open(self.paths[-1], 'w') as file:
            self.parser.write(file)


class ConfigCommand(LoggerCommand):
    '''
    Sets or reads a config value.

    config
        {name : Which variable to read/write}
        {value? : If given, this value will be stored}
    '''

    def handle(self):
        super().handle()

        # Parse arguments
        group, name = self.argument('name').split('.')
        value = self.argument('value')

        config = Config()
        if value is None:
            # Read variable
            try:
                value = config[group][name]
                logging.info(value)
            except KeyError:
                logging.error(f'No config value with name {group}.{name}')
                logging.error('Did you forget to define it?')
                return 1
        else:
            config[group][name] = value
            config.write()

        return 0
