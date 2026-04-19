"""Broker Config Screen."""

from textual.screen import Screen
from textual.widgets import Static


class BrokerConfigScreen(Screen):
    def compose(self):
        yield Static("Broker Config")