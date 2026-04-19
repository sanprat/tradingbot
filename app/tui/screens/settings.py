"""Settings Screen."""

from textual.screen import Screen
from textual.widgets import Static, Switch


class SettingsScreen(Screen):
    def compose(self):
        yield Static("Settings", id="title")
        yield Static("Kill Switch", id="kill_switch_label")
        yield Switch(id="kill_switch")
        yield Static("Broker Health: OK", id="broker_health")