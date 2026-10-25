"""Pula pytań na jedną grę – losowanie kategorii i pytań bez powtórzeń."""

# random – losowanie kategorii, pytań i kolejności odpowiedzi
import random
# defaultdict – grupowanie pytań po kategoriach
from collections import defaultdict

# Obiekty danych
from pnm.model.entities import Question, RoundQuestion


class QuestionPool:
    """Pytania dostępne w bieżącej grze, pogrupowane po kategoriach."""

    def __init__(self, questions: list[Question], rng: random.Random | None = None) -> None:
        # Generator losowy (w testach można podać własny z ziarnem)
        self._rng = rng or random.Random()
        # Słownik: kategoria -> lista niewykorzystanych pytań
        self._by_category: dict[str, list[Question]] = defaultdict(list)
        # Grupowanie pytań
        for question in questions:
            # Pomijamy pytania z mniej niż jedną błędną odpowiedzią
            if len(question.wrong) >= 1:
                # Dodanie do kategorii
                self._by_category[question.category].append(question)
        # Ostatnio wybrana kategoria (nie proponujemy jej od razu ponownie)
        self._last_category: str | None = None

    @property
    def size(self) -> int:
        """Liczba niewykorzystanych pytań."""
        # Suma długości list
        return sum(len(items) for items in self._by_category.values())

    def available_categories(self) -> list[str]:
        """Kategorie, w których zostały jeszcze pytania."""
        # Tylko niepuste kategorie
        return [name for name, items in self._by_category.items() if items]

    def pick_categories(self, count: int = 2) -> list[str]:
        """Losuje `count` różnych kategorii do wyboru przez gracza."""
        # Kategorie z pytaniami
        available = self.available_categories()
        # Najpierw próbujemy pominąć ostatnio graną kategorię
        fresh = [c for c in available if c != self._last_category]
        # Jeśli świeżych jest dość – losujemy z nich
        source = fresh if len(fresh) >= count else available
        # Losowanie bez powtórzeń (nie więcej, niż jest kategorii)
        return self._rng.sample(source, min(count, len(source)))

    def draw(self, category: str, difficulty: int, answers_count: int) -> RoundQuestion:
        """Wyciąga z kategorii pytanie o trudności najbliższej docelowej."""
        # Lista pytań kategorii
        items = self._by_category[category]
        # Najmniejsza różnica trudności w tej kategorii
        best = min(abs(q.difficulty - difficulty) for q in items)
        # Pytania o najlepiej dopasowanej trudności
        candidates = [q for q in items if abs(q.difficulty - difficulty) == best]
        # Losujemy jedno z nich
        question = self._rng.choice(candidates)
        # Usuwamy je z puli (bez powtórzeń w grze)
        items.remove(question)
        # Zapamiętujemy kategorię
        self._last_category = category
        # Wybieramy losowo potrzebną liczbę błędnych odpowiedzi
        wrong = self._rng.sample(question.wrong, min(answers_count - 1, len(question.wrong)))
        # Łączymy z poprawną odpowiedzią
        answers = [question.correct, *wrong]
        # Tasujemy kolejność
        self._rng.shuffle(answers)
        # Budujemy pytanie rundy
        return RoundQuestion(question=question, answers=answers,
                             correct_index=answers.index(question.correct))
