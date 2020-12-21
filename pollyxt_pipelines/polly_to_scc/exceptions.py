from datetime import datetime


class StartingTimeOutsideFile(Exception):
    '''
    Raised when the requested starting time is outside the file
    '''

    def __init__(self, start: datetime, end: datetime, requested: datetime):
        super(self)

        self.start = start
        self.end = end
        self.requested = requested

    def __str__(self) -> str:
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        requested = self.requested.strftime("%H:%M")
        return f'The requested start time {requested} is outside the file\'s range ({start}-{end})'