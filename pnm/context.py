"""Złożenie aplikacji: tworzy modele i kontrolery, które potem dostaje dowolny widok."""

# dataclass – kontener na zależności
from dataclasses import dataclass
# Path – ścieżki plików
from pathlib import Path

# Ścieżki danych
from pnm.config import DB_PATH, SEED_QUESTIONS_PATH, SETTINGS_PATH
# Kontrolery
from pnm.controller.app_controller import AppController
from pnm.controller.game_controller import GameController
# Modele
from pnm.model.database import Database
from pnm.model.game import GameModel
from pnm.model.repositories import QuestionBank, Ranking
from pnm.model.settings import SettingsModel


@dataclass
class AppContext:
    """Wszystkie modele i kontrolery – przekazywane do widoku."""

    # Ustawienia
    settings: SettingsModel
    # Bank pytań
    bank: QuestionBank
    # Ranking
    ranking: Ranking
    # Model rozgrywki
    game: GameModel
    # Kontroler aplikacji
    app_controller: AppController
    # Kontroler rozgrywki
    game_controller: GameController


def build_context(db_path: Path | str = DB_PATH, settings_path: Path | None = SETTINGS_PATH
                  ) -> AppContext:
    """Tworzy komplet modeli i kontrolerów."""
    # Baza danych (przy pierwszym uruchomieniu zasilana pytaniami z JSON)
    db = Database(db_path, SEED_QUESTIONS_PATH)
    # Ustawienia z pliku JSON
    settings = SettingsModel(settings_path)
    # Bank pytań
    bank = QuestionBank(db)
    # Ranking
    ranking = Ranking(db)
    # Model gry
    game = GameModel()
    # Kontroler rozgrywki
    game_controller = GameController(game, bank, ranking, settings)
    # Kontroler aplikacji
    app_controller = AppController(settings, bank, ranking, game_controller)
    # Kontekst
    return AppContext(settings, bank, ranking, game, app_controller, game_controller)
