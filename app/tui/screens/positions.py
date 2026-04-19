"""Positions Screen."""

from textual.screen import Screen
from textual.widgets import Static


class PositionsScreen(Screen):
    def compose(self):
        yield Static("Positions")