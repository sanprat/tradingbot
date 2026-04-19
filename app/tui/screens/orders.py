"""Orders Screen."""

from textual.screen import Screen
from textual.widgets import Static


class OrdersScreen(Screen):
    def compose(self):
        yield Static("Orders")