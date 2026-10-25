"""Obserwowalne modele nad bazą danych: bank pytań i ranking.

Widoki subskrybują te modele – po dodaniu pytania lub wyniku odświeżają się
tylko tabele, których to dotyczy.
"""

# datetime – znacznik czasu zapisu wyniku
from datetime import datetime

# Dostęp do bazy danych
from pnm.model.database import Database
# Obiekty danych
from pnm.model.entities import GameStats, Question, ScoreEntry
# Mechanizm powiadamiania obserwatorów
from pnm.model.observable import EventType, Observable

# Maksymalna długość treści pytania
MAX_QUESTION_LENGTH = 200
# Maksymalna długość odpowiedzi
MAX_ANSWER_LENGTH = 60


class QuestionBank(Observable):
    """Bank pytań: odczyt, walidacja i dodawanie/usuwanie pytań."""

    def __init__(self, db: Database) -> None:
        # Inicjalizacja mechanizmu obserwatorów
        super().__init__()
        # Baza danych
        self._db = db

    def all(self) -> list[Question]:
        """Wszystkie pytania."""
        # Delegacja do bazy
        return self._db.all_questions()

    def count(self) -> int:
        """Liczba pytań."""
        # Delegacja do bazy
        return self._db.question_count()

    def categories(self) -> list[tuple[str, int]]:
        """Kategorie z liczbą pytań."""
        # Delegacja do bazy
        return self._db.categories()

    def in_category(self, category: str) -> list[Question]:
        """Pytania z kategorii."""
        # Delegacja do bazy
        return self._db.questions_in(category)

    @staticmethod
    def validate(question: Question) -> str | None:
        """Zwraca opis błędu w pytaniu lub None, gdy pytanie jest poprawne."""
        # Kategoria jest wymagana
        if not question.category.strip():
            # Komunikat błędu
            return "Podaj kategorię."
        # Treść jest wymagana
        if not question.text.strip():
            # Komunikat błędu
            return "Podaj treść pytania."
        # Treść nie może być za długa
        if len(question.text) > MAX_QUESTION_LENGTH:
            # Komunikat błędu
            return f"Pytanie może mieć najwyżej {MAX_QUESTION_LENGTH} znaków."
        # Wszystkie odpowiedzi razem
        answers = [question.correct, *question.wrong]
        # Wymagane cztery niepuste odpowiedzi
        if len(answers) != 4 or any(not a.strip() for a in answers):
            # Komunikat błędu
            return "Podaj poprawną odpowiedź i trzy błędne."
        # Odpowiedzi nie mogą być za długie
        if any(len(a) > MAX_ANSWER_LENGTH for a in answers):
            # Komunikat błędu
            return f"Odpowiedź może mieć najwyżej {MAX_ANSWER_LENGTH} znaków."
        # Odpowiedzi nie mogą się powtarzać (bez względu na wielkość liter)
        if len({a.strip().lower() for a in answers}) != 4:
            # Komunikat błędu
            return "Odpowiedzi muszą być różne."
        # Trudność 1–3
        if question.difficulty not in (1, 2, 3):
            # Komunikat błędu
            return "Trudność musi wynosić 1, 2 lub 3."
        # Brak błędów
        return None

    def add(self, question: Question) -> int:
        """Dodaje poprawne pytanie (wcześniej należy wywołać validate)."""
        # Przycinamy białe znaki we wszystkich polach
        question = Question(
            # Treść
            text=question.text.strip(),
            # Poprawna odpowiedź
            correct=question.correct.strip(),
            # Błędne odpowiedzi
            wrong=[w.strip() for w in question.wrong],
            # Kategoria
            category=question.category.strip(),
            # Trudność
            difficulty=question.difficulty,
            # Pytania dodane przez użytkownika oznaczamy osobno
            source="user",
        )
        # Zapis w bazie
        question_id = self._db.add_question(question)
        # Powiadomienie widoków
        self.emit(EventType.QUESTIONS_CHANGED, category=question.category)
        # Zwracamy identyfikator
        return question_id

    def delete(self, question_id: int, category: str) -> None:
        """Usuwa pytanie."""
        # Usunięcie z bazy
        self._db.delete_question(question_id)
        # Powiadomienie widoków
        self.emit(EventType.QUESTIONS_CHANGED, category=category)


class Ranking(Observable):
    """Ranking graczy i statystyki."""

    def __init__(self, db: Database) -> None:
        # Inicjalizacja mechanizmu obserwatorów
        super().__init__()
        # Baza danych
        self._db = db

    def add(self, player: str, amount: int, answered: int, total: int, time_limit: int,
            source: str) -> int:
        """Zapisuje wynik i zwraca miejsce w rankingu."""
        # Budowa wpisu z bieżącym czasem
        entry = ScoreEntry(player=player, amount=amount, answered=answered, total=total,
                           time_limit=time_limit, source=source,
                           played_at=datetime.now().isoformat(timespec="seconds"))
        # Zapis w bazie
        score_id = self._db.add_score(entry)
        # Powiadomienie widoków
        self.emit(EventType.SCORES_CHANGED)
        # Miejsce w rankingu
        return self._db.rank_of(score_id)

    def top(self, limit: int = 10) -> list[ScoreEntry]:
        """Najlepsze wyniki."""
        # Delegacja do bazy
        return self._db.top_scores(limit)

    def recent(self, limit: int = 20) -> list[ScoreEntry]:
        """Ostatnie gry."""
        # Delegacja do bazy
        return self._db.recent_scores(limit)

    def stats(self) -> GameStats:
        """Statystyki zbiorcze."""
        # Delegacja do bazy
        return self._db.stats()

    def clear(self) -> None:
        """Czyści ranking."""
        # Usunięcie wyników
        self._db.clear_scores()
        # Powiadomienie widoków
        self.emit(EventType.SCORES_CHANGED)
