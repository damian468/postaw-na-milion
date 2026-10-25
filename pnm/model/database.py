"""Warstwa trwałego składowania danych – baza SQLite (pytania i ranking)."""

# json – odczyt pliku z pytaniami startowymi
import json
# sqlite3 – wbudowana w Pythona baza danych
import sqlite3
# threading – blokada, bo pytania mogą być czytane z wątku w tle
import threading
# Path – ścieżki plików
from pathlib import Path

# Obiekty danych
from pnm.model.entities import GameStats, Question, ScoreEntry

# Skrypt tworzący tabele (wykonywany przy każdym starcie – IF NOT EXISTS)
SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    correct     TEXT    NOT NULL,
    wrong1      TEXT    NOT NULL,
    wrong2      TEXT    NOT NULL,
    wrong3      TEXT    NOT NULL,
    difficulty  INTEGER NOT NULL DEFAULT 1,
    source      TEXT    NOT NULL DEFAULT 'local'
);
CREATE TABLE IF NOT EXISTS scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player      TEXT    NOT NULL,
    amount      INTEGER NOT NULL,
    answered    INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    time_limit  INTEGER NOT NULL,
    source      TEXT    NOT NULL,
    played_at   TEXT    NOT NULL
);
"""


class Database:
    """Dostęp do bazy SQLite – jedyne miejsce w kodzie, które zna SQL."""

    def __init__(self, path: Path | str, seed_path: Path | None = None) -> None:
        # Ścieżka ":memory:" oznacza bazę w pamięci (testy)
        if str(path) != ":memory:":
            # Tworzymy katalog na plik bazy
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Połączenie dostępne z wielu wątków (chronimy je blokadą)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        # Wiersze dostępne po nazwach kolumn
        self._conn.row_factory = sqlite3.Row
        # Blokada chroniąca połączenie
        self._lock = threading.Lock()
        # Tworzenie tabel
        with self._lock:
            # Wykonanie skryptu tworzącego
            self._conn.executescript(SCHEMA)
        # Zasilenie pustej bazy pytaniami startowymi
        if seed_path is not None:
            # Wczytanie pytań z pliku JSON
            self._seed_if_empty(seed_path)

    # ------------------------------------------------------------ pomocnicze

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Wykonuje zapytanie SELECT i zwraca wszystkie wiersze."""
        # Wyłączny dostęp do połączenia
        with self._lock:
            # Wykonanie i pobranie wyników
            return self._conn.execute(sql, params).fetchall()

    def _execute(self, sql: str, params: tuple = ()) -> int:
        """Wykonuje zapytanie modyfikujące i zatwierdza transakcję. Zwraca id wiersza."""
        # Wyłączny dostęp do połączenia
        with self._lock:
            # Wykonanie zapytania
            cursor = self._conn.execute(sql, params)
            # Zatwierdzenie zmian
            self._conn.commit()
            # Identyfikator ostatnio wstawionego wiersza
            return cursor.lastrowid

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> Question:
        """Zamienia wiersz tabeli na obiekt Question."""
        # Budowa obiektu z kolumn
        return Question(
            # Treść pytania
            text=row["text"],
            # Poprawna odpowiedź
            correct=row["correct"],
            # Trzy błędne odpowiedzi
            wrong=[row["wrong1"], row["wrong2"], row["wrong3"]],
            # Kategoria
            category=row["category"],
            # Trudność
            difficulty=row["difficulty"],
            # Źródło
            source=row["source"],
            # Identyfikator
            id=row["id"],
        )

    @staticmethod
    def _row_to_score(row: sqlite3.Row) -> ScoreEntry:
        """Zamienia wiersz tabeli na obiekt ScoreEntry."""
        # Budowa obiektu z kolumn (nazwy kolumn = nazwy pól)
        return ScoreEntry(**{key: row[key] for key in row.keys()})

    def _seed_if_empty(self, seed_path: Path) -> None:
        """Wczytuje pytania startowe, jeśli tabela pytań jest pusta."""
        # Sprawdzamy, czy są już jakieś pytania
        if self.question_count() > 0 or not seed_path.exists():
            # Nie trzeba niczego wczytywać
            return
        # Odczyt pliku JSON
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        # Plik ma strukturę {kategoria: [pytania]}
        for category, questions in data.items():
            # Każde pytanie z kategorii
            for item in questions:
                # Dodanie pytania do bazy
                self.add_question(Question(
                    # Treść
                    text=item["q"],
                    # Poprawna odpowiedź
                    correct=item["a"],
                    # Błędne odpowiedzi
                    wrong=item["w"],
                    # Kategoria z klucza słownika
                    category=category,
                    # Trudność (domyślnie 1)
                    difficulty=item.get("d", 1),
                ))

    # --------------------------------------------------------------- pytania

    def question_count(self) -> int:
        """Liczba pytań w bazie."""
        # Zliczenie wierszy
        return self._query("SELECT COUNT(*) AS n FROM questions")[0]["n"]

    def all_questions(self) -> list[Question]:
        """Wszystkie pytania z bazy."""
        # Pobranie i konwersja wierszy
        return [self._row_to_question(r) for r in self._query("SELECT * FROM questions")]

    def categories(self) -> list[tuple[str, int]]:
        """Lista kategorii z liczbą pytań, alfabetycznie."""
        # Grupowanie po kategorii
        rows = self._query("SELECT category, COUNT(*) AS n FROM questions "
                           "GROUP BY category ORDER BY category")
        # Lista krotek (nazwa, liczba)
        return [(row["category"], row["n"]) for row in rows]

    def questions_in(self, category: str) -> list[Question]:
        """Pytania z jednej kategorii."""
        # Filtrowanie po kategorii
        rows = self._query("SELECT * FROM questions WHERE category = ? ORDER BY difficulty, id",
                           (category,))
        # Konwersja wierszy
        return [self._row_to_question(r) for r in rows]

    def add_question(self, question: Question) -> int:
        """Dodaje pytanie i zwraca jego identyfikator."""
        # Uzupełniamy listę błędnych odpowiedzi do trzech elementów
        wrong = (list(question.wrong) + ["", "", ""])[:3]
        # Wstawienie wiersza
        return self._execute(
            # Zapytanie z parametrami (ochrona przed SQL injection)
            "INSERT INTO questions (category, text, correct, wrong1, wrong2, wrong3, "
            "difficulty, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            # Wartości parametrów
            (question.category, question.text, question.correct, *wrong,
             question.difficulty, question.source),
        )

    def delete_question(self, question_id: int) -> None:
        """Usuwa pytanie o podanym identyfikatorze."""
        # Usunięcie wiersza
        self._execute("DELETE FROM questions WHERE id = ?", (question_id,))

    # --------------------------------------------------------------- ranking

    def add_score(self, entry: ScoreEntry) -> int:
        """Zapisuje wynik gry i zwraca jego identyfikator."""
        # Wstawienie wiersza
        return self._execute(
            # Zapytanie z parametrami
            "INSERT INTO scores (player, amount, answered, total, time_limit, source, "
            "played_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            # Wartości parametrów
            (entry.player, entry.amount, entry.answered, entry.total, entry.time_limit,
             entry.source, entry.played_at),
        )

    def rank_of(self, score_id: int) -> int:
        """Miejsce wyniku w rankingu (1 = najlepszy)."""
        # Kwota i data wyniku
        row = self._query("SELECT amount, played_at FROM scores WHERE id = ?", (score_id,))[0]
        # Liczba wyników lepszych (wyższa kwota lub ta sama, ale wcześniej)
        better = self._query(
            # Zapytanie zliczające
            "SELECT COUNT(*) AS n FROM scores WHERE amount > ? OR "
            "(amount = ? AND played_at < ?)",
            # Parametry
            (row["amount"], row["amount"], row["played_at"]),
        )[0]["n"]
        # Miejsce = liczba lepszych + 1
        return better + 1

    def top_scores(self, limit: int = 10) -> list[ScoreEntry]:
        """Najlepsze wyniki."""
        # Sortowanie malejąco po kwocie, przy remisie – wcześniejsza gra wyżej
        rows = self._query("SELECT * FROM scores ORDER BY amount DESC, played_at ASC LIMIT ?",
                           (limit,))
        # Konwersja wierszy
        return [self._row_to_score(r) for r in rows]

    def recent_scores(self, limit: int = 20) -> list[ScoreEntry]:
        """Ostatnio rozegrane gry."""
        # Sortowanie malejąco po dacie
        rows = self._query("SELECT * FROM scores ORDER BY played_at DESC LIMIT ?", (limit,))
        # Konwersja wierszy
        return [self._row_to_score(r) for r in rows]

    def stats(self) -> GameStats:
        """Statystyki zbiorcze ze wszystkich gier."""
        # Agregaty w jednym zapytaniu
        row = self._query(
            # Liczba gier, wygrane, maksimum, średnia, suma
            "SELECT COUNT(*) AS games, SUM(amount > 0) AS wins, MAX(amount) AS best, "
            "AVG(amount) AS average, SUM(amount) AS total FROM scores"
        )[0]
        # Najczęściej grający gracze
        players = self._query("SELECT player, COUNT(*) AS n FROM scores GROUP BY player "
                              "ORDER BY n DESC, player LIMIT 5")
        # Budowa obiektu statystyk (NULL z pustej tabeli zamieniamy na 0)
        return GameStats(
            # Liczba gier
            games=row["games"] or 0,
            # Liczba wygranych
            wins=row["wins"] or 0,
            # Najlepszy wynik
            best=row["best"] or 0,
            # Średnia
            average=row["average"] or 0.0,
            # Suma
            total=row["total"] or 0,
            # Lista graczy
            top_players=[(p["player"], p["n"]) for p in players],
        )

    def clear_scores(self) -> None:
        """Usuwa cały ranking."""
        # Usunięcie wszystkich wierszy
        self._execute("DELETE FROM scores")

    def close(self) -> None:
        """Zamyka połączenie z bazą."""
        # Zamknięcie pod blokadą
        with self._lock:
            # Właściwe zamknięcie
            self._conn.close()
