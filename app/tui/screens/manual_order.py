"""Manual Order Screen."""

from textual.screen import Screen
from textual.widgets import Static, Input, Button


class ManualOrderScreen(Screen):
    def compose(self):
        yield Static("Manual Order Entry", id="title")
        yield Input(placeholder="Symbol", id="symbol_input")
        yield Input(placeholder="Quantity", id="quantity_input")
        yield Input(placeholder="Price", id="price_input")
        yield Input(placeholder="Order Type (BUY/SELL)", id="order_type_input")
        yield Button("Submit Order", id="submit_btn")