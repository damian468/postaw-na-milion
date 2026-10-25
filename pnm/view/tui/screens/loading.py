"""Ekran ładowania pytań – animacja tasowania kart."""

# Text – kolorowanie
from rich.text import Text
# Klasy Textual
from textual.containers import Center, Middle
from textual.reactive import reactive

# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Widżety
from pnm.view.tui.widgets import TrackedWidget, theme_color

# Klatki spinnera
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
# Klatki tasowanych kart z pytaniami
CARDS = ("[?] [ ] [ ] [ ]", "[ ] [?] [ ] [ ]", "[ ] [ ] [?] [ ]", "[ ] [ ] [ ] [?]",
         "[ ] [ ] [?] [ ]", "[ ] [?] [ ] [ ]")


class LoadingAnimation(TrackedWidget):
    """Spinner i przesuwający się znak zapytania."""

    # Etykieta diagnostyczna
    diag_label = "Animacja ładowania"
    # Klatka animacji
    frame = reactive(0)

    def __init__(self, message: str) -> None:
        # Konstruktor widżetu
        super().__init__()
        # Tekst pod animacją
        self._message = message

    def on_mount(self) -> None:
        # Klatka co 90 ms
        self.set_interval(0.09, self._next)

    def _next(self) -> None:
        # Następna klatka
        self.frame += 1

    def draw(self) -> Text:
        # Wynikowy tekst
        text = Text(justify="center")
        # Karty z pytaniami
        text.append(CARDS[(self.frame // 3) % len(CARDS)] + "\n\n",
                    style=f"bold {theme_color(self, 'accent')}")
        # Spinner i komunikat
        text.append(f"{SPINNER[self.frame % len(SPINNER)]}  {self._message}",
                    style=f"bold {theme_color(self, 'primary')}")
        # Wynik
        return text


class LoadingScreen(BaseScreen):
    """Ekran wyświetlany podczas przygotowania puli pytań."""

    def compose_content(self):
        # Źródło pytań
        source = self.ctx.settings["question_source"]
        # Komunikat zależny od źródła
        message = ("Pobieram pytania z Open Trivia DB…" if source != "local"
                   else "Tasuję pytania z bazy…")
        # Wyśrodkowanie w pionie
        with Middle():
            # Wyśrodkowanie w poziomie
            with Center():
                # Animacja
                yield LoadingAnimation(message)
