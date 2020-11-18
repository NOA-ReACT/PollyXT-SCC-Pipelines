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
