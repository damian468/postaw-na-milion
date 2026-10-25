"""Ekran bazowy: stopka ze skrótami, panel diagnostyczny i subskrypcje modeli."""

# Typ funkcji obsługi zdarzeń
from typing import Callable

# Klasy Textual
from textual.screen import Screen
from textual.widgets import Footer

# Kontekst aplikacji
from pnm.context import AppContext
# Mechanizm obserwatora
from pnm.model.observable import Event, Observable
# Panel diagnostyczny
from pnm.view.tui.widgets import DiagPanel


class BaseScreen(Screen):
    """Wspólna baza wszystkich ekranów pełnoekranowych."""

    def __init__(self, ctx: AppContext) -> None:
        # Konstruktor Textual
        super().__init__()
        # Modele i kontrolery
        self.ctx = ctx
        # Funkcje wypisujące subskrypcje (wywoływane przy zamknięciu ekranu)
        self._unsubscribers: list[Callable[[], None]] = []

    def compose(self):
        # Zawartość właściwa ekranu
        yield from self.compose_content()
        # Panel diagnostyczny (ukryty do wciśnięcia F2)
        yield DiagPanel(id="diag")
        # Stopka ze skrótami klawiszowymi
        footer = Footer()
        # Widoczność wg ustawień
        footer.display = self.ctx.settings["show_hints"]
        # Dodanie stopki
        yield footer

    def compose_content(self):
        """Do nadpisania – widżety ekranu."""
        # Domyślnie pusto
        yield from ()

    def observe(self, model: Observable, handler: Callable[[Event], None]) -> None:
        """Subskrybuje model; subskrypcja zniknie razem z ekranem."""
        # Rejestracja i zapamiętanie funkcji wypisującej
        self._unsubscribers.append(model.subscribe(handler))

    def on_unmount(self) -> None:
        # Wypisanie wszystkich subskrypcji
        for unsubscribe in self._unsubscribers:
            # Wypisanie
            unsubscribe()
        # Wyczyszczenie listy
        self._unsubscribers.clear()
