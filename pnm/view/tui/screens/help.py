"""Zasady gry i sterowanie – strony przewijane strzałkami ←/→."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

# Strony pomocy (wspólne z widokiem graficznym)
from pnm.view.help_pages import PAGES
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Widżety
from pnm.view.tui.widgets import TrackedStatic


class HelpScreen(BaseScreen):
    """Zasady gry."""

    # Skróty klawiszowe
    BINDINGS = [
        # Poprzednia strona
        Binding("left", "page(-1)", "Strona", key_display="←→"),
        # Następna strona
        Binding("right", "page(1)", show=False),
        # Powrót
        Binding("escape,enter", "back", "Wróć"),
    ]

    def compose_content(self):
        # Kolumna ekranu
        with Vertical(id="help"):
            # Tytuł strony
            yield TrackedStatic(classes="screen-title", id="help-title", diag_label="Tytuł strony")
            # Treść strony
            yield TrackedStatic(id="help-body", diag_label="Treść strony")
            # Wskaźnik stron
            yield TrackedStatic(id="help-dots", diag_label="Wskaźnik stron")

    def on_mount(self) -> None:
        # Bieżąca strona
        self._page = 0
        # Narysowanie strony
        self._show()

    def _show(self) -> None:
        """Rysuje bieżącą stronę."""
        # Tytuł i treść
        title, body = PAGES[self._page]
        # Tytuł
        self.query_one("#help-title", TrackedStatic).update(f"[b]{title}[/b]")
        # Treść
        self.query_one("#help-body", TrackedStatic).update(body)
        # Kropki stron (bieżąca wypełniona)
        dots = "  ".join("●" if i == self._page else "○" for i in range(len(PAGES)))
        # Wskaźnik
        self.query_one("#help-dots", TrackedStatic).update(f"◀  {dots}  ▶")

    def action_page(self, step: int) -> None:
        # Zmiana strony z zawijaniem
        self._page = (self._page + step) % len(PAGES)
        # Narysowanie
        self._show()

    def action_back(self) -> None:
        # Powrót do menu
        self.ctx.app_controller.back_to_menu()
