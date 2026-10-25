"""Widżety ekranu gry: zegar, drabinka pytań, pula pieniędzy, kolumny z zapadniami.

Każdy widżet przechowuje tylko swój fragment stanu w polach `reactive`.
Zmiana pola odświeża wyłącznie ten jeden widżet – np. dołożenie paczki na
odpowiedź B przerysowuje tylko kolumnę B i pasek puli, a nie cały ekran.
"""

# ceil – liczba rzędów cegiełek
import math
# textwrap – zawijanie treści odpowiedzi
import textwrap

# Kolorowanie tekstu
from rich.style import Style
from rich.text import Text
# Reaktywne pola Textual
from textual.reactive import reactive

# Stałe i formatowanie kwot
from pnm.config import BUNDLE_VALUE, bundles_to_money, format_money
# Model gry (tylko do odczytu)
from pnm.model.game import GameModel
# Duża czcionka i ikony
from pnm.view.tui.ascii_art import big_text, category_icon
# Widżety bazowe
from pnm.view.tui.widgets import TrackedStatic, TrackedWidget, theme_color

# Znak jednej paczki banknotów
BRICK = "▆"
# Liczba klatek animacji otwierania zapadni
OPEN_FRAMES = 9


def short_money(bundles: int) -> str:
    """Krótki zapis kwoty: „750 tys.” lub „1 mln”."""
    # Kwota w złotych
    amount = bundles_to_money(bundles)
    # Pełny milion
    if amount >= 1_000_000:
        # Zapis w milionach
        return f"{amount / 1_000_000:g} mln"
    # Zapis w tysiącach
    return f"{amount // 1000} tys."


class TimerBox(TrackedWidget):
    """Zegar odliczający czas – odświeża się tylko raz na sekundę."""

    # Etykieta diagnostyczna
    diag_label = "Zegar"
    # Pozostałe sekundy
    seconds = reactive(0)
    # Czy wstrzymano
    paused = reactive(False)
    # Limit czasu rundy (0 = bez limitu)
    limit = reactive(0)

    def draw(self) -> Text:
        # Brak limitu czasu
        if self.limit <= 0:
            # Napis zamiast cyfr
            return Text("\nBEZ LIMITU\nCZASU", justify="center",
                        style=f"bold {theme_color(self, 'primary')}")
        # Minuty i sekundy
        minutes, secs = divmod(max(0, self.seconds), 60)
        # Udział pozostałego czasu
        ratio = self.seconds / self.limit
        # Kolor: zielony → żółty → czerwony
        color = theme_color(self, "success" if ratio > 0.34 else
                            "warning" if self.seconds > 10 else "error")
        # Miganie w ostatnich sekundach (co druga sekunda jaśniejszy kolor)
        if self.seconds <= 10 and self.seconds % 2:
            # Kolor tekstu zamiast czerwieni
            color = theme_color(self, "foreground")
        # Wynikowy tekst
        text = Text(justify="center")
        # Cyfry dużą czcionką (kompaktowe)
        text.append("\n".join(big_text(f"{minutes}:{secs:02}", compact=True)),
                    style=Style(color=color, bold=True))
        # Szerokość paska postępu
        width = max(1, self.size.width)
        # Wypełniona część paska
        filled = round(width * ratio)
        # Pasek postępu
        text.append("\n" + "█" * filled, style=color)
        # Pusta część paska
        text.append("░" * (width - filled), style="dim")
        # Informacja o pauzie
        if self.paused:
            # Dopisek
            text.append("\nPAUZA", style="bold reverse")
        # Wynik
        return text


class Ladder(TrackedWidget):
    """Drabinka pytań – postęp gry i wyniki poprzednich rund."""

    # Etykieta diagnostyczna
    diag_label = "Drabinka pytań"

    def __init__(self, game: GameModel, **kwargs) -> None:
        # Konstruktor widżetu
        super().__init__(**kwargs)
        # Model gry (odczyt)
        self._game = game

    def draw(self) -> Text:
        # Skrót do modelu
        game = self._game
        # Wynikowy tekst
        text = Text()
        # Nagłówek
        text.append("  DRABINKA\n\n", style=f"bold {theme_color(self, 'primary')}")
        # Od ostatniego pytania do pierwszego
        for index in reversed(range(game.total_rounds)):
            # Liczba odpowiedzi w rundzie
            answers = game.layout[index]
            # Runda już rozegrana
            if index < len(game.history):
                # Zapis rundy
                record = game.history[index]
                # Czy gracz coś zachował
                kept = record.bundles_after > 0
                # Znacznik i kolor
                mark, style = ("✔", theme_color(self, "success")) if kept else (
                    "✖", theme_color(self, "error"))
                # Linia z kwotą po rundzie
                text.append(f" {mark} {index + 1}. {answers} odp. {short_money(record.bundles_after):>9}\n",
                            style=style)
            # Runda bieżąca
            elif index == game.round_index:
                # Wyróżniona linia
                text.append(f" ▶ {index + 1}. {answers} odp. {'':>9}\n",
                            style=f"bold reverse {theme_color(self, 'accent')}")
            # Runda przyszła
            else:
                # Przygaszona linia
                text.append(f" · {index + 1}. {answers} odp.\n", style="dim")
        # Wynik
        return text


class PoolBar(TrackedWidget):
    """Pasek z pieniędzmi, które trzeba jeszcze rozłożyć."""

    # Etykieta diagnostyczna
    diag_label = "Pula do rozłożenia"
    # Nierozłożone paczki
    unplaced = reactive(0)
    # Tryb: stawianie / zamknięte
    locked = reactive(False)
    # Paczki utracone przez upływ czasu
    lost = reactive(0)

    def draw(self) -> Text:
        # Zakłady zamknięte
        if self.locked:
            # Część pieniędzy przepadła przez czas
            if self.lost:
                # Komunikat o stracie
                return Text(f"CZAS MINĄŁ!  Nierozłożone {format_money(bundles_to_money(self.lost))}"
                            " przepada.", style=f"bold {theme_color(self, 'error')}",
                            justify="center")
            # Zwykłe zamknięcie
            return Text("ZAKŁADY ZAMKNIĘTE – otwieramy zapadnie…",
                        style=f"bold {theme_color(self, 'primary')}", justify="center")
        # Wszystko rozłożone
        if self.unplaced == 0:
            # Zachęta do zatwierdzenia
            return Text("✔  Wszystko rozłożone – [Enter] zamyka zakłady",
                        style=f"bold {theme_color(self, 'success')}", justify="center")
        # Pasek z cegiełkami
        text = Text(justify="center")
        # Etykieta
        text.append("DO ROZŁOŻENIA  ", style="bold")
        # Cegiełki paczek
        text.append(BRICK * self.unplaced, style=theme_color(self, "accent"))
        # Kwota
        text.append(f"  {self.unplaced} × {BUNDLE_VALUE // 1000} tys. = "
                    f"{format_money(bundles_to_money(self.unplaced))}",
                    style=f"bold {theme_color(self, 'warning')}")
        # Wynik
        return text


class AnswerColumn(TrackedWidget):
    """Kolumna odpowiedzi ze stosem paczek i zapadnią u dołu."""

    # Liczba paczek na odpowiedzi
    bundles = reactive(0)
    # Czy kolumna jest wybrana
    selected = reactive(False)
    # Stan zapadni: closed / opening / opened / correct
    state = reactive("closed")
    # Klatka animacji otwierania
    frame = reactive(0)

    def __init__(self, index: int, letter: str, answer: str) -> None:
        # Konstruktor widżetu
        super().__init__()
        # Indeks odpowiedzi
        self.index = index
        # Litera odpowiedzi
        self.letter = letter
        # Treść odpowiedzi
        self.answer = answer
        # Etykieta diagnostyczna
        self.diag_label = f"Kolumna {letter}"
        # Tytuł ramki
        self.border_title = f" {letter} "
        # Paczki utracone po otwarciu zapadni
        self.lost = 0
        # Zegar animacji
        self._anim_timer = None

    # --------------------------------------------------------- zmiany stanu

    def watch_selected(self, selected: bool) -> None:
        # Klasa CSS wybranej kolumny
        self.set_class(selected, "-selected")

    def watch_state(self, state: str) -> None:
        # Klasa CSS otwartej zapadni
        self.set_class(state in ("opening", "opened"), "-opened")
        # Klasa CSS poprawnej odpowiedzi
        self.set_class(state == "correct", "-correct")
        # Tytuł ramki dla poprawnej odpowiedzi
        if state == "correct":
            # Znacznik poprawnej
            self.border_title = f" {self.letter} ✔ POPRAWNA "

    def open_trapdoor(self, lost: int, animation: str) -> None:
        """Otwiera zapadnię (z animacją spadających pieniędzy)."""
        # Zapamiętanie straty
        self.lost = lost
        # Bez animacji – od razu otwarta
        if animation == "off":
            # Stan końcowy
            self.state = "opened"
            # Wyjście
            return
        # Początek animacji
        self.state = "opening"
        # Klatka zero
        self.frame = 0
        # Tempo animacji
        interval = 0.07 if animation == "normal" else 0.035
        # Zegar animacji (odświeża tylko tę kolumnę)
        self._anim_timer = self.set_interval(interval, self._animation_step)

    def _animation_step(self) -> None:
        """Kolejna klatka otwierania."""
        # Następna klatka
        self.frame += 1
        # Koniec animacji
        if self.frame >= OPEN_FRAMES:
            # Zatrzymanie zegara
            self._anim_timer.stop()
            # Stan końcowy
            self.state = "opened"

    def mark_correct(self) -> None:
        """Oznacza kolumnę jako poprawną odpowiedź."""
        # Zmiana stanu
        self.state = "correct"

    # -------------------------------------------------------------- mysz

    def on_click(self) -> None:
        # Kliknięcie – wybór kolumny
        self.screen.column_clicked(self.index)

    def on_mouse_scroll_up(self, event) -> None:
        # Kółko w górę – dołożenie paczki
        self.screen.column_scrolled(self.index, 1)
        # Zatrzymanie przewijania kontenera
        event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        # Kółko w dół – zdjęcie paczki
        self.screen.column_scrolled(self.index, -1)
        # Zatrzymanie przewijania kontenera
        event.stop()

    # ---------------------------------------------------------- rysowanie

    def draw(self) -> Text:
        # Wymiary obszaru treści
        width, height = max(1, self.size.width), max(1, self.size.height)
        # Kolory motywu
        accent, error = theme_color(self, "accent"), theme_color(self, "error")
        # Kolory motywu
        primary, success = theme_color(self, "primary"), theme_color(self, "success")
        # Czy zapadnia otwarta / otwiera się
        falling = self.state in ("opening", "opened")
        # Linie wynikowe
        lines: list[Text] = []
        # Treść odpowiedzi zawinięta do szerokości (maks. 3 linie)
        wrapped = textwrap.wrap(self.answer, width) or [""]
        # Styl odpowiedzi (przekreślona po otwarciu)
        answer_style = Style(bold=True, strike=falling, dim=falling,
                             color=success if self.state == "correct" else None)
        # Dodanie linii odpowiedzi
        for line in wrapped[:3]:
            # Wyśrodkowana linia
            lines.append(Text(line.center(width), style=answer_style))
        # Uzupełnienie do trzech linii
        while len(lines) < 3:
            # Pusta linia
            lines.append(Text(""))
        # Wysokość obszaru stosu (reszta minus kwota i zapadnia)
        stack_height = max(0, height - len(lines) - 2)
        # Cegiełek w rzędzie
        per_row = max(1, min(10, width - 2))
        # Liczba paczek do narysowania (po otwarciu – te, które spadły)
        drawn = self.lost if falling else self.bundles
        # Rzędy cegiełek od dołu
        rows = [BRICK * min(per_row, drawn - i * per_row)
                for i in range(math.ceil(drawn / per_row))]
        # Przesunięcie w dół w trakcie spadania
        offset = self.frame if self.state == "opening" else 0
        # Pusta siatka stosu
        grid = [""] * stack_height
        # Umieszczenie rzędów (po otwarciu nic nie zostaje)
        if self.state != "opened":
            # Każdy rząd od dołu
            for i, row in enumerate(rows):
                # Pozycja z przesunięciem
                y = stack_height - 1 - i + offset
                # Tylko w granicach obszaru
                if 0 <= y < stack_height:
                    # Wstawienie rzędu
                    grid[y] = row
        # Napis po otwarciu zapadni
        elif stack_height:
            # Środek obszaru
            grid[stack_height // 2] = "✖ SPADŁO" if self.lost else "pusta"
        # Kolor stosu
        stack_color = success if self.state == "correct" else error if falling else accent
        # Dodanie linii stosu
        for row in grid:
            # Wyśrodkowany rząd
            lines.append(Text(row.center(width), style=Style(color=stack_color, bold=True)))
        # Linia kwoty
        if falling:
            # Strata
            amount = f"−{format_money(bundles_to_money(self.lost))}" if self.lost else "bez strat"
            # Kolor błędu
            amount_style = Style(color=error, bold=True)
        # Poprawna odpowiedź
        elif self.state == "correct":
            # Kwota zachowana
            amount = f"✔ {format_money(bundles_to_money(self.bundles))}"
            # Kolor sukcesu
            amount_style = Style(color=success, bold=True)
        # Zwykły stan
        else:
            # Kwota lub informacja o pustej zapadni
            amount = format_money(bundles_to_money(self.bundles)) if self.bundles else "— pusta —"
            # Złoto dla kwoty, przygaszenie dla pustej
            amount_style = Style(color=accent, bold=True) if self.bundles else Style(dim=True)
        # Dodanie linii kwoty
        lines.append(Text(amount.center(width), style=amount_style))
        # Linia zapadni
        if self.state == "opening":
            # Szerokość szczeliny rośnie z każdą klatką
            gap = min(width, int(width * self.frame / 4))
            # Lewe skrzydło
            left = (width - gap) // 2
            # Rozsuwające się skrzydła zapadni
            door = "▀" * left + " " * gap + "▀" * (width - left - gap)
            # Kolor błędu
            door_style = Style(color=error)
        # Zapadnia otwarta
        elif self.state == "opened":
            # Opadnięte skrzydła na krawędziach
            door = "▘" + " " * max(0, width - 2) + "▝"
            # Kolor błędu
            door_style = Style(color=error)
        # Zapadnia zamknięta
        else:
            # Pełna klapa
            door = "▀" * width
            # Kolor główny lub sukcesu
            door_style = Style(color=success if self.state == "correct" else primary)
        # Dodanie linii zapadni
        lines.append(Text(door, style=door_style))
        # Złożenie wszystkich linii
        return Text("\n").join(lines[:height])


class CategoryCard(TrackedStatic):
    """Karta kategorii do wyboru przed pytaniem."""

    def __init__(self, index: int) -> None:
        # Konstruktor Static
        super().__init__(diag_label=f"Karta kategorii {index + 1}")
        # Indeks karty
        self.index = index

    def set_category(self, name: str, selected: bool) -> None:
        """Ustawia kategorię i wygląd karty."""
        # Klasa wybranej karty
        self.set_class(selected, "-selected")
        # Ikona, nazwa i numer klawisza
        self.update(f"[b]{category_icon(name)}[/b]\n\n[b]{name.upper()}[/b]\n\n[dim]klawisz {self.index + 1}[/dim]")

    def on_click(self) -> None:
        # Kliknięcie – wybór kategorii
        self.screen.category_clicked(self.index)
