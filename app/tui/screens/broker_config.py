"""Broker Config Screen."""

from textual.screen import Screen
from textual.widgets import Static, Input, Button


class BrokerConfigScreen(Screen):
    def compose(self):
        yield Static("Broker Configuration", id="title")
        yield Static("DHAN Client ID", id="dhan_label")
        yield Input(placeholder="DHAN Client ID", id="dhan_client_id")
        yield Input(placeholder="DHAN API Key", id="dhan_api_key")
        yield Static("Shoonya User ID", id="shoonya_label")
        yield Input(placeholder="Shoonya User ID", id="shoonya_user_id")
        yield Input(placeholder="Shoonya Password", id="shoonya_password")
        yield Static("Webhook Secret", id="webhook_secret_label")
        yield Input(placeholder="Webhook Secret", id="webhook_secret")
        yield Button("Save Configuration", id="save_btn")