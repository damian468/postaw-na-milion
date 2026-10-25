"""Kontroler rozgrywki – tłumaczy akcje gracza na operacje modelu i steruje czasem."""

# Obiekty i stałe konfiguracyjne
from pnm.config import ANSWER_LAYOUTS, target_difficulty
# Interfejs widoku
from pnm.controller.view_interface import ScreenId, View
# Model gry
from pnm.model.game import GameModel, GamePhase
# Klient internetowej bazy pytań
from pnm.model.online import OnlineError, OpenTriviaClient
# Pula pytań na jedną grę
from pnm.model.question_pool import QuestionPool
# Bank pytań i ranking
from pnm.model.repositories import QuestionBank, Ranking
# Ustawienia
from pnm.model.settings import SettingsModel

# Opóźnienia odsłaniania: (przed pierwszą zapadnią, między zapadniami, przed poprawną)
REVEAL_TIMING = {
    # Pełne napięcie jak w telewizji
    "normal": (1.2, 1.8, 1.6),
    # Przyspieszone
    "fast": (0.5, 0.8, 0.7),
    # Natychmiastowe
    "off": (0.0, 0.0, 0.0),
}

# Od tej liczby sekund zegar zaczyna „pikać”
WARNING_SECONDS = 10


class GameController:
    """Steruje przebiegiem gry: rundy, zegar, sekwencja otwierania zapadni."""

    def __init__(self, game: GameModel, bank: QuestionBank, ranking: Ranking,
                 settings: SettingsModel, online: OpenTriviaClient | None = None) -> None:
        # Model gry
        self.game = game
        # Bank pytań
        self._bank = bank
        # Ranking
        self._ranking = ranking
        # Ustawienia
        self._settings = settings
        # Klient OpenTDB
        self._online = online or OpenTriviaClient()
        # Widok (ustawiany przez attach_view)
        self._view: View | None = None
        # Pula pytań bieżącej gry
        self._pool: QuestionPool | None = None
        # Czas do następnego kroku odsłaniania
        self._reveal_timer = 0.0
        # Miejsce w rankingu po ostatniej grze
        self.last_rank: int | None = None
        # Źródło pytań faktycznie użyte w bieżącej grze
        self._source_used = "local"

    def attach_view(self, view: View) -> None:
        """Podłącza widok."""
        # Zapamiętanie widoku
        self._view = view

    # ---------------------------------------------------------- start gry

    def prepare_pool(self) -> str | None:
        """Buduje pulę pytań (operacja blokująca – wywoływana w tle).

        Zwraca komunikat dla gracza (np. o braku Internetu) albo None.
        """
        # Wybrane w ustawieniach źródło pytań
        source = self._settings["question_source"]
        # Pytania lokalne (gdy źródło je obejmuje)
        questions = self._bank.all() if source in ("local", "mixed") else []
        # Komunikat dla gracza
        note = None
        # Źródło faktycznie użyte
        self._source_used = source
        # Pobieranie z Internetu
        if source in ("online", "mixed"):
            # Próba pobrania
            try:
                # Dołączenie pytań z sieci
                questions += self._online.fetch(50)
            # Brak Internetu – wracamy do bazy lokalnej
            except OnlineError as error:
                # Komunikat o problemie
                note = f"{error}. Gram na pytaniach z lokalnej bazy."
                # Gdy nie mamy jeszcze pytań lokalnych – dobieramy je
                if source == "online":
                    # Pytania lokalne jako zapas
                    questions = self._bank.all()
                # Zapamiętanie faktycznego źródła
                self._source_used = "local"
        # Utworzenie puli
        self._pool = QuestionPool(questions)
        # Zwracamy komunikat
        return note

    def start_game(self, note: str | None = None) -> None:
        """Rozpoczyna grę na przygotowanej puli (wywoływane w wątku UI)."""
        # Bez puli nie da się grać
        if self._pool is None or self._pool.size == 0:
            # Komunikat błędu
            self._view.notify("Brak pytań w bazie – dodaj pytania w edytorze.", "error")
            # Powrót do menu
            self._view.navigate(ScreenId.MAIN_MENU)
            # Wyjście
            return
        # Ewentualny komunikat z etapu przygotowania
        if note:
            # Ostrzeżenie
            self._view.notify(note, "warning")
        # Start modelu z bieżącymi ustawieniami
        self.game.start(
            # Imię gracza
            player=self._settings["player_name"],
            # Układ rund
            layout=ANSWER_LAYOUTS[self._settings["game_length"]],
            # Limit czasu
            time_limit=self._settings["time_limit"],
        )
        # Propozycja kategorii do pierwszego pytania
        self._offer_categories()
        # Pokazanie ekranu gry
        self._view.navigate(ScreenId.GAME)

    def _offer_categories(self) -> None:
        """Losuje kategorie i przekazuje je do modelu."""
        # Losowanie dwóch kategorii
        categories = self._pool.pick_categories(2)
        # Skończyły się pytania – kończymy grę
        if not categories:
            # Komunikat
            self._view.notify("Skończyły się pytania – gra zakończona.", "warning")
            # Zakończenie gry
            self._finish()
            # Wyjście
            return
        # Przekazanie do modelu
        self.game.offer_categories(categories)

    # ------------------------------------------------------- akcje gracza

    def choose_category(self, index: int) -> None:
        """Gracz wybrał kategorię o podanym indeksie."""
        # Tylko w fazie wyboru kategorii i dla istniejącego indeksu
        if self.game.phase is not GamePhase.CATEGORY or not (
                0 <= index < len(self.game.category_options)):
            # Ignorujemy
            return
        # Nazwa kategorii
        category = self.game.category_options[index]
        # Trudność dopasowana do postępu gry
        difficulty = target_difficulty(self.game.round_index, self.game.total_rounds)
        # Wylosowanie pytania
        question = self._pool.draw(category, difficulty, self.game.answers_count)
        # Start rundy w modelu
        self.game.start_round(question)

    def add(self, answer: int, count: int = 1) -> None:
        """Dokłada paczki na odpowiedź."""
        # Delegacja do modelu
        self.game.add_bet(answer, count)

    def remove(self, answer: int, count: int = 1) -> None:
        """Zdejmuje paczki z odpowiedzi."""
        # Delegacja do modelu
        self.game.remove_bet(answer, count)

    def all_in(self, answer: int) -> None:
        """Stawia całą pulę na odpowiedź."""
        # Delegacja do modelu
        self.game.all_in(answer)

    def clear_answer(self, answer: int) -> None:
        """Zdejmuje wszystko z odpowiedzi."""
        # Delegacja do modelu
        self.game.clear_answer(answer)

    def clear_all(self) -> None:
        """Zdejmuje wszystko ze wszystkich odpowiedzi."""
        # Delegacja do modelu
        self.game.clear_all()

    def lock(self) -> None:
        """Gracz zamyka zakłady."""
        # Próba zamknięcia (model sam sprawdzi zasady)
        if self.game.lock_bets():
            # Odliczanie do pierwszej zapadni
            self._reveal_timer = self._timing[0]

    def set_paused(self, paused: bool) -> None:
        """Wstrzymuje lub wznawia zegar."""
        # Delegacja do modelu
        self.game.set_paused(paused)

    def skip_reveal(self) -> None:
        """Przyspiesza odsłanianie – od razu pokazuje wynik rundy."""
        # Tylko w fazie odsłaniania
        if self.game.phase is GamePhase.REVEAL:
            # Natychmiastowe ujawnienie
            self.game.reveal_correct()

    def continue_game(self) -> None:
        """Po zakończonej rundzie: następne pytanie albo koniec gry."""
        # Tylko po zakończonej rundzie
        if self.game.phase is not GamePhase.ROUND_OVER:
            # Ignorujemy
            return
        # Jest kolejne pytanie
        if self.game.can_continue:
            # Następna runda
            self.game.advance_round()
            # Wybór kategorii
            self._offer_categories()
        # Koniec gry
        else:
            # Zakończenie
            self._finish()

    def abandon(self) -> None:
        """Przerywa grę bez zapisu i wraca do menu."""
        # Wyczyszczenie modelu
        self.game.abandon()
        # Powrót do menu
        self._view.navigate(ScreenId.MAIN_MENU)

    # ------------------------------------------------------------- zegar

    @property
    def _timing(self) -> tuple[float, float, float]:
        """Opóźnienia odsłaniania wg ustawień animacji."""
        # Odczyt z tabeli
        return REVEAL_TIMING[self._settings["animation"]]

    def tick(self, dt: float) -> None:
        """Wywoływane cyklicznie przez widok (ok. 10 razy na sekundę)."""
        # Faza stawiania – odliczamy czas
        if self.game.phase is GamePhase.BETTING:
            # Sekundy przed odliczeniem
            before = self.game.seconds_left
            # Odliczanie w modelu
            expired = self.game.tick(dt)
            # Sygnał dźwiękowy w ostatnich sekundach
            if (self.game.time_limit and self.game.seconds_left != before
                    and self.game.seconds_left <= WARNING_SECONDS):
                # Dźwięk tylko gdy włączony
                self._beep()
            # Czas minął – zakłady zamykają się same
            if expired:
                # Wymuszone zamknięcie
                self.game.lock_bets(forced=True)
                # Odliczanie do pierwszej zapadni
                self._reveal_timer = self._timing[0]
        # Faza odsłaniania – kolejne zapadnie
        elif self.game.phase is GamePhase.REVEAL:
            # Odliczanie do następnego kroku
            self._reveal_timer -= dt
            # Jeszcze nie czas
            if self._reveal_timer > 0:
                # Wyjście
                return
            # Są jeszcze zamknięte błędne zapadnie
            if self.game.closed_wrong_left:
                # Otwarcie kolejnej
                self.game.open_next_trapdoor()
                # Dźwięk otwarcia
                self._beep()
                # Ostatnia błędna – dłuższa pauza przed ujawnieniem
                last = self.game.closed_wrong_left == 0
                # Ustawienie odliczania
                self._reveal_timer = self._timing[2] if last else self._timing[1]
            # Wszystkie błędne otwarte – ujawniamy poprawną
            else:
                # Ujawnienie
                self.game.reveal_correct()

    def _beep(self) -> None:
        """Sygnał dźwiękowy, jeśli włączony w ustawieniach."""
        # Sprawdzenie ustawienia
        if self._settings["sound"] and self._view:
            # Dźwięk
            self._view.bell()

    # ------------------------------------------------------------ koniec

    def _finish(self) -> None:
        """Kończy grę, zapisuje wynik i pokazuje podsumowanie."""
        # Zakończenie w modelu
        self.game.finish()
        # Zapis w rankingu
        self.last_rank = self._ranking.add(
            # Imię gracza
            player=self.game.player,
            # Wygrana
            amount=self.game.money,
            # Liczba pytań z sukcesem
            answered=self.game.answered_rounds,
            # Łączna liczba pytań
            total=self.game.total_rounds,
            # Limit czasu
            time_limit=self.game.time_limit,
            # Źródło pytań
            source=self._source_used,
        )
        # Ekran podsumowania
        self._view.navigate(ScreenId.SUMMARY)
