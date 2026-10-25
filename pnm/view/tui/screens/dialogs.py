"""Okna dialogowe: potwierdzenie, pauza, wpisywanie tekstu."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

# Duża czcionka
from pnm.view.tui.ascii_art import big_text


class ConfirmDialog(ModalScreen[bool]):
    """Pytanie tak/nie. Zwraca True (tak) lub False (nie)."""

    # Skróty klawiszowe
    BINDINGS = [
        # Tak
        Binding("t,y", "answer(True)", "Tak"),
        # Nie
        Binding("n,escape", "answer(False)", "Nie"),
        # Przejście między przyciskami strzałkami
        Binding("left,right", "app.focus_next", show=False),
    ]

    def __init__(self, title: str, message: str) -> None:
        # Konstruktor Textual
        super().__init__()
        # Tytuł okna
        self._title = title
        # Treść pytania
        self._message = message

    def compose(self):
        # Ramka okna
        with Vertical(classes="dialog"):
            # Tytuł
            yield Static(self._title, classes="dialog-title")
            # Treść
            yield Static(self._message, classes="dialog-body")
            # Rząd przycisków
            with Horizontal(classes="dialog-buttons"):
                # Przycisk „Tak”
                yield Button("Tak [T]", variant="error", id="yes")
                # Przycisk „Nie”
                yield Button("Nie [N]", variant="primary", id="no")

    def on_mount(self) -> None:
        # Domyślnie zaznaczone „Nie” (bezpieczniej)
        self.query_one("#no").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Zwrot odpowiedzi wg przycisku
        self.dismiss(event.button.id == "yes")

    def action_answer(self, value: bool) -> None:
        # Zwrot odpowiedzi z klawiatury
        self.dismiss(value)


class PauseDialog(ModalScreen[None]):
    """Ekran pauzy – zakrywa pytanie, by nie można było „oszukiwać” czasem."""

    # Wznowienie gry
    BINDINGS = [Binding("p,escape,enter,space", "resume", "Wznów")]

    def compose(self):
        # Ramka okna
        with Vertical(classes="dialog pause"):
            # Napis PAUZA dużą czcionką
            yield Static("\n".join(big_text("PAUZA")), classes="pause-art")
            # Podpowiedź
            yield Static("Naciśnij [b]P[/b], [b]Enter[/b] lub [b]Esc[/b], aby wrócić do gry.",
                         classes="dialog-body")

    def action_resume(self) -> None:
        # Zamknięcie okna
        self.dismiss(None)


class TextInputDialog(ModalScreen[str | None]):
    """Wpisywanie tekstu. Zwraca tekst albo None po anulowaniu."""

    # Anulowanie klawiszem Esc
    BINDINGS = [Binding("escape", "cancel", "Anuluj")]

    def __init__(self, title: str, value: str, max_length: int = 16) -> None:
        # Konstruktor Textual
        super().__init__()
        # Tytuł okna
        self._title = title
        # Wartość początkowa
        self._value = value
        # Maksymalna długość
        self._max_length = max_length

    def compose(self):
        # Ramka okna
        with Vertical(classes="dialog"):
            # Tytuł
            yield Static(self._title, classes="dialog-title")
            # Pole tekstowe
            yield Input(value=self._value, max_length=self._max_length, id="text")
            # Podpowiedź
            yield Static("[b]Enter[/b] – zapisz   [b]Esc[/b] – anuluj", classes="dialog-body")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Zwrot wpisanego tekstu
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        # Anulowanie
        self.dismiss(None)
