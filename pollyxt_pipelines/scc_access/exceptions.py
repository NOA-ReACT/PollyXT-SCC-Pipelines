'''Exceptions that might occur while working with SCC'''


class PageNotAccessible(Exception):
    '''
    Raised when a page cannot be accessed
    '''

    def __init__(self, page_url: str, status_code: int):
        self.page_url = page_url
        self.status_code = status_code

    def __str__(self) -> str:
        return f'Page {self.page_url} not accessible (status code {self.status_code})'


class WrongCredentialsException(Exception):
    '''Raised when login() fails due to wrong credentials'''
    pass


class SCCError(Exception):
    '''Raised when an error message from SCC is parsed from the page body'''

    def __init__(self, errors: str) -> None:
        self.errors = errors

    def __str__(self) -> str:
        return self.errors


class UnexpectedResponse(Exception):
    '''Raised when the response is not OK and we don't have a concrete reason for it'''
    pass
