"""Ekran rozgrywki: wybór kategorii, rozkładanie pieniędzy, otwieranie zapadni."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ContentSwitcher

# Stałe i formatowanie
from pnm.config import ANSWER_LETTERS, format_money
# Model gry
from pnm.model.game import GamePhase
# Zdarzenia
from pnm.model.observable import Event, EventType
# Escapowanie znaków markupu w tekstach z bazy
from rich.markup import escape
# Duża czcionka i ikony
from pnm.view.tui.ascii_art import category_icon
# Widżety gry
from pnm.view.tui.game_widgets import (AnswerColumn, CategoryCard, Ladder, PoolBar,
                                       TimerBox)
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Okna dialogowe
from pnm.view.tui.screens.dialogs import ConfirmDialog, PauseDialog
# Widżety ogólne
from pnm.view.tui.widgets import TrackedStatic

# Akcje dostępne w poszczególnych fazach gry (steruje też stopką)
PHASE_ACTIONS = {
    # Wybór kategorii
    GamePhase.CATEGORY: {"move", "pick", "confirm"},
    # Rozkładanie pieniędzy
    GamePhase.BETTING: {"move", "pick", "confirm", "add", "remove", "all_in", "clear",
                        "reset", "pause"},
    # Otwieranie zapadni
    GamePhase.REVEAL: {"skip"},
    # Koniec rundy
    GamePhase.ROUND_OVER: {"confirm"},
}


class GameScreen(BaseScreen):
    """Główny ekran gry. Reaguje na zdarzenia modelu, odświeżając tylko zmienione widżety."""

    # Skróty klawiszowe (stopka pokazuje tylko te dostępne w bieżącej fazie)
    BINDINGS = [
        # Wybór kolumny / kategorii
        Binding("left", "move(-1)", "Wybór", key_display="←→"),
        # Wybór w prawo (ukryty w stopce – opisany przy strzałce w lewo)
        Binding("right", "move(1)", "Wybór", show=False),
        # Bezpośredni wybór klawiszami 1–4
        Binding("1", "pick(0)", show=False),
        # Bezpośredni wybór
        Binding("2", "pick(1)", show=False),
        # Bezpośredni wybór
        Binding("3", "pick(2)", show=False),
        # Bezpośredni wybór
        Binding("4", "pick(3)", show=False),
        # Dołożenie paczki
        Binding("up,plus", "add(1)", "+25 tys.", key_display="↑/+"),
        # Zdjęcie paczki
        Binding("down,minus", "remove(1)", "−25 tys.", key_display="↓/−"),
        # Dołożenie 10 paczek
        Binding("pageup", "add(10)", "+250 tys.", key_display="PgUp"),
        # Zdjęcie 10 paczek
        Binding("pagedown", "remove(10)", "−250 tys.", key_display="PgDn"),
        # Wszystko na wybraną odpowiedź
        Binding("a", "all_in", "Wszystko tu"),
        # Wyczyszczenie wybranej odpowiedzi
        Binding("backspace,delete", "clear", "Zdejmij", key_display="⌫"),
        # Wyczyszczenie wszystkich odpowiedzi
        Binding("r", "reset", "Od nowa"),
        # Zatwierdzenie
        Binding("enter", "confirm", "Zatwierdź"),
        # Pominięcie animacji
        Binding("space,enter", "skip", "Pomiń animację", key_display="Spacja"),
        # Pauza
        Binding("p", "pause", "Pauza"),
        # Przerwanie gry
        Binding("escape", "quit_game", "Przerwij grę"),
    ]

    def compose_content(self):
        # Skrót do modelu
        game = self.ctx.game
        # Pasek nagłówka
        with Horizontal(id="game-header"):
            # Numer pytania
            yield TrackedStatic(id="round-box", diag_label="Numer pytania")
            # Stan konta
            yield TrackedStatic(id="bank-box", diag_label="Stan konta")
            # Zegar
            yield TimerBox(id="timer-box")
        # Część główna
        with Horizontal(id="game-body"):
            # Drabinka pytań
            yield Ladder(game, id="ladder")
            # Przełącznik: wybór kategorii / plansza
            with ContentSwitcher(initial="category-view", id="switcher"):
                # Widok wyboru kategorii
                with Vertical(id="category-view"):
                    # Nagłówek wyboru
                    yield TrackedStatic(id="category-title", diag_label="Tytuł kategorii")
                    # Dwie karty
                    with Horizontal(id="category-cards"):
                        # Karta pierwsza
                        yield CategoryCard(0)
                        # Karta druga
                        yield CategoryCard(1)
                    # Podpowiedź
                    yield TrackedStatic("←→ lub 1/2 – wybór kategorii   ·   Enter – zatwierdź",
                                        id="category-hint", diag_label="Podpowiedź")
                # Widok planszy
                with Vertical(id="board-view"):
                    # Panel z pytaniem
                    yield TrackedStatic(id="question", diag_label="Pytanie")
                    # Pasek puli
                    yield PoolBar(id="pool")
                    # Kontener kolumn odpowiedzi
                    yield Horizontal(id="answers")
                    # Linia statusu
                    yield TrackedStatic(id="status", diag_label="Status rundy")

    # --------------------------------------------------------------- start

    def on_mount(self) -> None:
        # Wybrana kolumna odpowiedzi
        self._selected = 0
        # Wybrana karta kategorii
        self._category = 0
        # Lista kolumn bieżącej rundy
        self._columns: list[AnswerColumn] = []
        # Subskrypcja zdarzeń modelu gry
        self.observe(self.ctx.game, self._on_game_event)
        # Zegar
        timer = self.query_one(TimerBox)
        # Limit czasu i pełny czas przed pierwszym pytaniem
        timer.limit, timer.seconds = self.ctx.game.time_limit, self.ctx.game.time_limit
        # Pierwsze narysowanie nagłówka
        self._update_header()
        # Pokazanie stanu, w jakim jest gra (zwykle wybór kategorii)
        if self.ctx.game.phase is GamePhase.CATEGORY:
            # Karty kategorii
            self._show_categories()

    # ------------------------------------------------- obsługa zdarzeń modelu

    def _on_game_event(self, event: Event) -> None:
        """Rozdziela zdarzenia modelu do widżetów, których dotyczą."""
        # Skrót do modelu
        game = self.ctx.game
        # Typ zdarzenia
        kind = event.type
        # Nowe kategorie do wyboru
        if kind is EventType.CATEGORIES_OFFERED:
            # Pokazanie kart
            self._show_categories()
        # Start rundy
        elif kind is EventType.ROUND_STARTED:
            # Zbudowanie planszy
            self._show_board()
        # Zmiana stawki na jednej odpowiedzi
        elif kind is EventType.BETS_CHANGED:
            # Indeks odpowiedzi
            index = event.data["answer"]
            # Odświeżenie tylko tej kolumny
            self._columns[index].bundles = game.bets[index]
            # Odświeżenie paska puli
            self.query_one(PoolBar).unplaced = game.unplaced
        # Zmiana sekundy na zegarze
        elif kind is EventType.TIME_CHANGED:
            # Odświeżenie tylko zegara
            self.query_one(TimerBox).seconds = event.data["seconds"]
        # Pauza
        elif kind is EventType.PAUSE_CHANGED:
            # Znacznik pauzy na zegarze
            self.query_one(TimerBox).paused = event.data["paused"]
        # Zamknięcie zakładów
        elif kind is EventType.BETS_LOCKED:
            # Obsługa zamknięcia
            self._on_locked(event.data["forced"], event.data["lost_unplaced"])
        # Otwarcie zapadni
        elif kind is EventType.TRAPDOOR_OPENED:
            # Animacja w jednej kolumnie
            self._columns[event.data["answer"]].open_trapdoor(event.data["lost"],
                                                              self.ctx.settings["animation"])
            # Aktualizacja stanu konta
            self._update_header()
        # Ujawnienie poprawnej odpowiedzi
        elif kind is EventType.CORRECT_REVEALED:
            # Podświetlenie poprawnej kolumny
            self._columns[event.data["answer"]].mark_correct()
            # Aktualizacja drabinki (nowy wynik rundy)
            self.query_one(Ladder).refresh()
            # Aktualizacja nagłówka
            self._update_header()
            # Komunikat końca rundy
            self._set_round_over_status()
        # Złamanie zasad
        elif kind is EventType.RULE_VIOLATION:
            # Komunikat ostrzegawczy
            self.app.notify(event.data["message"], severity="warning", timeout=3)
            # Mignięcie wybranej kolumny
            self._flash()
        # Odświeżenie stopki ze skrótami (zależą od fazy)
        self.refresh_bindings()

    # ------------------------------------------------------------- widoki

    def _update_header(self) -> None:
        """Aktualizuje numer pytania i stan konta."""
        # Skrót do modelu
        game = self.ctx.game
        # Numer pytania
        self.query_one("#round-box", TrackedStatic).update(
            f"[dim]PYTANIE[/dim]\n[b]{game.round_number} / {game.total_rounds}[/b]\n"
            f"[dim]{game.answers_count} odpowiedzi[/dim]")
        # Stan konta
        self.query_one("#bank-box", TrackedStatic).update(
            f"[dim]{game.player.upper()} – NA KONCIE[/dim]\n[b $accent]{format_money(game.money)}[/b $accent]"
            f"\n[dim]{game.bundles} paczek po 25 000 zł[/dim]")

    def _show_categories(self) -> None:
        """Pokazuje wybór kategorii."""
        # Skrót do modelu
        game = self.ctx.game
        # Pierwsza karta wybrana
        self._category = 0
        # Tytuł
        self.query_one("#category-title", TrackedStatic).update(
            f"[b]PYTANIE {game.round_number} Z {game.total_rounds}[/b]   ·   "
            f"{game.answers_count} możliwe odpowiedzi\n\n[b $accent]WYBIERZ KATEGORIĘ[/]")
        # Karty
        cards = list(self.query(CategoryCard))
        # Ustawienie kart
        for card in cards:
            # Karta ma kategorię, gdy jest jej odpowiednik w modelu
            card.display = card.index < len(game.category_options)
            # Uzupełnienie treści
            if card.display:
                # Nazwa i zaznaczenie
                card.set_category(game.category_options[card.index], card.index == 0)
        # Aktualizacja nagłówka i drabinki
        self._update_header()
        # Drabinka – nowa bieżąca runda
        self.query_one(Ladder).refresh()
        # Przełączenie widoku
        self.query_one(ContentSwitcher).current = "category-view"

    def _show_board(self) -> None:
        """Buduje planszę dla nowej rundy."""
        # Skrót do modelu
        game = self.ctx.game
        # Bieżące pytanie
        question = game.current
        # Panel pytania
        self.query_one("#question", TrackedStatic).update(
            f"[b $accent]{category_icon(question.category)}  {escape(question.category.upper())}[/]\n"
            f"[b]{escape(question.text)}[/b]")
        # Kontener kolumn
        container = self.query_one("#answers")
        # Usunięcie kolumn poprzedniej rundy
        container.remove_children()
        # Nowe kolumny
        self._columns = [AnswerColumn(i, ANSWER_LETTERS[i], answer)
                         for i, answer in enumerate(question.answers)]
        # Wstawienie kolumn
        container.mount(*self._columns)
        # Wybrana pierwsza kolumna
        self._selected = 0
        # Zaznaczenie
        self._columns[0].selected = True
        # Pasek puli
        pool = self.query_one(PoolBar)
        # Reset paska
        pool.locked, pool.lost, pool.unplaced = False, 0, game.unplaced
        # Zegar
        timer = self.query_one(TimerBox)
        # Reset zegara
        timer.limit, timer.seconds, timer.paused = game.time_limit, game.seconds_left, False
        # Status
        self._set_status("Rozłóż [b]wszystkie[/b] pieniądze na odpowiedzi. "
                         "[b $warning]Co najmniej jedna zapadnia musi zostać pusta![/]")
        # Nagłówek
        self._update_header()
        # Przełączenie widoku
        self.query_one(ContentSwitcher).current = "board-view"

    def _on_locked(self, forced: bool, lost_unplaced: int) -> None:
        """Reakcja na zamknięcie zakładów."""
        # Pasek puli
        pool = self.query_one(PoolBar)
        # Tryb zamknięty
        pool.locked, pool.lost = True, lost_unplaced
        # Odznaczenie wybranej kolumny
        self._columns[self._selected].selected = False
        # Aktualizacja konta (nierozłożone przepadły)
        self._update_header()
        # Komunikat przy końcu czasu
        if forced:
            # Powiadomienie
            self.app.notify("Czas minął! Zakłady zostały zamknięte.", severity="error", timeout=3)
        # Status
        self._set_status("Zapadnie otwierają się…   [dim][Spacja] – pomiń animację[/dim]")

    def _set_round_over_status(self) -> None:
        """Komunikat po zakończeniu rundy."""
        # Skrót do modelu
        game = self.ctx.game
        # Gracz stracił wszystko
        if game.bundles == 0:
            # Komunikat porażki
            self._set_status("[b $error]Niestety, wszystkie pieniądze spadły…[/]   "
                             "[b]Enter[/b] – podsumowanie")
        # Ostatnie pytanie z wygraną
        elif not game.can_continue:
            # Komunikat zwycięstwa
            self._set_status(f"[b $success]BRAWO! Wygrywasz {format_money(game.money)}![/]   "
                             "[b]Enter[/b] – podsumowanie")
        # Kolejna runda
        else:
            # Komunikat przejściowy
            self._set_status(f"Zostaje Ci [b $accent]{format_money(game.money)}[/]   "
                             "[b]Enter[/b] – następne pytanie")

    def _set_status(self, text: str) -> None:
        """Ustawia linię statusu."""
        # Aktualizacja jednego widżetu
        self.query_one("#status", TrackedStatic).update(text)

    def _flash(self) -> None:
        """Mignięcie wybranej kolumny przy złamaniu zasad."""
        # Bez kolumn nie ma czego podświetlać
        if not self._columns:
            # Wyjście
            return
        # Wybrana kolumna
        column = self._columns[self._selected]
        # Klasa podświetlenia błędu
        column.add_class("-flash")
        # Usunięcie klasy po chwili
        self.set_timer(0.35, lambda: column.remove_class("-flash"))

    # ---------------------------------------------------------- akcje

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Włącza tylko akcje sensowne w bieżącej fazie gry."""
        # Akcje dostępne zawsze
        if action not in {"move", "pick", "confirm", "add", "remove", "all_in", "clear",
                          "reset", "pause", "skip"}:
            # Dozwolone
            return True
        # Akcje bieżącej fazy
        return action in PHASE_ACTIONS.get(self.ctx.game.phase, set())

    def _select_column(self, index: int) -> None:
        """Zmienia wybraną kolumnę – odświeża tylko dwie kolumny."""
        # Bez kolumn nic nie robimy
        if not self._columns:
            # Wyjście
            return
        # Indeks z zawijaniem
        index %= len(self._columns)
        # Odznaczenie poprzedniej
        self._columns[self._selected].selected = False
        # Zapamiętanie nowej
        self._selected = index
        # Zaznaczenie nowej
        self._columns[index].selected = True

    def _select_category(self, index: int) -> None:
        """Zmienia wybraną kartę kategorii."""
        # Liczba dostępnych kategorii
        count = len(self.ctx.game.category_options)
        # Nowy indeks z zawijaniem
        self._category = index % count
        # Aktualizacja obu kart
        for card in self.query(CategoryCard):
            # Tylko widoczne karty
            if card.index < count:
                # Nazwa i zaznaczenie
                card.set_category(self.ctx.game.category_options[card.index],
                                  card.index == self._category)

    def action_move(self, step: int) -> None:
        # Wybór kategorii
        if self.ctx.game.phase is GamePhase.CATEGORY:
            # Przesunięcie karty
            self._select_category(self._category + step)
        # Wybór kolumny
        else:
            # Przesunięcie kolumny
            self._select_column(self._selected + step)

    def action_pick(self, index: int) -> None:
        # Wybór kategorii od razu zatwierdza
        if self.ctx.game.phase is GamePhase.CATEGORY:
            # Przekazanie do kontrolera
            self.ctx.game_controller.choose_category(index)
        # Wybór kolumny o numerze (jeśli istnieje)
        elif index < len(self._columns):
            # Zaznaczenie
            self._select_column(index)

    def action_add(self, count: int) -> None:
        # Dołożenie paczek na wybraną odpowiedź
        self.ctx.game_controller.add(self._selected, count)

    def action_remove(self, count: int) -> None:
        # Zdjęcie paczek z wybranej odpowiedzi
        self.ctx.game_controller.remove(self._selected, count)

    def action_all_in(self) -> None:
        # Cała pula na wybraną odpowiedź
        self.ctx.game_controller.all_in(self._selected)

    def action_clear(self) -> None:
        # Wyczyszczenie wybranej odpowiedzi
        self.ctx.game_controller.clear_answer(self._selected)

    def action_reset(self) -> None:
        # Wyczyszczenie wszystkich odpowiedzi
        self.ctx.game_controller.clear_all()

    def action_confirm(self) -> None:
        # Faza gry
        phase = self.ctx.game.phase
        # Wybór kategorii
        if phase is GamePhase.CATEGORY:
            # Zatwierdzenie wybranej karty
            self.ctx.game_controller.choose_category(self._category)
        # Zamknięcie zakładów
        elif phase is GamePhase.BETTING:
            # Przekazanie do kontrolera
            self.ctx.game_controller.lock()
        # Następna runda / podsumowanie
        elif phase is GamePhase.ROUND_OVER:
            # Przekazanie do kontrolera
            self.ctx.game_controller.continue_game()

    def action_skip(self) -> None:
        # Natychmiastowe ujawnienie wyniku
        self.ctx.game_controller.skip_reveal()

    def action_pause(self) -> None:
        # Wstrzymanie zegara
        self.ctx.game_controller.set_paused(True)
        # Okno pauzy, po zamknięciu – wznowienie
        self.app.push_screen(PauseDialog(), lambda _: self.ctx.game_controller.set_paused(False))

    def action_quit_game(self) -> None:
        # Wstrzymanie zegara na czas pytania
        self.ctx.game_controller.set_paused(True)

        def answer(confirmed: bool) -> None:
            # Gracz potwierdził przerwanie
            if confirmed:
                # Przerwanie gry
                self.ctx.game_controller.abandon()
            # Gracz zrezygnował
            else:
                # Wznowienie zegara
                self.ctx.game_controller.set_paused(False)

        # Okno potwierdzenia
        self.app.push_screen(ConfirmDialog("Przerwać grę?",
                                           "Wynik tej gry nie zostanie zapisany w rankingu."),
                             answer)

    # ------------------------------------------------------------- mysz

    def column_clicked(self, index: int) -> None:
        """Kliknięcie kolumny myszą."""
        # Tylko podczas stawiania
        if self.ctx.game.phase is GamePhase.BETTING:
            # Zaznaczenie kolumny
            self._select_column(index)

    def column_scrolled(self, index: int, direction: int) -> None:
        """Kółko myszy nad kolumną – dokłada lub zdejmuje paczkę."""
        # Tylko podczas stawiania
        if self.ctx.game.phase is not GamePhase.BETTING:
            # Wyjście
            return
        # Zaznaczenie kolumny pod kursorem
        self._select_column(index)
        # Dołożenie lub zdjęcie
        if direction > 0:
            # Dołożenie paczki
            self.ctx.game_controller.add(index, 1)
        # Zdjęcie paczki
        else:
            # Zdjęcie
            self.ctx.game_controller.remove(index, 1)

    def category_clicked(self, index: int) -> None:
        """Kliknięcie karty kategorii."""
        # Tylko w fazie wyboru kategorii
        if self.ctx.game.phase is GamePhase.CATEGORY:
            # Zatwierdzenie
            self.ctx.game_controller.choose_category(index)
