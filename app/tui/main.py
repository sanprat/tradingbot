"""TradingBot TUI Main Application."""

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer

from app.tui.client import TradingBotClient
from app.tui.screens.dashboard import DashboardScreen
from app.tui.screens.positions import PositionsScreen
from app.tui.screens.orders import OrdersScreen
from app.tui.screens.signals import SignalsScreen
from app.tui.screens.manual_order import ManualOrderScreen
from app.tui.screens.settings import SettingsScreen
from app.tui.screens.broker_config import BrokerConfigScreen


class TradingBotApp(App):
    CSS_PATH = "app/tui/styles/app.tcss"
    TITLE = "TradingBot"
    BINDINGS = [
        ("d", "switch_screen('dashboard')", "Dashboard"),
        ("p", "switch_screen('positions')", "Positions"),
        ("o", "switch_screen('orders')", "Orders"),
        ("s", "switch_screen('signals')", "Signals"),
        ("m", "switch_screen('manual')", "Manual"),
        ("c", "switch_screen('broker_config')", "Config"),
        ("k", "toggle_kill_switch", "Kill Switch"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.client = TradingBotClient()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield DashboardScreen("dashboard")
        yield PositionsScreen("positions")
        yield OrdersScreen("orders")
        yield SignalsScreen("signals")
        yield ManualOrderScreen("manual")
        yield SettingsScreen("settings")
        yield BrokerConfigScreen("broker_config")

    def on_mount(self) -> None:
        self.set_interval(5.0, self.refresh_data)

    def refresh_data(self) -> None:
        pass

    def action_toggle_kill_switch(self) -> None:
        pass