"""Test widoku tekstowego – automatyczny „gracz” steruje grą klawiszami (Textual Pilot).

Uruchomienie:  python -m unittest tests.test_tui
"""

# asyncio – testy Textual są asynchroniczne
import asyncio
# os – opcjonalny katalog na zrzuty ekranu
import os
# unittest – framework testowy
import unittest

# Złożenie aplikacji
from pnm.context import build_context
# Fazy gry
from pnm.model.game import GamePhase
# Widok tekstowy
from pnm.view.tui.app import TuiView

# Katalog na zrzuty ekranu SVG (ustaw PNM_SHOTS, by je zapisać)
SHOTS = os.environ.get("PNM_SHOTS")


async def shot(app, name: str) -> None:
    """Zapisuje zrzut ekranu, jeśli ustawiono katalog."""
    # Tylko gdy podano katalog
    if SHOTS:
        # Zapis SVG
        app.save_screenshot(f"{name}.svg", SHOTS)


async def play_game(test: unittest.TestCase) -> None:
    """Rozgrywa pełną grę klawiaturą."""
    # Kontekst z bazą w pamięci i bez pliku ustawień
    ctx = build_context(":memory:", None)
    # Szybkie animacje
    ctx.settings.set("animation", "fast")
    # Widok tekstowy
    view = TuiView(ctx)
    # Podłączenie do kontrolera
    ctx.app_controller.attach_view(view)
    # Uruchomienie w trybie testowym (terminal 130x40)
    async with view.app.run_test(size=(130, 40)) as pilot:
        # Chwila na animacje menu
        await pilot.pause(0.5)
        # Zrzut menu
        await shot(view.app, "01_menu")
        # Panel diagnostyczny
        await pilot.press("f2")
        # Enter na „Nowa gra”
        await pilot.press("enter")
        # Czekamy na przygotowanie pytań
        for _ in range(50):
            # Krótka pauza
            await pilot.pause(0.05)
            # Gra rozpoczęta
            if ctx.game.phase is GamePhase.CATEGORY:
                # Koniec czekania
                break
        # Gra w fazie wyboru kategorii
        test.assertIs(ctx.game.phase, GamePhase.CATEGORY)
        # Zrzut wyboru kategorii
        await pilot.pause(0.3)
        # Zapis
        await shot(view.app, "02_category")
        # Numer rundy (do zrzutów)
        round_no = 0
        # Rozgrywka do końca
        while ctx.game.phase is not GamePhase.FINISHED:
            # Zmiana kategorii strzałką i zatwierdzenie
            await pilot.press("right", "enter")
            # Faza stawiania
            test.assertIs(ctx.game.phase, GamePhase.BETTING)
            # Indeks poprawnej odpowiedzi
            correct = ctx.game.current.correct_index
            # Przejście do poprawnej kolumny klawiszem cyfry
            await pilot.press(str(correct + 1))
            # 10 paczek strzałką w górę (PgUp)
            await pilot.press("pageup")
            # Reszta klawiszem A
            await pilot.press("a")
            # Wszystko rozłożone
            test.assertEqual(ctx.game.unplaced, 0)
            # Próba złamania zasady – dokładamy na inną kolumnę (pusta pula)
            await pilot.press(str((correct + 1) % ctx.game.answers_count + 1), "up")
            # Zrzut planszy w pierwszej rundzie
            if round_no == 0:
                # Chwila na odświeżenie
                await pilot.pause(0.2)
                # Zapis
                await shot(view.app, "03_board")
            # Zamknięcie zakładów
            await pilot.press("enter")
            # Odsłanianie
            for _ in range(80):
                # Pauza
                await pilot.pause(0.05)
                # Zrzut w trakcie animacji w pierwszej rundzie
                if round_no == 0 and _ == 22:
                    # Zapis
                    await shot(view.app, "04_reveal")
                # Koniec rundy
                if ctx.game.phase is GamePhase.ROUND_OVER:
                    # Koniec czekania
                    break
            # Runda zakończona
            test.assertIs(ctx.game.phase, GamePhase.ROUND_OVER)
            # Zrzut po rundzie
            if round_no == 0:
                # Chwila na animację
                await pilot.pause(0.6)
                # Zapis
                await shot(view.app, "05_round_over")
            # Dalej
            await pilot.press("enter")
            # Kolejna runda
            round_no += 1
        # Milion wygrany
        test.assertEqual(ctx.game.money, 1_000_000)
        # Chwila na ekran podsumowania
        await pilot.pause(0.5)
        # Zrzut podsumowania
        await shot(view.app, "06_summary")
        # Powrót do menu (strzałka w dół i Enter)
        await pilot.press("down", "enter")
        # Chwila
        await pilot.pause(0.2)
        # Wejście w ranking: 2. pozycja menu
        await pilot.press("down", "enter")
        # Chwila
        await pilot.pause(0.3)
        # Zrzut rankingu
        await shot(view.app, "07_ranking")
        # Powrót
        await pilot.press("escape")
        # Baza pytań: 3. pozycja
        await pilot.press("down", "down", "enter")
        # Chwila
        await pilot.pause(0.3)
        # Zrzut bazy pytań
        await shot(view.app, "08_bank")
        # Formularz nowego pytania
        await pilot.press("n")
        # Chwila
        await pilot.pause(0.2)
        # Zrzut formularza
        await shot(view.app, "09_form")
        # Anulowanie i powrót
        await pilot.press("escape", "escape")
        # Ustawienia: 4. pozycja
        await pilot.press("down", "down", "down", "enter")
        # Zmiana motywu (5. wiersz) strzałką w prawo
        await pilot.press("down", "down", "down", "down", "right")
        # Motyw zmieniony
        test.assertEqual(ctx.settings["theme"], "neon")
        # Chwila
        await pilot.pause(0.3)
        # Zrzut ustawień
        await shot(view.app, "10_settings")
        # Powrót
        await pilot.press("escape")
        # Pomoc: 5. pozycja
        await pilot.press("down", "down", "down", "down", "enter", "right")
        # Chwila
        await pilot.pause(0.2)
        # Zrzut pomocy
        await shot(view.app, "11_help")


class TuiTests(unittest.TestCase):
    """Testy widoku tekstowego."""

    def test_full_game_with_keyboard(self) -> None:
        # Uruchomienie scenariusza
        asyncio.run(play_game(self))


# Uruchomienie bezpośrednio z pliku
if __name__ == "__main__":
    # Start frameworka
    unittest.main()
