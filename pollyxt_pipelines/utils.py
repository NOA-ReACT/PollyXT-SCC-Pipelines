'''Various helper functions that fit nowhere'''


def bool_to_emoji(x: bool) -> str:
    '''
    Returns a boolean as a checkmark or as an X.

    Contains color tags for use with the `rich` library.
    '''
    if x:
        return '[green]✔[/green]'
    else:
        return '[red]✘[/red]'


def option_to_bool(x: bool, absence_value: bool):
    '''
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
    '''

    if absence_value:
        return not x
    return x
