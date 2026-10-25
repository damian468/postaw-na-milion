"""Podsumowanie gry: wygrana dużymi cyframi, iskierki ASCII i przebieg rund."""

# random – pozycje iskierek
import random

# Kolorowanie
from rich.style import Style
from rich.text import Text
# Klasy Textual
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Static

# Stałe i formatowanie
from pnm.config import ANSWER_LETTERS, bundles_to_money, format_money
# Duża czcionka
from pnm.view.tui.ascii_art import big_text
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Widżety
from pnm.view.tui.widgets import ArrowMenu, TrackedWidget, animations_on, theme_color

# Znaki iskierek
SPARKS = "*+·✦."


class Fireworks(TrackedWidget):
    """Kwota wygranej dużą czcionką otoczona migoczącymi iskierkami."""

    # Etykieta diagnostyczna
    diag_label = "Wygrana + iskierki"
    # Klatka animacji
    frame = reactive(0)

    def __init__(self, amount: int, won: bool, **kwargs) -> None:
        # Konstruktor widżetu
        super().__init__(**kwargs)
        # Kwota wygranej
        self._amount = amount
        # Czy gracz cokolwiek wygrał
        self._won = won
        # Generator losowy
        self._rng = random.Random()

    def on_mount(self) -> None:
        # Iskierki tylko przy wygranej
        if self._won:
            # Animacja co 150 ms
            self.set_interval(0.15, self._next)

    def _next(self) -> None:
        # Nowa klatka, jeśli animacje włączone
        if animations_on(self):
            # Następna klatka
            self.frame += 1

    def draw(self) -> Text:
        # Wymiary
        width, height = max(1, self.size.width), max(1, self.size.height)
        # Linie kwoty (pełna czcionka lub kompaktowa, gdy za wąsko)
        digits = f"{self._amount:,}".replace(",", " ")
        # Pełna czcionka
        art = big_text(digits)
        # Za szeroko – kompaktowa
        if len(art[0]) > width:
            # Kompaktowa
            art = big_text(digits, compact=True)
        # Pusta siatka
        grid = [[" "] * width for _ in range(height)]
        # Iskierki w losowych miejscach (gęstość zależna od klatki)
        if self._won:
            # Generator zależny od klatki (powtarzalny w obrębie klatki)
            rng = random.Random(self.frame)
            # Około 25 iskierek
            for _ in range(25):
                # Losowe miejsce i znak
                grid[rng.randrange(height)][rng.randrange(width)] = rng.choice(SPARKS)
        # Pozycja pionowa kwoty (środek)
        top = max(0, (height - len(art)) // 2)
        # Wstawienie kwoty
        for row, line in enumerate(art):
            # Tylko w granicach
            if top + row < height:
                # Pozycja pozioma (środek)
                left = max(0, (width - len(line)) // 2)
                # Znaki linii
                for col, char in enumerate(line[:width - left]):
                    # Wpisanie znaku
                    grid[top + row][left + col] = char
        # Kolor kwoty
        color = theme_color(self, "accent" if self._won else "error")
        # Kolor iskierek
        spark = theme_color(self, "primary")
        # Wynikowy tekst
        text = Text()
        # Każda linia siatki
        for row, line in enumerate(grid):
            # Każdy znak
            for char in line:
                # Bloki – kolor kwoty, reszta – kolor iskierek
                text.append(char, Style(color=color, bold=True) if char in "█▀▄" else Style(color=spark))
            # Nowa linia (oprócz ostatniej)
            if row < height - 1:
                # Znak końca linii
                text.append("\n")
        # Wynik
        return text


class SummaryScreen(BaseScreen):
    """Ekran końca gry."""

    def compose_content(self):
        # Skrót do modelu gry
        game = self.ctx.game
        # Czy gracz coś wygrał
        won = game.bundles > 0
        # Miejsce w rankingu
        rank = self.ctx.game_controller.last_rank
        # Nagłówek zależny od wyniku
        title = ("GRATULACJE! WYGRYWASZ" if won else "TYM RAZEM SIĘ NIE UDAŁO…")
        # Całość w pionie
        with Vertical(id="summary"):
            # Nagłówek
            yield Static(f"[b]{title}[/b]", id="summary-title")
            # Kwota z iskierkami
            yield Fireworks(game.money, won, id="fireworks")
            # Informacje dodatkowe
            yield Static(f"{game.player}  ·  {format_money(game.money)}  ·  pytania: "
                         f"{game.answered_rounds}/{game.total_rounds}  ·  "
                         f"[b]miejsce w rankingu: {rank}[/b]", id="summary-info")
            # Tabela rund i menu obok siebie
            with Horizontal(id="summary-bottom"):
                # Przebieg rund
                yield DataTable(id="summary-table", cursor_type="row", zebra_stripes=True)
                # Menu akcji
                yield ArrowMenu([("again", "Zagraj ponownie"), ("menu", "Menu główne")],
                                id="summary-menu")

    def on_mount(self) -> None:
        # Tabela przebiegu
        table = self.query_one(DataTable)
        # Kolumny tabeli
        table.add_columns("Nr", "Kategoria", "Pytanie", "Poprawna", "Twoje zakłady", "Po rundzie")
        # Każda rozegrana runda
        for record in self.ctx.game.history:
            # Zakłady w formacie „A:10 B:30”
            bets = " ".join(f"{ANSWER_LETTERS[i]}:{b}" for i, b in enumerate(record.bets) if b)
            # Wiersz tabeli
            table.add_row(
                # Numer
                str(record.number),
                # Kategoria
                record.category,
                # Skrócone pytanie
                record.question[:38] + ("…" if len(record.question) > 38 else ""),
                # Poprawna odpowiedź
                f"{ANSWER_LETTERS[record.correct_index]}: {record.answers[record.correct_index]}",
                # Zakłady w paczkach
                bets or "—",
                # Kwota po rundzie
                format_money(bundles_to_money(record.bundles_after)),
            )
        # Fokus na menu
        self.query_one(ArrowMenu).focus()

    def on_arrow_menu_selected(self, message: ArrowMenu.Selected) -> None:
        # Nowa gra
        if message.item_id == "again":
            # Przez kontroler
            self.ctx.app_controller.new_game()
        # Menu główne
        else:
            # Przez kontroler
            self.ctx.app_controller.back_to_menu()
