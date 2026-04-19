"""Manual Order Screen."""

from textual.screen import Screen
from textual.widgets import Static


class ManualOrderScreen(Screen):
    def compose(self):
        yield Static("Manual Order")