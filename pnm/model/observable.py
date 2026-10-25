"""Wzorzec Obserwator – model powiadamia widoki o zmianach bez znajomości ich typu.

Dzięki temu ten sam model może obsługiwać widok tekstowy (Textual) i graficzny
(tkinter). Każdy widżet subskrybuje tylko te zdarzenia, które go dotyczą, więc
odświeżane są wyłącznie elementy, które faktycznie się zmieniły.
"""

# dataclass upraszcza definicję niezmiennego obiektu zdarzenia
from dataclasses import dataclass, field
# Enum – czytelne, zamknięte zbiory typów zdarzeń
from enum import Enum, auto
# Typy pomocnicze do adnotacji
from typing import Any, Callable


class EventType(Enum):
    """Wszystkie rodzaje zdarzeń emitowanych przez modele."""

    # Rozpoczęto nową grę
    GAME_STARTED = auto()
    # Zaproponowano graczowi dwie kategorie do wyboru
    CATEGORIES_OFFERED = auto()
    # Rozpoczęła się runda (pytanie jest na ekranie)
    ROUND_STARTED = auto()
    # Zmieniła się stawka na jednej z odpowiedzi
    BETS_CHANGED = auto()
    # Zmieniła się liczba pełnych sekund na zegarze
    TIME_CHANGED = auto()
    # Gra została wstrzymana lub wznowiona
    PAUSE_CHANGED = auto()
    # Zakłady zostały zamknięte (ręcznie lub po upływie czasu)
    BETS_LOCKED = auto()
    # Otworzyła się zapadnia pod błędną odpowiedzią
    TRAPDOOR_OPENED = auto()
    # Ujawniono poprawną odpowiedź – runda zakończona
    CORRECT_REVEALED = auto()
    # Gra dobiegła końca
    GAME_FINISHED = auto()
    # Gracz próbował złamać zasady (komunikat ostrzegawczy)
    RULE_VIOLATION = auto()
    # Zmieniono ustawienie
    SETTING_CHANGED = auto()
    # Zmieniła się zawartość bazy pytań
    QUESTIONS_CHANGED = auto()
    # Zmienił się ranking
    SCORES_CHANGED = auto()


@dataclass(frozen=True)
class Event:
    """Pojedyncze zdarzenie: typ + dowolne dane dodatkowe."""

    # Rodzaj zdarzenia
    type: EventType
    # Słownik z danymi (np. indeks odpowiedzi, kwota)
    data: dict[str, Any] = field(default_factory=dict)


# Typ funkcji nasłuchującej – przyjmuje zdarzenie, nic nie zwraca
Listener = Callable[[Event], None]


class Observable:
    """Klasa bazowa dla modeli, które mogą mieć obserwatorów."""

    def __init__(self) -> None:
        # Lista zarejestrowanych funkcji nasłuchujących
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Rejestruje obserwatora i zwraca funkcję wypisującą go."""
        # Dodajemy obserwatora do listy
        self._listeners.append(listener)
        # Zwracamy funkcję, którą widok wywoła przy zamknięciu ekranu
        return lambda: self.unsubscribe(listener)

    def unsubscribe(self, listener: Listener) -> None:
        """Usuwa obserwatora (bezpiecznie, nawet gdy go nie ma)."""
        # Usuwamy tylko jeśli obserwator jest zarejestrowany
        if listener in self._listeners:
            # Właściwe usunięcie z listy
            self._listeners.remove(listener)

    def emit(self, event_type: EventType, **data: Any) -> None:
        """Rozsyła zdarzenie do wszystkich obserwatorów."""
        # Tworzymy obiekt zdarzenia z przekazanymi danymi
        event = Event(event_type, data)
        # Iterujemy po kopii listy, bo obserwator może się w trakcie wypisać
        for listener in list(self._listeners):
            # Powiadamiamy obserwatora
            listener(event)
