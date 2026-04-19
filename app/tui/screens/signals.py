"""Signals Screen."""

from textual.screen import Screen
from textual.widgets import Static, DataTable


class SignalsScreen(Screen):
    def compose(self):
        yield Static("Trading Signals", id="title")
        yield DataTable(id="signals_table")