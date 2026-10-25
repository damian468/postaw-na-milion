"""Menu główne z animowanym logo i deszczem pieniędzy."""

# Klasy Textual
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

# Format kwot
from pnm.config import format_money, bundles_to_money, START_BUNDLES
# Escapowanie znaków markupu (imię gracza)
from rich.markup import escape
# Zdarzenia modeli
from pnm.model.observable import Event, EventType
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Widżety
from pnm.view.tui.widgets import ArrowMenu, Logo, MoneyRain, TrackedStatic


class MenuScreen(BaseScreen):
    """Ekran startowy z menu strzałkowym."""

    def compose_content(self):
        # Pozycje menu z kontrolera (wspólne dla każdego widoku)
        items = self.ctx.app_controller.menu_items
        # Układ: deszcz | środek | deszcz
        with Horizontal(id="menu-layout"):
            # Lewa animacja
            yield MoneyRain(classes="rain")
            # Część środkowa
            with Vertical(id="menu-center"):
                # Animowane logo
                yield Logo(id="logo")
                # Hasło programu
                yield Static(f"T E L E T U R N I E J   ·   {format_money(bundles_to_money(START_BUNDLES))}"
                             f"   ·   {START_BUNDLES} PACZEK", id="tagline")
                # Menu strzałkowe
                yield ArrowMenu([(item.id, item.label) for item in items], id="main-menu")
                # Opis podświetlonej pozycji
                yield TrackedStatic(items[0].description, id="menu-desc", diag_label="Opis pozycji")
                # Pasek informacji
                yield TrackedStatic(self._status_text(), id="menu-status", diag_label="Status")
            # Prawa animacja
            yield MoneyRain(classes="rain")

    def _status_text(self) -> str:
        """Tekst paska informacji."""
        # Ustawienia
        settings = self.ctx.settings
        # Złożenie tekstu
        return (f"Gracz: [b]{escape(settings['player_name'])}[/b]   ·   Pytań w bazie: "
                f"[b]{self.ctx.bank.count()}[/b]   ·   Czas: {settings.label('time_limit')}")

    def on_mount(self) -> None:
        # Fokus na menu, by od razu działały strzałki
        self.query_one(ArrowMenu).focus()
        # Zmiana ustawień odświeża tylko pasek statusu
        self.observe(self.ctx.settings, self._on_settings)

    def _on_settings(self, event: Event) -> None:
        # Tylko zmiany ustawień
        if event.type is EventType.SETTING_CHANGED:
            # Aktualizacja paska
            self.query_one("#menu-status", TrackedStatic).update(self._status_text())

    def on_arrow_menu_highlighted(self, message: ArrowMenu.Highlighted) -> None:
        # Opis podświetlonej pozycji
        item = next(i for i in self.ctx.app_controller.menu_items if i.id == message.item_id)
        # Aktualizacja tylko opisu
        self.query_one("#menu-desc", TrackedStatic).update(item.description)

    def on_arrow_menu_selected(self, message: ArrowMenu.Selected) -> None:
        # Przekazanie wyboru do kontrolera
        self.ctx.app_controller.select_menu(message.item_id)
