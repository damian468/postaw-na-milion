"""Abstrakcyjny interfejs widoku – kontrakt między kontrolerem a dowolnym UI.

Kontroler zna wyłącznie ten interfejs. Widok tekstowy (Textual) i graficzny
(tkinter) implementują go na swój sposób, więc zamiana interfejsu nie wymaga
żadnych zmian w modelu ani w kontrolerach.
"""

# ABC – klasy abstrakcyjne
from abc import ABC, abstractmethod
# Enum – identyfikatory ekranów
from enum import Enum, auto
# Typy funkcji zwrotnych
from typing import Any, Callable


class ScreenId(Enum):
    """Ekrany aplikacji, między którymi przełącza kontroler."""

    # Menu główne
    MAIN_MENU = auto()
    # Ustawienia
    SETTINGS = auto()
    # Zasady gry
    HELP = auto()
    # Ranking i statystyki
    RANKING = auto()
    # Edytor bazy pytań
    QUESTION_BANK = auto()
    # Ekran ładowania pytań
    LOADING = auto()
    # Rozgrywka
    GAME = auto()
    # Podsumowanie gry
    SUMMARY = auto()


class View(ABC):
    """Interfejs, który musi spełnić każdy widok aplikacji."""

    @abstractmethod
    def run(self) -> None:
        """Uruchamia pętlę zdarzeń interfejsu (blokuje do zamknięcia)."""

    @abstractmethod
    def navigate(self, screen: ScreenId) -> None:
        """Pokazuje wskazany ekran."""

    @abstractmethod
    def notify(self, message: str, severity: str = "information") -> None:
        """Pokazuje krótki komunikat (severity: information / warning / error)."""

    @abstractmethod
    def run_background(self, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Wykonuje `task` w tle, a jego wynik przekazuje do `on_done` w wątku UI."""

    @abstractmethod
    def apply_theme(self, theme: str) -> None:
        """Zmienia motyw kolorystyczny."""

    @abstractmethod
    def bell(self) -> None:
        """Wydaje krótki sygnał dźwiękowy."""

    @abstractmethod
    def quit(self) -> None:
        """Zamyka aplikację."""
