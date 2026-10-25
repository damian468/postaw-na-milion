"""Model rozgrywki – czyste zasady teleturnieju, bez żadnego kodu interfejsu.

Zasady (jak w programie TV „Postaw na milion”):
* gracz zaczyna z 1 000 000 zł w 40 paczkach po 25 000 zł,
* przed każdym pytaniem wybiera jedną z dwóch kategorii,
* rozkłada pieniądze na zapadnie z odpowiedziami – co najmniej jedna musi zostać pusta,
* pieniądze niepostawione przed upływem czasu przepadają,
* zapadnie pod błędnymi odpowiedziami otwierają się i pieniądze na nich spadają,
* gra kończy się po ostatnim pytaniu albo gdy gracz straci wszystko.
"""

# ceil – zaokrąglenie w górę (wyświetlamy pełne sekundy)
import math
# random – losowa kolejność otwierania zapadni przy remisach
import random
# Enum – fazy gry
from enum import Enum, auto

# Stałe gry i funkcje pomocnicze
from pnm.config import START_BUNDLES, bundles_to_money, format_money
# Obiekty danych
from pnm.model.entities import RoundQuestion, RoundRecord
# Mechanizm powiadamiania obserwatorów
from pnm.model.observable import EventType, Observable


class GamePhase(Enum):
    """Fazy rozgrywki – kontroler i widoki reagują na nie inaczej."""

    # Brak aktywnej gry
    IDLE = auto()
    # Wybór kategorii przed pytaniem
    CATEGORY = auto()
    # Rozkładanie pieniędzy na zapadnie (biegnie zegar)
    BETTING = auto()
    # Otwieranie zapadni po zamknięciu zakładów
    REVEAL = auto()
    # Runda zakończona, czekamy na gracza
    ROUND_OVER = auto()
    # Gra zakończona
    FINISHED = auto()


class GameModel(Observable):
    """Stan pojedynczej gry wraz z zasadami jej prowadzenia."""

    def __init__(self, rng: random.Random | None = None) -> None:
        # Inicjalizacja mechanizmu obserwatorów
        super().__init__()
        # Generator liczb losowych (można podać własny w testach)
        self._rng = rng or random.Random()
        # Ustawiamy stan początkowy
        self._clear_state()

    # ------------------------------------------------------------------ stan

    def _clear_state(self) -> None:
        """Zeruje wszystkie pola stanu gry."""
        # Bieżąca faza gry
        self.phase = GamePhase.IDLE
        # Imię gracza
        self.player = ""
        # Liczba odpowiedzi w kolejnych rundach
        self.layout: tuple[int, ...] = ()
        # Indeks bieżącej rundy (od 0)
        self.round_index = 0
        # Liczba paczek, które gracz aktualnie posiada
        self.bundles = START_BUNDLES
        # Liczba paczek na starcie (do statystyk)
        self.start_bundles = START_BUNDLES
        # Limit czasu na pytanie w sekundach (0 = brak limitu)
        self.time_limit = 0
        # Pozostały czas w bieżącej rundzie
        self.time_left = 0.0
        # Czy zegar jest wstrzymany
        self.paused = False
        # Dwie kategorie do wyboru
        self.category_options: list[str] = []
        # Pytanie bieżącej rundy
        self.current: RoundQuestion | None = None
        # Liczba paczek na każdej odpowiedzi
        self.bets: list[int] = []
        # Indeksy odpowiedzi, pod którymi otwarto zapadnię
        self.opened: set[int] = set()
        # Kolejka zapadni do otwarcia w fazie REVEAL
        self._reveal_queue: list[int] = []
        # Paczki przed rozpoczęciem bieżącej rundy
        self.bundles_before = START_BUNDLES
        # Paczki utracone przez niepostawienie przed końcem czasu
        self.lost_unplaced = 0
        # Historia zakończonych rund
        self.history: list[RoundRecord] = []

    # ----------------------------------------------------------- właściwości

    @property
    def total_rounds(self) -> int:
        """Liczba pytań w grze."""
        # Długość układu rund
        return len(self.layout)

    @property
    def round_number(self) -> int:
        """Numer bieżącej rundy liczony od 1."""
        # Indeks + 1
        return self.round_index + 1

    @property
    def answers_count(self) -> int:
        """Liczba odpowiedzi w bieżącej rundzie."""
        # Gdy brak układu, zwracamy 0
        if not self.layout:
            # Brak aktywnej gry
            return 0
        # Odczyt z układu rund
        return self.layout[self.round_index]

    @property
    def is_last_round(self) -> bool:
        """Czy bieżąca runda jest ostatnia."""
        # Porównujemy numer rundy z liczbą rund
        return self.round_number >= self.total_rounds

    @property
    def money(self) -> int:
        """Aktualna kwota gracza w złotych."""
        # Przeliczenie paczek na złotówki
        return bundles_to_money(self.bundles)

    @property
    def placed(self) -> int:
        """Liczba paczek postawionych na odpowiedziach."""
        # Suma stawek
        return sum(self.bets)

    @property
    def unplaced(self) -> int:
        """Liczba paczek jeszcze nierozdzielonych."""
        # W fazie odsłaniania nierozdzielone pieniądze już przepadły
        if self.phase in (GamePhase.REVEAL, GamePhase.ROUND_OVER):
            # Nic nie zostało do rozdzielenia
            return 0
        # Różnica posiadanych i postawionych paczek
        return self.bundles - self.placed

    @property
    def empty_answers(self) -> int:
        """Liczba odpowiedzi bez żadnej paczki."""
        # Zliczamy zera na liście stawek
        return sum(1 for bet in self.bets if bet == 0)

    @property
    def seconds_left(self) -> int:
        """Pozostały czas zaokrąglony w górę do pełnych sekund."""
        # Zaokrąglenie w górę – „0:01” widać aż do samego końca
        return math.ceil(self.time_left)

    @property
    def answered_rounds(self) -> int:
        """Liczba rund zakończonych z pieniędzmi na koncie."""
        # Liczymy rekordy historii z dodatnią kwotą po rundzie
        return sum(1 for record in self.history if record.bundles_after > 0)

    # ------------------------------------------------------ przebieg gry

    def start(self, player: str, layout: tuple[int, ...], time_limit: int,
              start_bundles: int = START_BUNDLES) -> None:
        """Rozpoczyna nową grę."""
        # Czyścimy stan po poprzedniej grze
        self._clear_state()
        # Zapisujemy imię gracza
        self.player = player
        # Zapisujemy układ rund
        self.layout = tuple(layout)
        # Zapisujemy limit czasu
        self.time_limit = time_limit
        # Startowa liczba paczek
        self.bundles = start_bundles
        # Zapamiętujemy ją do statystyk
        self.start_bundles = start_bundles
        # Informujemy obserwatorów o nowej grze
        self.emit(EventType.GAME_STARTED)

    def offer_categories(self, categories: list[str]) -> None:
        """Przechodzi do wyboru kategorii z podanej listy."""
        # Zapamiętujemy kategorie
        self.category_options = list(categories)
        # Zmiana fazy
        self.phase = GamePhase.CATEGORY
        # Powiadomienie widoków
        self.emit(EventType.CATEGORIES_OFFERED, categories=self.category_options)

    def start_round(self, round_question: RoundQuestion) -> None:
        """Rozpoczyna rundę z przygotowanym pytaniem."""
        # Ustawiamy bieżące pytanie
        self.current = round_question
        # Zerujemy stawki dla każdej odpowiedzi
        self.bets = [0] * len(round_question.answers)
        # Wszystkie zapadnie zamknięte
        self.opened = set()
        # Pusta kolejka odsłaniania
        self._reveal_queue = []
        # Zapamiętujemy stan konta przed rundą
        self.bundles_before = self.bundles
        # Nic jeszcze nie przepadło
        self.lost_unplaced = 0
        # Pełny czas na odpowiedź
        self.time_left = float(self.time_limit)
        # Zegar nie jest wstrzymany
        self.paused = False
        # Zmiana fazy na stawianie
        self.phase = GamePhase.BETTING
        # Powiadomienie widoków
        self.emit(EventType.ROUND_STARTED)

    # ------------------------------------------------------------ zakłady

    def _can_bet(self, answer: int) -> bool:
        """Czy w tej chwili można zmieniać stawkę na podanej odpowiedzi."""
        # Tylko w fazie stawiania, bez pauzy i dla istniejącej odpowiedzi
        return (self.phase is GamePhase.BETTING and not self.paused
                and 0 <= answer < len(self.bets))

    def _violation(self, message: str) -> None:
        """Wysyła komunikat o złamaniu zasad."""
        # Widoki pokażą go jako ostrzeżenie
        self.emit(EventType.RULE_VIOLATION, message=message)

    def add_bet(self, answer: int, count: int = 1) -> int:
        """Przenosi do `count` paczek z puli na odpowiedź. Zwraca liczbę przeniesionych."""
        # Poza fazą stawiania nic nie robimy
        if not self._can_bet(answer):
            # Brak zmian
            return 0
        # Nie przeniesiemy więcej, niż leży w puli
        count = min(count, self.unplaced)
        # Pula jest pusta
        if count <= 0:
            # Komunikat dla gracza
            self._violation("Wszystkie pieniądze są już rozłożone – zabierz coś z innej zapadni.")
            # Brak zmian
            return 0
        # Gdyby to była ostatnia pusta zapadnia, złamalibyśmy zasadę
        if self.bets[answer] == 0 and self.empty_answers <= 1:
            # Komunikat dla gracza
            self._violation("Przynajmniej jedna zapadnia musi zostać pusta!")
            # Brak zmian
            return 0
        # Przenosimy paczki
        self.bets[answer] += count
        # Powiadamiamy – zmieniła się tylko ta jedna odpowiedź
        self.emit(EventType.BETS_CHANGED, answer=answer)
        # Zwracamy liczbę przeniesionych paczek
        return count

    def remove_bet(self, answer: int, count: int = 1) -> int:
        """Zdejmuje do `count` paczek z odpowiedzi do puli. Zwraca liczbę zdjętych."""
        # Poza fazą stawiania nic nie robimy
        if not self._can_bet(answer):
            # Brak zmian
            return 0
        # Nie zdejmiemy więcej, niż leży na odpowiedzi
        count = min(count, self.bets[answer])
        # Nic do zdjęcia
        if count <= 0:
            # Brak zmian
            return 0
        # Zdejmujemy paczki
        self.bets[answer] -= count
        # Powiadamiamy o zmianie tej odpowiedzi
        self.emit(EventType.BETS_CHANGED, answer=answer)
        # Zwracamy liczbę zdjętych paczek
        return count

    def all_in(self, answer: int) -> int:
        """Stawia całą pulę na wskazaną odpowiedź."""
        # Delegacja do add_bet z maksymalną liczbą paczek
        return self.add_bet(answer, self.unplaced)

    def clear_answer(self, answer: int) -> int:
        """Zdejmuje wszystkie paczki z odpowiedzi."""
        # Nieistniejąca odpowiedź – nic do zdjęcia
        if not self._can_bet(answer):
            # Brak zmian
            return 0
        # Delegacja do remove_bet z pełną stawką
        return self.remove_bet(answer, self.bets[answer])

    def clear_all(self) -> None:
        """Zdejmuje paczki ze wszystkich odpowiedzi."""
        # Dla każdej odpowiedzi z niezerową stawką
        for index, bet in enumerate(self.bets):
            # Jeśli coś na niej leży
            if bet:
                # Zdejmujemy całość
                self.remove_bet(index, bet)

    def lock_problem(self) -> str | None:
        """Zwraca powód, dla którego nie można zamknąć zakładów (lub None)."""
        # Zamykać można tylko w fazie stawiania
        if self.phase is not GamePhase.BETTING:
            # Komunikat techniczny
            return "Teraz nie można zamknąć zakładów."
        # Wszystkie pieniądze muszą leżeć na zapadniach
        if self.unplaced > 0:
            # Komunikat z kwotą do rozdzielenia
            return (f"Rozłóż jeszcze {format_money(bundles_to_money(self.unplaced))}"
                    " – wszystkie pieniądze muszą leżeć na zapadniach.")
        # Wszystko w porządku
        return None

    def lock_bets(self, forced: bool = False) -> bool:
        """Zamyka zakłady. `forced=True` – koniec czasu (niepostawione przepadają)."""
        # Zamykać można tylko w fazie stawiania
        if self.phase is not GamePhase.BETTING:
            # Brak zmian
            return False
        # Przy ręcznym zamknięciu sprawdzamy zasady
        if not forced:
            # Szukamy problemu
            problem = self.lock_problem()
            # Jeśli jest problem – komunikat i rezygnacja
            if problem:
                # Ostrzeżenie dla gracza
                self._violation(problem)
                # Zakłady pozostają otwarte
                return False
        # Niepostawione paczki przepadają
        self.lost_unplaced = self.bundles - self.placed
        # Gracz zachowuje tylko to, co leży na zapadniach
        self.bundles = self.placed
        # Kolejność otwierania: najpierw puste, potem rosnąco wg stawek (budowanie napięcia)
        wrong = [i for i in range(len(self.bets)) if i != self.current.correct_index]
        # Sortowanie z losowym rozstrzyganiem remisów
        self._reveal_queue = sorted(wrong, key=lambda i: (self.bets[i], self._rng.random()))
        # Zegar przestaje mieć znaczenie
        self.paused = False
        # Zmiana fazy na odsłanianie
        self.phase = GamePhase.REVEAL
        # Powiadomienie widoków
        self.emit(EventType.BETS_LOCKED, forced=forced, lost_unplaced=self.lost_unplaced)
        # Zakłady zamknięte
        return True

    # --------------------------------------------------------------- zegar

    def tick(self, dt: float) -> bool:
        """Odlicza czas. Zwraca True, gdy czas właśnie się skończył."""
        # Zegar działa tylko w fazie stawiania, bez pauzy i z limitem czasu
        if self.phase is not GamePhase.BETTING or self.paused or self.time_limit <= 0:
            # Czas się nie skończył
            return False
        # Pełne sekundy przed odliczeniem
        before = self.seconds_left
        # Odejmujemy upływ czasu (nie schodzimy poniżej zera)
        self.time_left = max(0.0, self.time_left - dt)
        # Zdarzenie tylko przy zmianie pełnej sekundy – widok zegara odświeża się raz na sekundę
        if self.seconds_left != before:
            # Powiadomienie z nową liczbą sekund
            self.emit(EventType.TIME_CHANGED, seconds=self.seconds_left)
        # Czy czas właśnie minął
        return self.time_left <= 0

    def set_paused(self, paused: bool) -> None:
        """Wstrzymuje lub wznawia zegar."""
        # Pauza ma sens tylko podczas stawiania
        if self.phase is not GamePhase.BETTING or self.paused == paused:
            # Brak zmian
            return
        # Zmiana stanu
        self.paused = paused
        # Powiadomienie widoków
        self.emit(EventType.PAUSE_CHANGED, paused=paused)

    # ------------------------------------------------------------ odsłanianie

    @property
    def closed_wrong_left(self) -> int:
        """Liczba zamkniętych jeszcze zapadni pod błędnymi odpowiedziami."""
        # Długość kolejki odsłaniania
        return len(self._reveal_queue)

    def open_next_trapdoor(self) -> int | None:
        """Otwiera kolejną zapadnię pod błędną odpowiedzią. Zwraca jej indeks."""
        # Tylko w fazie odsłaniania i gdy coś zostało w kolejce
        if self.phase is not GamePhase.REVEAL or not self._reveal_queue:
            # Nic nie otwarto
            return None
        # Pobieramy kolejną zapadnię
        answer = self._reveal_queue.pop(0)
        # Pieniądze na niej przepadają
        lost = self.bets[answer]
        # Oznaczamy zapadnię jako otwartą
        self.opened.add(answer)
        # Odejmujemy stracone paczki
        self.bundles -= lost
        # Powiadomienie widoków (animacja spadających pieniędzy)
        self.emit(EventType.TRAPDOOR_OPENED, answer=answer, lost=lost)
        # Zwracamy indeks otwartej zapadni
        return answer

    def reveal_correct(self) -> None:
        """Kończy odsłanianie – pokazuje poprawną odpowiedź."""
        # Tylko w fazie odsłaniania
        if self.phase is not GamePhase.REVEAL:
            # Brak zmian
            return
        # Otwieramy ewentualne pozostałe błędne zapadnie
        while self._reveal_queue:
            # Kolejna zapadnia
            self.open_next_trapdoor()
        # Zapisujemy przebieg rundy w historii
        self.history.append(RoundRecord(
            # Numer rundy
            number=self.round_number,
            # Kategoria
            category=self.current.category,
            # Treść pytania
            question=self.current.text,
            # Odpowiedzi
            answers=list(self.current.answers),
            # Poprawna odpowiedź
            correct_index=self.current.correct_index,
            # Stawki
            bets=list(self.bets),
            # Stan konta przed rundą
            bundles_before=self.bundles_before,
            # Stan konta po rundzie
            bundles_after=self.bundles,
            # Paczki utracone przez upływ czasu
            lost_unplaced=self.lost_unplaced,
        ))
        # Zmiana fazy
        self.phase = GamePhase.ROUND_OVER
        # Powiadomienie widoków
        self.emit(EventType.CORRECT_REVEALED, answer=self.current.correct_index,
                  kept=self.bundles)

    @property
    def can_continue(self) -> bool:
        """Czy po zakończonej rundzie jest kolejne pytanie."""
        # Gracz musi mieć pieniądze i nie może to być ostatnia runda
        return self.bundles > 0 and not self.is_last_round

    def advance_round(self) -> None:
        """Przechodzi do następnej rundy (przed wyborem kategorii)."""
        # Zwiększamy indeks rundy
        self.round_index += 1

    def finish(self) -> None:
        """Kończy grę."""
        # Zmiana fazy
        self.phase = GamePhase.FINISHED
        # Powiadomienie widoków
        self.emit(EventType.GAME_FINISHED, amount=self.money, won=self.bundles > 0)

    def abandon(self) -> None:
        """Przerywa grę bez zapisu wyniku."""
        # Czyścimy stan
        self._clear_state()
