"""Ekrany widoku tekstowego i ich mapowanie na identyfikatory używane przez kontroler."""

# Identyfikatory ekranów
from pnm.controller.view_interface import ScreenId
# Ekrany
from pnm.view.tui.screens.bank import QuestionBankScreen
from pnm.view.tui.screens.game import GameScreen
from pnm.view.tui.screens.help import HelpScreen
from pnm.view.tui.screens.loading import LoadingScreen
from pnm.view.tui.screens.menu import MenuScreen
from pnm.view.tui.screens.ranking import RankingScreen
from pnm.view.tui.screens.settings import SettingsScreen
from pnm.view.tui.screens.summary import SummaryScreen

# Mapa: identyfikator ekranu -> klasa ekranu
SCREENS = {
    # Menu główne
    ScreenId.MAIN_MENU: MenuScreen,
    # Ustawienia
    ScreenId.SETTINGS: SettingsScreen,
    # Pomoc
    ScreenId.HELP: HelpScreen,
    # Ranking
    ScreenId.RANKING: RankingScreen,
    # Baza pytań
    ScreenId.QUESTION_BANK: QuestionBankScreen,
    # Ładowanie
    ScreenId.LOADING: LoadingScreen,
    # Gra
    ScreenId.GAME: GameScreen,
    # Podsumowanie
    ScreenId.SUMMARY: SummaryScreen,
}
