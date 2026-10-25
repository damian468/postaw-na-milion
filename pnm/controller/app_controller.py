"""Kontroler aplikacji – nawigacja, menu główne, ustawienia, ranking i bank pytań."""

# dataclass – opis pozycji menu
from dataclasses import dataclass
# Any – wartości ustawień
from typing import Any

# Kontroler rozgrywki
from pnm.controller.game_controller import GameController
# Interfejs widoku
from pnm.controller.view_interface import ScreenId, View
# Obiekt pytania
from pnm.model.entities import Question
# Bank pytań i ranking
from pnm.model.repositories import QuestionBank, Ranking
# Ustawienia
from pnm.model.settings import SettingsModel


@dataclass(frozen=True)
class MenuItem:
    """Pozycja menu głównego (wspólna dla wszystkich widoków)."""

    # Identyfikator akcji
    id: str
    # Tekst pozycji
    label: str
    # Opis wyświetlany pod menu
    description: str


# Pozycje menu głównego w kolejności wyświetlania
MAIN_MENU: tuple[MenuItem, ...] = (
    # Start gry
    MenuItem("new_game", "Nowa gra", "Masz milion złotych. Postaw go mądrze!"),
    # Ranking
    MenuItem("ranking", "Ranking i statystyki", "Najlepsze wyniki, historia gier i statystyki."),
    # Edytor pytań
    MenuItem("bank", "Baza pytań", "Przeglądaj, dodawaj i usuwaj pytania w bazie SQLite."),
    # Ustawienia
    MenuItem("settings", "Ustawienia", "Imię, czas, długość gry, źródło pytań, motyw..."),
    # Zasady
    MenuItem("help", "Jak grać?", "Zasady teleturnieju i sterowanie."),
    # Wyjście
    MenuItem("quit", "Wyjście", "Do zobaczenia w studiu!"),
)


class AppController:
    """Główny kontroler: obsługuje akcje spoza samej rozgrywki."""

    def __init__(self, settings: SettingsModel, bank: QuestionBank, ranking: Ranking,
                 game: GameController) -> None:
        # Ustawienia
        self.settings = settings
        # Bank pytań
        self.bank = bank
        # Ranking
        self.ranking = ranking
        # Kontroler rozgrywki
        self.game = game
        # Widok (ustawiany przez attach_view)
        self._view: View | None = None

    @property
    def menu_items(self) -> tuple[MenuItem, ...]:
        """Pozycje menu głównego."""
        # Stała lista
        return MAIN_MENU

    def attach_view(self, view: View) -> None:
        """Podłącza widok do tego i podrzędnego kontrolera."""
        # Zapamiętanie widoku
        self._view = view
        # Przekazanie do kontrolera gry
        self.game.attach_view(view)

    def start(self) -> None:
        """Wywoływane przez widok po uruchomieniu."""
        # Ustawienie zapisanego motywu
        self._view.apply_theme(self.settings["theme"])
        # Ekran startowy
        self._view.navigate(ScreenId.MAIN_MENU)

    # ---------------------------------------------------------- nawigacja

    def select_menu(self, item_id: str) -> None:
        """Obsługuje wybór pozycji menu głównego."""
        # Mapowanie identyfikatorów na akcje
        actions = {
            # Nowa gra
            "new_game": self.new_game,
            # Ranking
            "ranking": lambda: self._view.navigate(ScreenId.RANKING),
            # Bank pytań
            "bank": lambda: self._view.navigate(ScreenId.QUESTION_BANK),
            # Ustawienia
            "settings": lambda: self._view.navigate(ScreenId.SETTINGS),
            # Pomoc
            "help": lambda: self._view.navigate(ScreenId.HELP),
            # Wyjście
            "quit": self._view.quit,
        }
        # Wykonanie akcji (nieznane identyfikatory są ignorowane)
        actions.get(item_id, lambda: None)()

    def back_to_menu(self) -> None:
        """Powrót do menu głównego."""
        # Nawigacja
        self._view.navigate(ScreenId.MAIN_MENU)

    def new_game(self) -> None:
        """Rozpoczyna nową grę: ładowanie pytań w tle, potem start."""
        # Ekran ładowania
        self._view.navigate(ScreenId.LOADING)
        # Przygotowanie puli w tle i start gry po zakończeniu
        self._view.run_background(self.game.prepare_pool, self.game.start_game)

    # ---------------------------------------------------------- ustawienia

    def cycle_setting(self, key: str, step: int) -> None:
        """Przełącza ustawienie na sąsiednią opcję."""
        # Zmiana w modelu
        self.settings.cycle(key, step)
        # Zmiana motywu działa natychmiast
        if key == "theme":
            # Zastosowanie motywu
            self._view.apply_theme(self.settings["theme"])

    def set_setting(self, key: str, value: Any) -> bool:
        """Ustawia wartość; zwraca False i pokazuje komunikat przy błędzie."""
        # Próba zapisu
        try:
            # Zmiana w modelu
            self.settings.set(key, value)
        # Niepoprawna wartość
        except ValueError as error:
            # Komunikat
            self._view.notify(str(error), "error")
            # Niepowodzenie
            return False
        # Zmiana motywu działa natychmiast
        if key == "theme":
            # Zastosowanie motywu
            self._view.apply_theme(self.settings["theme"])
        # Sukces
        return True

    # ---------------------------------------------------------- bank pytań

    def add_question(self, category: str, text: str, correct: str, wrong: list[str],
                     difficulty: int) -> bool:
        """Dodaje pytanie do bazy; zwraca True przy sukcesie."""
        # Budowa obiektu pytania
        question = Question(text=text, correct=correct, wrong=wrong, category=category,
                            difficulty=difficulty)
        # Walidacja
        problem = self.bank.validate(question)
        # Błąd – komunikat
        if problem:
            # Ostrzeżenie
            self._view.notify(problem, "error")
            # Niepowodzenie
            return False
        # Zapis
        self.bank.add(question)
        # Potwierdzenie
        self._view.notify("Pytanie zapisane w bazie.", "information")
        # Sukces
        return True

    def delete_question(self, question: Question) -> None:
        """Usuwa pytanie z bazy."""
        # Usunięcie
        self.bank.delete(question.id, question.category)
        # Potwierdzenie
        self._view.notify("Pytanie usunięte.", "information")

    # ------------------------------------------------------------- ranking

    def clear_ranking(self) -> None:
        """Czyści ranking."""
        # Usunięcie wyników
        self.ranking.clear()
        # Potwierdzenie
        self._view.notify("Ranking wyczyszczony.", "information")
