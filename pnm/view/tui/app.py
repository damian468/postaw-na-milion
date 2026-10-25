"""Widok tekstowy oparty na bibliotece Textual – implementacja interfejsu View."""

# time – pomiar upływu czasu między tyknięciami zegara
import time
# Typy funkcji zwrotnych
from typing import Any, Callable

# Klasy Textual
from textual.app import App
from textual.binding import Binding
from textual.screen import ModalScreen

# Kontekst aplikacji (modele + kontrolery)
from pnm.context import AppContext
# Interfejs widoku
from pnm.controller.view_interface import ScreenId, View
# Motywy kolorystyczne
from pnm.view.tui.themes import THEMES


class PnmApp(App):
    """Aplikacja Textual – pętla zdarzeń, ekrany, motywy."""

    # Plik stylów (CSS Textual)
    CSS_PATH = "styles.tcss"
    # Tytuł okna terminala
    TITLE = "Postaw na milion"
    # Wyłączenie palety poleceń (niepotrzebna w grze)
    ENABLE_COMMAND_PALETTE = False
    # Skróty globalne
    BINDINGS = [
        # Panel diagnostyczny odświeżania
        Binding("f2", "toggle_diag", "Diagnostyka", show=False),
        # Wyjście awaryjne
        Binding("ctrl+q", "quit", "Wyjście", show=False, priority=True),
    ]

    def __init__(self, ctx: AppContext) -> None:
        # Konstruktor Textual
        super().__init__()
        # Modele i kontrolery
        self.ctx = ctx
        # Czy panel diagnostyczny jest widoczny
        self.diag_enabled = False
        # Czy na stosie jest już ekran bazowy
        self._base_pushed = False
        # Czas ostatniego tyknięcia
        self._last_tick = time.monotonic()

    def on_mount(self) -> None:
        # Rejestracja własnych motywów
        for theme in THEMES:
            # Rejestracja w Textual
            self.register_theme(theme)
        # Zegar gry – 10 tyknięć na sekundę
        self.set_interval(0.1, self._tick)
        # Kontroler ustawia motyw i pokazuje menu
        self.ctx.app_controller.start()

    def _tick(self) -> None:
        """Przekazuje upływ czasu do kontrolera gry."""
        # Bieżący czas
        now = time.monotonic()
        # Upływ od poprzedniego tyknięcia (ograniczony – np. po uśpieniu komputera)
        dt = min(0.5, now - self._last_tick)
        # Zapamiętanie czasu
        self._last_tick = now
        # Kontroler odlicza czas i steruje odsłanianiem
        self.ctx.game_controller.tick(dt)

    def show(self, screen_id: ScreenId) -> None:
        """Pokazuje ekran o podanym identyfikatorze."""
        # Import tutaj, by uniknąć cyklicznych importów
        from pnm.view.tui.screens import SCREENS
        # Utworzenie nowego ekranu
        screen = SCREENS[screen_id](self.ctx)
        # Zamknięcie ewentualnych okien dialogowych
        while isinstance(self.screen, ModalScreen):
            # Zdjęcie dialogu ze stosu
            self.pop_screen()
        # Pierwszy ekran – kładziemy na stos
        if not self._base_pushed:
            # Położenie na stos
            self.push_screen(screen)
            # Zapamiętanie
            self._base_pushed = True
        # Kolejne – podmieniamy bieżący
        else:
            # Podmiana ekranu
            self.switch_screen(screen)

    def run_in_thread(self, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Uruchamia zadanie w wątku roboczym i wraca z wynikiem do wątku UI."""

        def work() -> None:
            # Wykonanie zadania (np. pobranie pytań z Internetu)
            try:
                # Wynik zadania
                result = task()
            # Nieoczekiwany błąd – komunikat zamiast awarii
            except Exception as error:  # noqa: BLE001 – chcemy złapać wszystko
                # Komunikat w wątku UI
                self.call_from_thread(self.notify, f"Błąd: {error}", severity="error")
                # Powrót do menu
                self.call_from_thread(self.show, ScreenId.MAIN_MENU)
                # Wyjście
                return
            # Przekazanie wyniku do wątku UI
            self.call_from_thread(on_done, result)

        # Start wątku roboczego Textual
        self.run_worker(work, thread=True, group="background")

    def action_toggle_diag(self) -> None:
        """Pokazuje/ukrywa panel diagnostyczny."""
        # Przełączenie flagi (panel sam sprawdza ją co pół sekundy)
        self.diag_enabled = not self.diag_enabled
        # Informacja dla użytkownika
        self.notify("Panel odświeżania: " + ("WŁĄCZONY" if self.diag_enabled else "wyłączony"),
                    timeout=2)


class TuiView(View):
    """Adapter: realizuje interfejs View za pomocą aplikacji Textual."""

    def __init__(self, ctx: AppContext) -> None:
        # Aplikacja Textual
        self.app = PnmApp(ctx)

    def run(self) -> None:
        # Start pętli zdarzeń Textual
        self.app.run()

    def navigate(self, screen: ScreenId) -> None:
        # Przełączenie ekranu
        self.app.show(screen)

    def notify(self, message: str, severity: str = "information") -> None:
        # Powiadomienie typu „toast”
        self.app.notify(message, severity=severity, timeout=4)

    def run_background(self, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        # Zadanie w wątku roboczym
        self.app.run_in_thread(task, on_done)

    def apply_theme(self, theme: str) -> None:
        # Zmiana motywu Textual (cała aplikacja przerysowuje kolory)
        self.app.theme = theme

    def bell(self) -> None:
        # Dzwonek terminala
        self.app.bell()

    def quit(self) -> None:
        # Zamknięcie aplikacji
        self.app.exit()
