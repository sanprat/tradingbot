"""Signals Screen."""

from textual.screen import Screen
from textual.widgets import Static


class SignalsScreen(Screen):
    def compose(self):
        yield Static("Signals")