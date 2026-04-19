"""Orders Screen."""

from textual.screen import Screen
from textual.widgets import Static, DataTable


class OrdersScreen(Screen):
    def compose(self):
        yield Static("Orders", id="title")
        yield DataTable(id="orders_table")