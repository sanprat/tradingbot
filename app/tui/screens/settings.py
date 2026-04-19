"""Settings Screen."""

from textual.screen import Screen
from textual.widgets import Static


class SettingsScreen(Screen):
    def compose(self):
        yield Static("Settings")