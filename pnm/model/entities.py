"""Proste obiekty danych (encje) używane w całej aplikacji."""

# dataclass generuje konstruktor, porównania i repr
from dataclasses import dataclass, field


@dataclass
class Question:
    """Pytanie w bazie: jedna poprawna i trzy błędne odpowiedzi."""

    # Treść pytania
    text: str
    # Poprawna odpowiedź
    correct: str
    # Lista błędnych odpowiedzi (zwykle 3)
    wrong: list[str]
    # Nazwa kategorii, np. „Historia”
    category: str
    # Trudność: 1 – łatwe, 2 – średnie, 3 – trudne
    difficulty: int = 1
    # Pochodzenie pytania: „local” (baza) lub „online” (OpenTDB)
    source: str = "local"
    # Identyfikator w bazie (None dla pytań spoza bazy)
    id: int | None = None


@dataclass
class RoundQuestion:
    """Pytanie przygotowane do konkretnej rundy (wybrane i przetasowane odpowiedzi)."""

    # Oryginalne pytanie z bazy
    question: Question
    # Odpowiedzi w kolejności wyświetlania (2, 3 lub 4)
    answers: list[str]
    # Indeks poprawnej odpowiedzi na liście answers
    correct_index: int

    @property
    def text(self) -> str:
        """Treść pytania."""
        # Delegujemy do oryginalnego pytania
        return self.question.text

    @property
    def category(self) -> str:
        """Kategoria pytania."""
        # Delegujemy do oryginalnego pytania
        return self.question.category


@dataclass
class RoundRecord:
    """Zapis przebiegu jednej rundy – używany na ekranie podsumowania."""

    # Numer rundy liczony od 1
    number: int
    # Kategoria pytania
    category: str
    # Treść pytania
    question: str
    # Odpowiedzi w kolejności wyświetlania
    answers: list[str]
    # Indeks poprawnej odpowiedzi
    correct_index: int
    # Liczba paczek postawionych na każdej odpowiedzi
    bets: list[int]
    # Liczba paczek przed rundą
    bundles_before: int
    # Liczba paczek po rundzie
    bundles_after: int
    # Paczki utracone, bo nie zostały postawione przed końcem czasu
    lost_unplaced: int = 0


@dataclass
class ScoreEntry:
    """Wpis w rankingu (jedna zakończona gra)."""

    # Imię gracza
    player: str
    # Wygrana kwota w złotych
    amount: int
    # Liczba pytań, po których gracz miał jeszcze pieniądze
    answered: int
    # Łączna liczba pytań w grze
    total: int
    # Limit czasu na pytanie (0 = bez limitu)
    time_limit: int
    # Źródło pytań użyte w grze
    source: str
    # Data i godzina rozegrania w formacie ISO
    played_at: str
    # Identyfikator w bazie
    id: int | None = None


@dataclass
class GameStats:
    """Zbiorcze statystyki wszystkich rozegranych gier."""

    # Liczba rozegranych gier
    games: int = 0
    # Liczba gier zakończonych z niezerową wygraną
    wins: int = 0
    # Najwyższa wygrana
    best: int = 0
    # Średnia wygrana
    average: float = 0.0
    # Suma wszystkich wygranych
    total: int = 0
    # Najczęściej grający gracze: lista (imię, liczba gier)
    top_players: list[tuple[str, int]] = field(default_factory=list)
