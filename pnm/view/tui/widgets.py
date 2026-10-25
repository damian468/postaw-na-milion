"""Wspólne widżety widoku tekstowego: logo, deszcz pieniędzy, menu strzałkowe, diagnostyka."""

# random – losowe krople animacji
import random

# Text i Style – kolorowanie znak po znaku
from rich.style import Style
from rich.text import Text
# Klasy bazowe Textual
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

# Duża czcionka i słowa logo
from pnm.view.tui.ascii_art import LOGO_WORDS, big_text


def theme_color(widget: Widget, name: str) -> str:
    """Kolor zmiennej motywu (np. „accent”) jako tekst #RRGGBB."""
    # Odczyt ze zmiennych bieżącego motywu aplikacji
    return widget.app.theme_variables.get(name, "#FFFFFF")


def animations_on(widget: Widget) -> bool:
    """Czy w ustawieniach włączono animacje."""
    # Ustawienia są dostępne przez kontekst aplikacji
    return widget.app.ctx.settings["animation"] != "off"


class TrackedStatic(Static):
    """Static, który liczy swoje odświeżenia (podgląd w panelu diagnostycznym F2)."""

    # Etykieta w panelu diagnostycznym
    diag_label = "Tekst"

    def __init__(self, *args, diag_label: str | None = None, **kwargs) -> None:
        # Konstruktor Static
        super().__init__(*args, **kwargs)
        # Licznik odświeżeń
        self.render_count = 0
        # Własna etykieta, jeśli podano
        if diag_label:
            # Nadpisanie etykiety klasy
            self.diag_label = diag_label

    def render(self):
        """Rysuje zawartość i zwiększa licznik odświeżeń."""
        # Zliczenie odświeżenia
        self.render_count += 1
        # Właściwe rysowanie przez Static
        return super().render()


class TrackedWidget(Widget):
    """Widżet rysowany metodą draw(), który liczy swoje odświeżenia."""

    # Etykieta w panelu diagnostycznym
    diag_label = "Widżet"

    def __init__(self, *args, **kwargs) -> None:
        # Konstruktor Widget
        super().__init__(*args, **kwargs)
        # Licznik odświeżeń
        self.render_count = 0

    def render(self):
        """Zlicza odświeżenie i deleguje do draw()."""
        # Zliczenie odświeżenia
        self.render_count += 1
        # Właściwe rysowanie
        return self.draw()

    def draw(self):
        """Do nadpisania w klasach pochodnych."""
        # Domyślnie pusto
        return ""


class DiagPanel(Static):
    """Panel diagnostyczny (F2) – pokazuje, ile razy odświeżył się każdy widżet.

    Pozwala naocznie sprawdzić, że przy zmianie odświeżają się tylko elementy,
    których zmiana dotyczy (np. zegar raz na sekundę, jedna kolumna przy zakładzie).
    """

    def on_mount(self) -> None:
        # Odświeżanie panelu dwa razy na sekundę
        self.set_interval(0.5, self._refresh_counts)
        # Ostatnio wyświetlony tekst (by nie odświeżać bez potrzeby)
        self._last = ""

    def _refresh_counts(self) -> None:
        """Zbiera liczniki z widżetów bieżącego ekranu."""
        # Panel ukryty – nic nie robimy
        if not self.app.diag_enabled:
            # Ukrycie panelu
            self.display = False
            # Wyjście
            return
        # Pokazanie panelu
        self.display = True
        # Widżety ekranu z licznikiem odświeżeń
        tracked = [w for w in self.screen.query("*") if hasattr(w, "render_count")]
        # Linie w formacie „etykieta  liczba”
        lines = [f"{w.diag_label:<16}{w.render_count:>6}" for w in tracked]
        # Złożenie tekstu
        text = "[b]ODŚWIEŻENIA WIDŻETÓW[/b]\n" + "\n".join(lines)
        # Aktualizacja tylko przy zmianie
        if text != self._last:
            # Zapamiętanie
            self._last = text
            # Aktualizacja zawartości
            self.update(text)


class Logo(TrackedWidget):
    """Animowane logo „POSTAW NA MILION” z przesuwającym się refleksem światła."""

    # Etykieta diagnostyczna
    diag_label = "Logo"
    # Klatka animacji (zmiana powoduje odświeżenie tylko logo)
    frame = reactive(0)

    def on_mount(self) -> None:
        # Animacja refleksu co 70 ms
        self.set_interval(0.07, self._advance)

    def _advance(self) -> None:
        """Przesuwa refleks, jeśli animacje są włączone."""
        # Animacje wyłączone – logo statyczne
        if animations_on(self):
            # Następna klatka
            self.frame += 1

    def _lines(self) -> list[str]:
        """Linie logo (pełne lub kompaktowe zależnie od wysokości terminala)."""
        # Kompaktowo na niskich terminalach
        compact = self.app.size.height < 36
        # Linie obu słów
        lines = []
        # Każde słowo logo
        for index, word in enumerate(LOGO_WORDS):
            # Odstęp między słowami
            if index:
                # Pusta linia
                lines.append("")
            # Linie dużej czcionki
            lines.extend(big_text(word, compact))
        # Wynik
        return lines

    def get_content_height(self, container, viewport, width) -> int:
        """Wysokość logo = liczba linii."""
        # Liczba linii
        return len(self._lines())

    def draw(self) -> Text:
        """Rysuje logo z kolorowym refleksem."""
        # Kolor bazowy
        base = Style(color=theme_color(self, "primary"), bold=True)
        # Kolor refleksu
        shine = Style(color=theme_color(self, "accent"), bold=True)
        # Szerokość widżetu
        width = self.size.width
        # Wynikowy tekst
        text = Text()
        # Okres przesuwania refleksu
        period = width + 30
        # Pozycja refleksu
        position = self.frame % period
        # Każda linia logo
        for row, line in enumerate(self._lines()):
            # Wyśrodkowanie linii
            padded = line.center(width)
            # Każdy znak linii
            for col, char in enumerate(padded):
                # Odległość od ukośnego pasa refleksu
                distance = abs((col + row * 2) - position)
                # Znak w pasie refleksu – kolor akcentu
                text.append(char, shine if distance < 4 else base)
            # Koniec linii
            text.append("\n")
        # Usuwamy ostatni znak nowej linii
        text.rstrip()
        # Wynik
        return text


class MoneyRain(TrackedWidget):
    """Animacja ASCII spadających paczek banknotów (dekoracja menu)."""

    # Etykieta diagnostyczna
    diag_label = "Deszcz pieniędzy"
    # Klatka animacji
    frame = reactive(0)
    # Znaki kropli
    CHARS = ("▆", "$", "·", "▆", "¤")

    def on_mount(self) -> None:
        # Lista kropli: [kolumna, wiersz, prędkość, znak]
        self._drops: list[list] = []
        # Generator losowy
        self._rng = random.Random()
        # Animacja co 120 ms
        self.set_interval(0.12, self._advance)

    def _advance(self) -> None:
        """Przesuwa krople w dół i dodaje nowe."""
        # Bez animacji nic się nie dzieje
        if not animations_on(self):
            # Wyjście
            return
        # Wymiary widżetu
        width, height = self.size.width, self.size.height
        # Widżet jeszcze bez rozmiaru
        if width <= 0 or height <= 0:
            # Wyjście
            return
        # Nowa kropla z prawdopodobieństwem zależnym od szerokości
        if self._rng.random() < 0.35 + width / 60:
            # Losowa kolumna, start nad ekranem, losowa prędkość i znak
            self._drops.append([self._rng.randrange(width), 0.0, self._rng.uniform(0.3, 1.0),
                                self._rng.choice(self.CHARS)])
        # Przesunięcie kropel
        for drop in self._drops:
            # Spadek o prędkość
            drop[1] += drop[2]
        # Usunięcie kropel poza ekranem
        self._drops = [d for d in self._drops if d[1] < height and d[0] < width]
        # Nowa klatka – odświeżenie tylko tego widżetu
        self.frame += 1

    def draw(self) -> Text:
        """Rysuje krople na pustej siatce."""
        # Wymiary
        width, height = self.size.width, self.size.height
        # Pusta siatka znaków
        grid = [[" "] * width for _ in range(height)]
        # Umieszczenie kropel
        for col, row, _speed, char in getattr(self, "_drops", []):
            # Tylko w granicach siatki
            if 0 <= int(row) < height and 0 <= col < width:
                # Znak kropli
                grid[int(row)][col] = char
        # Kolor banknotów
        style = Style(color=theme_color(self, "accent"))
        # Złożenie linii w tekst
        return Text("\n".join("".join(line) for line in grid), style=style)


class MenuEntry(TrackedStatic):
    """Pojedyncza pozycja menu strzałkowego."""

    def __init__(self, item_id: str, label: str, index: int) -> None:
        # Etykieta diagnostyczna z nazwą pozycji
        super().__init__(diag_label=f"Menu: {label[:10]}")
        # Identyfikator akcji
        self.item_id = item_id
        # Tekst pozycji
        self.label = label
        # Pozycja na liście
        self.index = index
        # Pierwsze narysowanie
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        """Zmienia wygląd pozycji (wybrana / zwykła)."""
        # Klasa CSS do stylowania
        self.set_class(selected, "-selected")
        # Strzałki wokół wybranej pozycji
        self.update(f"▶  {self.label}  ◀" if selected else self.label)

    def on_click(self) -> None:
        # Kliknięcie myszą – wybór i zatwierdzenie
        self.parent.activate(self.index)

    def on_enter(self) -> None:
        # Najechanie myszą – podświetlenie
        self.parent.highlight(self.index)


class ArrowMenu(Vertical, can_focus=True):
    """Menu obsługiwane strzałkami (↑/↓, Enter) oraz myszą.

    Zmiana zaznaczenia odświeża tylko dwie pozycje: poprzednią i nową.
    """

    # Skróty klawiszowe menu
    BINDINGS = [
        # Strzałka w górę
        Binding("up", "move(-1)", "W górę", show=False),
        # Strzałka w dół
        Binding("down", "move(1)", "W dół", show=False),
        # Pierwsza pozycja
        Binding("home", "jump(0)", show=False),
        # Ostatnia pozycja
        Binding("end", "jump(-1)", show=False),
        # Zatwierdzenie
        Binding("enter", "activate_current", "Wybierz"),
    ]

    class Highlighted(Message):
        """Zmieniono podświetloną pozycję."""

        def __init__(self, item_id: str) -> None:
            # Konstruktor wiadomości
            super().__init__()
            # Identyfikator pozycji
            self.item_id = item_id

    class Selected(Message):
        """Zatwierdzono pozycję."""

        def __init__(self, item_id: str) -> None:
            # Konstruktor wiadomości
            super().__init__()
            # Identyfikator pozycji
            self.item_id = item_id

    def __init__(self, items: list[tuple[str, str]], **kwargs) -> None:
        # Konstruktor kontenera
        super().__init__(**kwargs)
        # Pozycje (identyfikator, etykieta)
        self._items = items
        # Indeks zaznaczonej pozycji
        self._index = 0

    def compose(self):
        # Tworzenie pozycji menu
        for index, (item_id, label) in enumerate(self._items):
            # Pojedyncza pozycja
            yield MenuEntry(item_id, label, index)

    def on_mount(self) -> None:
        # Zaznaczenie pierwszej pozycji
        self._entries()[0].set_selected(True)

    def _entries(self) -> list[MenuEntry]:
        """Lista pozycji menu."""
        # Zapytanie o dzieci typu MenuEntry
        return list(self.query(MenuEntry))

    def highlight(self, index: int) -> None:
        """Podświetla pozycję o podanym indeksie."""
        # Pozycje menu
        entries = self._entries()
        # Indeks z zawijaniem
        index %= len(entries)
        # Bez zmiany – bez odświeżania
        if index == self._index:
            # Wyjście
            return
        # Odznaczenie poprzedniej (odświeża tylko ją)
        entries[self._index].set_selected(False)
        # Zapamiętanie nowego indeksu
        self._index = index
        # Zaznaczenie nowej (odświeża tylko ją)
        entries[index].set_selected(True)
        # Powiadomienie rodzica (np. aktualizacja opisu)
        self.post_message(self.Highlighted(entries[index].item_id))

    def activate(self, index: int) -> None:
        """Podświetla i zatwierdza pozycję."""
        # Podświetlenie
        self.highlight(index)
        # Zatwierdzenie
        self.action_activate_current()

    def action_move(self, step: int) -> None:
        # Przesunięcie zaznaczenia
        self.highlight(self._index + step)

    def action_jump(self, index: int) -> None:
        # Skok na pozycję (−1 = ostatnia)
        self.highlight(index if index >= 0 else len(self._items) - 1)

    def action_activate_current(self) -> None:
        # Wiadomość o zatwierdzeniu bieżącej pozycji
        self.post_message(self.Selected(self._items[self._index][0]))
