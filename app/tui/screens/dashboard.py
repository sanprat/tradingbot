"""Dashboard Screen."""

from textual.screen import Screen
from textual.widgets import Static, DataTable


class DashboardScreen(Screen):
    def compose(self):
        yield Static("Trading Bot Dashboard", id="title")
        yield Static("System Status: Running", id="status")
        yield DataTable(id="positions_table")
        yield DataTable(id="orders_table")