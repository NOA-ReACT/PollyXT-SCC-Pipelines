"""
Console singleton for printing throught the app
"""

from rich.console import Console
from rich.theme import Theme

console_theme = Theme({"info": "cyan", "warn": "yellow", "error": "bold red"})
console = Console(theme=console_theme)
