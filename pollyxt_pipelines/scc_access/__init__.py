from pollyxt_pipelines.config import Config


class SCC_Credentials():
    '''
    Contains all required credentials to authenticate with SCC
    '''
    http_auth_user: str
    http_auth_password: str
    username: str
    password: str

    def __init__(self, config: Config):
        self.http_auth_user = config['http']['username']
        self.http_auth_password = config['http']['password']
        self.username = config['auth']['username']
        self.password = config['auth']['password']
