"""Ekran ustawień – lista opcji przełączanych strzałkami ←/→, podgląd na żywo."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

# Zdarzenia
from pnm.model.observable import Event, EventType
# Maksymalna długość imienia
from pnm.model.settings import MAX_NAME_LENGTH, SettingDefinition
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Okno wpisywania tekstu
from pnm.view.tui.screens.dialogs import TextInputDialog
# Widżety
from pnm.view.tui.widgets import TrackedStatic


class SettingRow(TrackedStatic):
    """Wiersz ustawienia: etykieta i wartość ze strzałkami."""

    def __init__(self, definition: SettingDefinition, index: int) -> None:
        # Etykieta diagnostyczna z nazwą ustawienia
        super().__init__(diag_label=f"Opcja: {definition.label[:9]}")
        # Definicja ustawienia
        self.definition = definition
        # Pozycja na liście
        self.index = index

    def refresh_row(self, value_label: str, selected: bool) -> None:
        """Rysuje wiersz z podaną wartością."""
        # Klasa wybranego wiersza
        self.set_class(selected, "-selected")
        # Pole tekstowe – podpowiedź „Enter”
        if self.definition.is_text:
            # Wartość z ikoną edycji
            value = f"✎ {value_label}" + ("   [dim](Enter – zmień)[/dim]" if selected else "")
        # Pole wyboru – strzałki po bokach
        else:
            # Wartość ze strzałkami
            value = f"◀  {value_label}  ▶" if selected else f"   {value_label}"
        # Treść wiersza
        self.update(f"{self.definition.label:<22}{value}")

    def on_click(self) -> None:
        # Kliknięcie – wybór wiersza
        self.screen.select_row(self.index)


class SettingsScreen(BaseScreen):
    """Ustawienia aplikacji."""

    # Skróty klawiszowe
    BINDINGS = [
        # Poprzednie ustawienie
        Binding("up", "move(-1)", "Wybór", key_display="↑↓"),
        # Następne ustawienie
        Binding("down", "move(1)", show=False),
        # Poprzednia wartość
        Binding("left", "change(-1)", "Zmień", key_display="←→"),
        # Następna wartość
        Binding("right", "change(1)", show=False),
        # Edycja pola tekstowego / następna wartość
        Binding("enter", "edit", "Edytuj"),
        # Powrót
        Binding("escape", "back", "Wróć"),
    ]

    def compose_content(self):
        # Kolumna ustawień
        with Vertical(id="settings"):
            # Tytuł
            yield Static("[b]≡  USTAWIENIA[/b]", classes="screen-title")
            # Wiersze ustawień
            for index, definition in enumerate(self.ctx.settings.definitions):
                # Wiersz
                yield SettingRow(definition, index)
            # Opis wybranego ustawienia
            yield TrackedStatic(id="settings-desc", diag_label="Opis ustawienia")
            # Informacja o zapisie
            yield Static("[dim]Zmiany zapisują się automatycznie w pliku data/settings.json[/dim]",
                         id="settings-note")

    def on_mount(self) -> None:
        # Indeks wybranego wiersza
        self._index = 0
        # Pierwsze narysowanie wszystkich wierszy
        for row in self._rows():
            # Wiersz
            self._draw_row(row)
        # Opis
        self._draw_description()
        # Zmiana ustawienia odświeża tylko jego wiersz
        self.observe(self.ctx.settings, self._on_setting)

    def _rows(self) -> list[SettingRow]:
        """Wiersze ustawień."""
        # Zapytanie o widżety
        return list(self.query(SettingRow))

    def _draw_row(self, row: SettingRow) -> None:
        """Rysuje jeden wiersz."""
        # Etykieta wartości i zaznaczenie
        row.refresh_row(self.ctx.settings.label(row.definition.key), row.index == self._index)

    def _draw_description(self) -> None:
        """Rysuje opis wybranego ustawienia."""
        # Definicja wybranego ustawienia
        definition = self._rows()[self._index].definition
        # Aktualizacja opisu
        self.query_one("#settings-desc", TrackedStatic).update(f"ℹ  {definition.description}")

    def _on_setting(self, event: Event) -> None:
        # Tylko zmiany ustawień
        if event.type is not EventType.SETTING_CHANGED:
            # Wyjście
            return
        # Wiersz zmienionego ustawienia
        for row in self._rows():
            # Porównanie klucza
            if row.definition.key == event.data["key"]:
                # Odświeżenie tylko tego wiersza
                self._draw_row(row)

    def select_row(self, index: int) -> None:
        """Zaznacza wiersz – odświeża tylko poprzedni i nowy."""
        # Wiersze
        rows = self._rows()
        # Poprzedni wiersz
        previous = rows[self._index]
        # Nowy indeks z zawijaniem
        self._index = index % len(rows)
        # Odświeżenie poprzedniego
        self._draw_row(previous)
        # Odświeżenie nowego
        self._draw_row(rows[self._index])
        # Opis
        self._draw_description()

    def action_move(self, step: int) -> None:
        # Przesunięcie zaznaczenia
        self.select_row(self._index + step)

    def action_change(self, step: int) -> None:
        # Definicja wybranego ustawienia
        definition = self._rows()[self._index].definition
        # Pola tekstowe edytuje się Enterem
        if definition.is_text:
            # Wyjście
            return
        # Zmiana przez kontroler
        self.ctx.app_controller.cycle_setting(definition.key, step)

    def action_edit(self) -> None:
        # Definicja wybranego ustawienia
        definition = self._rows()[self._index].definition
        # Pole wyboru – Enter działa jak strzałka w prawo
        if not definition.is_text:
            # Następna wartość
            self.action_change(1)
            # Wyjście
            return

        def save(value: str | None) -> None:
            # Zapis, jeśli nie anulowano
            if value is not None:
                # Przez kontroler (waliduje wartość)
                self.ctx.app_controller.set_setting(definition.key, value)

        # Okno wpisywania tekstu
        self.app.push_screen(TextInputDialog(definition.label,
                                             self.ctx.settings[definition.key],
                                             MAX_NAME_LENGTH), save)

    def action_back(self) -> None:
        # Powrót do menu
        self.ctx.app_controller.back_to_menu()
