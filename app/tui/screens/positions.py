"""Positions Screen."""

from textual.screen import Screen
from textual.widgets import Static, DataTable


class PositionsScreen(Screen):
    def compose(self):
        yield Static("Open Positions", id="title")
        yield DataTable(id="positions_table")