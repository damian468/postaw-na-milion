"""Stałe konfiguracyjne i drobne funkcje pomocnicze gry „Postaw na milion”."""

# Path pozwala budować ścieżki niezależnie od systemu operacyjnego
from pathlib import Path

# Katalog główny projektu (dwa poziomy wyżej niż ten plik: pnm/config.py -> projekt)
BASE_DIR = Path(__file__).resolve().parent.parent
# Katalog na dane trwałe (baza, ustawienia, pytania startowe)
DATA_DIR = BASE_DIR / "data"
# Plik bazy danych SQLite z pytaniami i rankingiem
DB_PATH = DATA_DIR / "pnm.db"
# Plik JSON z ustawieniami użytkownika
SETTINGS_PATH = DATA_DIR / "settings.json"
# Plik JSON z pytaniami, którymi zasilana jest pusta baza przy pierwszym uruchomieniu
SEED_QUESTIONS_PATH = DATA_DIR / "questions.json"

# Wartość jednej paczki banknotów w złotych (jak w programie TV)
BUNDLE_VALUE = 25_000
# Liczba paczek na start gry (40 x 25 000 zł = 1 000 000 zł)
START_BUNDLES = 40

# Układ rund: liczba odpowiedzi w kolejnych pytaniach dla danej długości gry
ANSWER_LAYOUTS = {
    # Krótka gra: 5 pytań
    5: (4, 4, 3, 3, 2),
    # Pełna gra: 8 pytań, jak w oryginalnym formacie
    8: (4, 4, 4, 4, 3, 3, 3, 2),
}

# Litery oznaczające odpowiedzi (A, B, C, D)
ANSWER_LETTERS = "ABCD"


def format_money(amount: int) -> str:
    """Zwraca kwotę w formacie „1 000 000 zł”."""
    # Formatowanie z przecinkami tysięcy, potem zamiana przecinków na spacje
    return f"{amount:,}".replace(",", " ") + " zł"


def bundles_to_money(bundles: int) -> int:
    """Przelicza liczbę paczek na kwotę w złotych."""
    # Każda paczka ma stałą wartość BUNDLE_VALUE
    return bundles * BUNDLE_VALUE


def target_difficulty(round_index: int, total_rounds: int) -> int:
    """Zwraca docelową trudność pytania (1-3) dla danej rundy."""
    # Ułamek postępu gry: 0.0 dla pierwszej rundy, 1.0 dla ostatniej
    progress = round_index / max(1, total_rounds - 1)
    # Pierwsze ~40% gry to pytania łatwe
    if progress < 0.4:
        # Zwracamy poziom łatwy
        return 1
    # Kolejne rundy do ~80% gry to pytania średnie
    if progress < 0.8:
        # Zwracamy poziom średni
        return 2
    # Końcówka gry to pytania trudne
    return 3
