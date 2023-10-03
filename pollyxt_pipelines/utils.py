"""Various helper functions that fit nowhere"""

from typing import List, Union, Optional
from datetime import datetime, timedelta
import re


def bool_to_emoji(x: bool) -> str:
    """
    Returns a boolean as a checkmark or as an X.

    Contains color tags for use with the `rich` library.
    """
    if x:
        return "[green]✔[/green]"
    else:
        return "[red]✘[/red]"


def option_to_bool(x: bool, absence_value: bool):
    """
    Converts cleo's options into booleans. You can use this with options like
    `--enable-feature` or `--no-feature` to avoid flipping the boolean everytime

    Parameters
    ---
    - x (bool, None): The value to convert
    - absence_value (bool): What to return in case `x` is None.

    Examples
    ---
    ```python
    # For options like `--no-feature` you should set `absence_value` to False:
    option_to_bool(self.option('no-feature'), True) # Returns False only if option is set

    # For options like `--enable-feature` you should set `absence_value` to False:
    option_to_bool(self.option('enable-feature), True) # Returns True only if option is set
    """

    if absence_value:
        return not x
    return x


def ints_to_strs(arr: List[int]) -> List[str]:
    """
    Convert a list of `int` to a list of `str`.
    """
    return [str(x) for x in arr]


def ints_to_csv(arr: List[int]) -> str:
    """
    Convert a list of `int` to a string with comma separated values
    """
    return ", ".join(ints_to_strs(arr))


def date_option_to_datetime(today: datetime, string: str) -> datetime:
    """
    Given a datetime and a string, this function will do one of the following:
        - If the `string` contains only time info (in HH:MM or HH:MM:SS format), the function will return `today` with the hours
          and minutes set to the values from `string`.
        - If `string` contains both date and time (in YYYY-mm-DD HH:MM or YYYY-mm-DD HH:MM:SS format),
          the function will return this as a datetime object. The `today` object will be ignored
    This function is used to parse command line options that allow the user to input either time or date and time when
    trimming files.

    Args:
        today: A date to use if `string` contains only time information.
        string: Time in "HH:MM" or date and time in "YYYY-mm-DD HH:MM"

    Returns:
        The string parsed as a datetime object

    Throws:
        ValueError: When the string is not in an acceptable format
    """

    # Try to determine the string's format
    date_seconds_match = re.search(
        r"^\d{4}-[01]\d-[0123]\d_[012]\d:[0-5]\d:[0-5]\d", string
    )
    if date_seconds_match is not None:
        # Strings seems to be in YYYY-mm-DD HH:MM:SS format
        return datetime.strptime(string, "%Y-%m-%d_%H:%M:%S")

    date_match = re.search(r"^\d{4}-[01]\d-[0123]\d_[012]\d:[0-5]\d", string)
    if date_match is not None:
        # String seems to be in YYYY-mm-DD HH:MM format
        return datetime.strptime(string, "%Y-%m-%d_%H:%M")

    time_seconds_match = re.search(r"^[012]\d:[0-5]\d:[0-5]\d", string)
    if time_seconds_match is not None:
        # String seems to be in HH:MM:SS format, replace in `today` and return
        hour, minute, second = [int(x) for x in string.split(":")]
        return today.replace(hour=hour, minute=minute, second=second)

    time_match = re.search(r"^[012]\d:[0-5]\d", string)
    if time_match is not None:
        # String is only time, replace in `today` and return
        hour, minute = [int(x) for x in string.split(":")]
        return today.replace(hour=hour, minute=minute)

    minutes_match = re.search(r"^XX:[0-5]\d$", string)
    if minutes_match is not None:
        minute = int(string[-2:])
        if today.replace(minute=minute) < today:
            return (today + timedelta(hours=1)).replace(minute=minute)
        else:
            return today.replace(minute=minute)

    raise ValueError("`string` is neither in XX:MM, HH:MM nor YYYY-mm-DD HH:MM format!")


def parse_into_string_or_integer_list(
    text_values: Optional[str],
) -> Optional[Union[List[int], List[str]]]:
    """
    Parses comma-seperated values into a list of either integers or string.
    For the resulting list to be an integer one, all values must be integers (0-9)
    If input is none, returns none.
    """

    if text_values is None:
        return None

    values = [x.strip() for x in text_values.split(",")]
    if all([re.match(r"^\d+$", x) for x in values]):
        return [int(x) for x in values]
    else:
        return values
