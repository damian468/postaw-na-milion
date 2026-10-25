"""Testy modelu i kontrolera – uruchamiane bez żadnego interfejsu użytkownika.

Uruchomienie:  python -m unittest discover tests
"""

# random – deterministyczny generator dla testów
import random
# unittest – wbudowany framework testowy
import unittest

# Stałe gry
from pnm.config import ANSWER_LAYOUTS, SEED_QUESTIONS_PATH, format_money
# Kontrolery
from pnm.controller.app_controller import AppController
from pnm.controller.game_controller import GameController
# Interfejs widoku
from pnm.controller.view_interface import ScreenId, View
# Modele
from pnm.model.database import Database
from pnm.model.entities import Question, RoundQuestion
from pnm.model.game import GameModel, GamePhase
from pnm.model.observable import EventType
from pnm.model.online import OnlineError
from pnm.model.repositories import QuestionBank, Ranking
from pnm.model.settings import SettingsModel


class FakeView(View):
    """Atrapa widoku – zapisuje wywołania zamiast rysować."""

    def __init__(self) -> None:
        # Historia nawigacji
        self.screens: list[ScreenId] = []
        # Historia komunikatów
        self.messages: list[tuple[str, str]] = []

    def run(self) -> None:
        # Nic do uruchomienia
        pass

    def navigate(self, screen: ScreenId) -> None:
        # Zapis ekranu
        self.screens.append(screen)

    def notify(self, message: str, severity: str = "information") -> None:
        # Zapis komunikatu
        self.messages.append((message, severity))

    def run_background(self, task, on_done) -> None:
        # W testach wykonujemy synchronicznie
        on_done(task())

    def apply_theme(self, theme: str) -> None:
        # Brak motywów w testach
        pass

    def bell(self) -> None:
        # Cisza
        pass

    def quit(self) -> None:
        # Brak pętli do zamknięcia
        pass


class OfflineClient:
    """Atrapa klienta OpenTDB symulująca brak Internetu."""

    def fetch(self, amount: int = 50):
        # Zawsze błąd sieci
        raise OnlineError("Brak sieci")


def make_round(answers: int = 4, correct: int = 0) -> RoundQuestion:
    """Tworzy pytanie rundy o zadanej liczbie odpowiedzi."""
    # Odpowiedzi A, B, C, D...
    texts = [f"odp{i}" for i in range(answers)]
    # Pytanie bazowe
    question = Question("Pytanie?", texts[correct], [t for t in texts if t != texts[correct]], "Test")
    # Pytanie rundy
    return RoundQuestion(question, texts, correct)


class GameModelTests(unittest.TestCase):
    """Zasady gry."""

    def setUp(self) -> None:
        # Nowy model z ziarnem losowości
        self.game = GameModel(random.Random(1))
        # Start gry 8-rundowej z limitem 60 s
        self.game.start("Test", ANSWER_LAYOUTS[8], 60)
        # Pierwsza runda: 4 odpowiedzi, poprawna B
        self.game.start_round(make_round(4, correct=1))

    def test_start_money(self) -> None:
        # Na start milion złotych
        self.assertEqual(self.game.money, 1_000_000)
        # Wszystko w puli
        self.assertEqual(self.game.unplaced, 40)

    def test_one_trapdoor_must_stay_empty(self) -> None:
        # Stawiamy po paczce na trzy odpowiedzi
        for answer in range(3):
            # Dokładamy paczkę
            self.assertEqual(self.game.add_bet(answer), 1)
        # Czwarta odpowiedź musi zostać pusta
        self.assertEqual(self.game.add_bet(3), 0)

    def test_cannot_lock_with_unplaced_money(self) -> None:
        # Część pieniędzy na A
        self.game.add_bet(0, 10)
        # Zamknięcie odrzucone
        self.assertFalse(self.game.lock_bets())
        # Wciąż faza stawiania
        self.assertIs(self.game.phase, GamePhase.BETTING)

    def test_reveal_keeps_money_on_correct(self) -> None:
        # 30 paczek na poprawną B
        self.game.add_bet(1, 30)
        # 10 paczek na błędną A
        self.game.add_bet(0, 10)
        # Zamknięcie
        self.assertTrue(self.game.lock_bets())
        # Otwieramy wszystkie błędne
        while self.game.open_next_trapdoor() is not None:
            # Kolejna zapadnia
            pass
        # Ujawnienie poprawnej
        self.game.reveal_correct()
        # Zostało 30 paczek
        self.assertEqual(self.game.money, 750_000)
        # Historia zawiera rundę
        self.assertEqual(self.game.history[0].bundles_after, 30)

    def test_timeout_loses_unplaced(self) -> None:
        # Tylko 4 paczki postawione
        self.game.add_bet(1, 4)
        # Upływ całego czasu
        self.assertTrue(self.game.tick(61))
        # Wymuszone zamknięcie
        self.game.lock_bets(forced=True)
        # 36 paczek przepadło
        self.assertEqual(self.game.lost_unplaced, 36)
        # Zostały tylko postawione
        self.assertEqual(self.game.bundles, 4)

    def test_time_event_once_per_second(self) -> None:
        # Licznik zdarzeń zegara
        events = []
        # Subskrypcja
        self.game.subscribe(lambda e: events.append(e) if e.type is EventType.TIME_CHANGED else None)
        # 10 kroków po 0.1 s = 1 sekunda
        for _ in range(10):
            # Krok zegara
            self.game.tick(0.1)
        # Dokładnie jedno zdarzenie (odświeżenie zegara raz na sekundę)
        self.assertEqual(len(events), 1)


class ControllerTests(unittest.TestCase):
    """Pełna gra przez kontroler z atrapą widoku."""

    def setUp(self) -> None:
        # Baza w pamięci zasilona pytaniami startowymi
        db = Database(":memory:", SEED_QUESTIONS_PATH)
        # Ustawienia bez pliku
        self.settings = SettingsModel(None)
        # Modele
        self.bank, self.ranking, self.game = QuestionBank(db), Ranking(db), GameModel()
        # Kontroler gry z atrapą klienta offline
        self.gc = GameController(self.game, self.bank, self.ranking, self.settings, OfflineClient())
        # Kontroler aplikacji
        self.app = AppController(self.settings, self.bank, self.ranking, self.gc)
        # Atrapa widoku
        self.view = FakeView()
        # Podłączenie widoku
        self.app.attach_view(self.view)

    def test_seed_loaded(self) -> None:
        # Baza ma ponad 100 pytań
        self.assertGreater(self.bank.count(), 100)

    def test_full_game_all_correct(self) -> None:
        # Animacje wyłączone – szybkie odsłanianie
        self.settings.set("animation", "off")
        # Nowa gra z menu
        self.app.select_menu("new_game")
        # Widok przeszedł do gry
        self.assertEqual(self.view.screens[-2:], [ScreenId.LOADING, ScreenId.GAME])
        # Rozgrywamy wszystkie rundy
        while self.game.phase is not GamePhase.FINISHED:
            # Wybór pierwszej kategorii
            self.gc.choose_category(0)
            # Wszystko na poprawną odpowiedź
            self.gc.all_in(self.game.current.correct_index)
            # Zamknięcie zakładów
            self.gc.lock()
            # Odsłanianie do końca rundy
            while self.game.phase is GamePhase.REVEAL:
                # Krok zegara
                self.gc.tick(0.1)
            # Dalej
            self.gc.continue_game()
        # Wygrany milion
        self.assertEqual(self.game.money, 1_000_000)
        # Ekran podsumowania
        self.assertEqual(self.view.screens[-1], ScreenId.SUMMARY)
        # Pierwsze miejsce w rankingu
        self.assertEqual(self.gc.last_rank, 1)

    def test_online_fallback(self) -> None:
        # Źródło internetowe
        self.settings.set("question_source", "online")
        # Przygotowanie puli (bez sieci)
        note = self.gc.prepare_pool()
        # Komunikat o braku sieci
        self.assertIn("lokalnej bazy", note)

    def test_add_question_validation(self) -> None:
        # Puste odpowiedzi – odrzucone
        self.assertFalse(self.app.add_question("X", "Pytanie?", "a", ["", "c", "d"], 1))
        # Poprawne pytanie – zapisane
        self.assertTrue(self.app.add_question("X", "Pytanie?", "a", ["b", "c", "d"], 1))

    def test_format_money(self) -> None:
        # Format kwoty
        self.assertEqual(format_money(1_000_000), "1 000 000 zł")


# Uruchomienie testów bezpośrednio z pliku
if __name__ == "__main__":
    # Start frameworka
    unittest.main()
