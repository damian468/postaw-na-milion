"""Klient internetowej bazy pytań Open Trivia DB (https://opentdb.com)."""

# json – parsowanie odpowiedzi serwera
import json
# urllib.parse – dekodowanie tekstów zakodowanych w URL
import urllib.parse
# urllib.request – zapytanie HTTP bez zewnętrznych bibliotek
import urllib.request

# Obiekt pytania
from pnm.model.entities import Question

# Adres API (encode=url3986 – teksty zakodowane procentowo, bez encji HTML)
API_URL = "https://opentdb.com/api.php?amount={amount}&type=multiple&encode=url3986"

# Tłumaczenie nazw kategorii OpenTDB na polski
CATEGORY_NAMES = {
    # Wiedza ogólna
    "General Knowledge": "Wiedza ogólna",
    # Książki
    "Entertainment: Books": "Książki",
    # Film
    "Entertainment: Film": "Film",
    # Muzyka
    "Entertainment: Music": "Muzyka",
    # Musicale i teatr
    "Entertainment: Musicals & Theatres": "Teatr",
    # Telewizja
    "Entertainment: Television": "Telewizja",
    # Gry wideo
    "Entertainment: Video Games": "Gry wideo",
    # Gry planszowe
    "Entertainment: Board Games": "Gry planszowe",
    # Przyroda i nauka
    "Science & Nature": "Nauka i przyroda",
    # Komputery
    "Science: Computers": "Komputery",
    # Matematyka
    "Science: Mathematics": "Matematyka",
    # Mitologia
    "Mythology": "Mitologia",
    # Sport
    "Sports": "Sport",
    # Geografia
    "Geography": "Geografia",
    # Historia
    "History": "Historia",
    # Polityka
    "Politics": "Polityka",
    # Sztuka
    "Art": "Sztuka",
    # Celebryci
    "Celebrities": "Celebryci",
    # Zwierzęta
    "Animals": "Zwierzęta",
    # Pojazdy
    "Vehicles": "Pojazdy",
    # Komiksy
    "Entertainment: Comics": "Komiksy",
    # Gadżety
    "Science: Gadgets": "Gadżety",
    # Anime i manga
    "Entertainment: Japanese Anime & Manga": "Anime i manga",
    # Kreskówki
    "Entertainment: Cartoon & Animations": "Kreskówki",
}

# Zamiana poziomu trudności OpenTDB na skalę 1–3
DIFFICULTY = {"easy": 1, "medium": 2, "hard": 3}


class OnlineError(Exception):
    """Błąd pobierania pytań z Internetu."""


class OpenTriviaClient:
    """Pobiera pytania wielokrotnego wyboru z Open Trivia DB."""

    def __init__(self, timeout: float = 6.0) -> None:
        # Maksymalny czas oczekiwania na odpowiedź serwera
        self.timeout = timeout

    def fetch(self, amount: int = 50) -> list[Question]:
        """Pobiera `amount` pytań (maks. 50). Zgłasza OnlineError przy problemach."""
        # Adres z liczbą pytań (API przyjmuje maks. 50)
        url = API_URL.format(amount=min(50, amount))
        # Zapytanie z nagłówkiem identyfikującym aplikację
        request = urllib.request.Request(url, headers={"User-Agent": "PostawNaMilion/1.0"})
        # Próba pobrania danych
        try:
            # Otwarcie połączenia z limitem czasu
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                # Odczyt i parsowanie JSON
                payload = json.loads(response.read().decode("utf-8"))
        # Brak sieci, przekroczony czas lub zła odpowiedź
        except (OSError, ValueError) as error:
            # Zgłoszenie błędu z czytelnym opisem
            raise OnlineError(f"Brak połączenia z OpenTDB ({error})") from error
        # Kod 0 oznacza sukces
        if payload.get("response_code") != 0:
            # Np. limit zapytań – kod 5
            raise OnlineError(f"OpenTDB zwróciło kod {payload.get('response_code')}")
        # Zamiana wyników na obiekty Question
        return [self._to_question(item) for item in payload.get("results", [])]

    @staticmethod
    def _to_question(item: dict) -> Question:
        """Zamienia rekord OpenTDB na obiekt Question."""
        # Funkcja dekodująca tekst zakodowany procentowo
        decode = urllib.parse.unquote
        # Oryginalna nazwa kategorii
        category = decode(item["category"])
        # Budowa obiektu pytania
        return Question(
            # Treść pytania
            text=decode(item["question"]),
            # Poprawna odpowiedź
            correct=decode(item["correct_answer"]),
            # Błędne odpowiedzi
            wrong=[decode(w) for w in item["incorrect_answers"]],
            # Kategoria po polsku (z dopiskiem, że pytanie jest z sieci)
            category=CATEGORY_NAMES.get(category, category) + " (EN)",
            # Trudność w skali 1–3
            difficulty=DIFFICULTY.get(item.get("difficulty", "medium"), 2),
            # Oznaczenie źródła
            source="online",
        )
