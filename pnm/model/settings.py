"""Model ustawień użytkownika z zapisem do pliku JSON."""

# json – zapis i odczyt pliku ustawień
import json
# dataclass – opis pojedynczego ustawienia
from dataclasses import dataclass
# Path – ścieżka do pliku
from pathlib import Path
# Any – wartości ustawień mogą mieć różne typy
from typing import Any

# Mechanizm powiadamiania obserwatorów
from pnm.model.observable import EventType, Observable


@dataclass(frozen=True)
class SettingOption:
    """Jedna możliwa wartość ustawienia wraz z etykietą dla użytkownika."""

    # Wartość zapisywana w pliku
    value: Any
    # Etykieta wyświetlana w menu
    label: str


@dataclass(frozen=True)
class SettingDefinition:
    """Opis ustawienia: klucz, etykieta, opis i dozwolone wartości."""

    # Klucz w słowniku ustawień
    key: str
    # Nazwa wyświetlana w menu
    label: str
    # Krótki opis pod listą ustawień
    description: str
    # Wartość domyślna
    default: Any
    # Dozwolone wartości (pusta krotka = dowolny tekst)
    options: tuple[SettingOption, ...] = ()

    @property
    def is_text(self) -> bool:
        """Czy ustawienie jest polem tekstowym."""
        # Brak listy opcji oznacza pole tekstowe
        return not self.options


# Maksymalna długość imienia gracza
MAX_NAME_LENGTH = 16

# Pełna lista ustawień – widoki budują z niej menu automatycznie
SETTINGS_SCHEMA: tuple[SettingDefinition, ...] = (
    # Imię gracza zapisywane w rankingu
    SettingDefinition("player_name", "Imię gracza",
                      "Pod tym imieniem zapiszesz się w rankingu.", "Gracz"),
    # Limit czasu na rozłożenie pieniędzy
    SettingDefinition("time_limit", "Czas na pytanie",
                      "Ile sekund masz na rozłożenie pieniędzy na zapadnie.", 60, (
                          # Tryb ekspresowy
                          SettingOption(30, "30 sekund"),
                          # Tryb szybki
                          SettingOption(45, "45 sekund"),
                          # Tryb telewizyjny
                          SettingOption(60, "60 sekund (jak w TV)"),
                          # Tryb spokojny
                          SettingOption(90, "90 sekund"),
                          # Tryb treningowy
                          SettingOption(0, "Bez limitu (trening)"),
                      )),
    # Liczba pytań w grze
    SettingDefinition("game_length", "Długość gry",
                      "Pełna gra to 8 pytań, krótka – 5.", 8, (
                          # Krótka gra
                          SettingOption(5, "Krótka – 5 pytań"),
                          # Pełna gra
                          SettingOption(8, "Pełna – 8 pytań"),
                      )),
    # Skąd brać pytania
    SettingDefinition("question_source", "Źródło pytań",
                      "Pytania z lokalnej bazy SQLite lub pobierane z Internetu (Open Trivia DB).",
                      "local", (
                          # Lokalna baza po polsku
                          SettingOption("local", "Lokalna baza (PL)"),
                          # Internetowa baza po angielsku
                          SettingOption("online", "Internet – OpenTDB (EN)"),
                          # Oba źródła naraz
                          SettingOption("mixed", "Mieszane"),
                      )),
    # Motyw kolorystyczny
    SettingDefinition("theme", "Motyw kolorystyczny",
                      "Zmienia kolory całej aplikacji – podgląd na żywo.", "studio", (
                          # Ciemnoniebieskie studio telewizyjne
                          SettingOption("studio", "Studio TV"),
                          # Fioletowo-różowy neon
                          SettingOption("neon", "Neon"),
                          # Zielony monitor fosforowy
                          SettingOption("retro", "Retro terminal"),
                          # Złoto i czerń
                          SettingOption("gold", "Złoty skarbiec"),
                          # Jasny motyw dzienny
                          SettingOption("day", "Dzienny (jasny)"),
                      )),
    # Szybkość animacji
    SettingDefinition("animation", "Animacje",
                      "Tempo otwierania zapadni i efektów ASCII.", "normal", (
                          # Pełne napięcie
                          SettingOption("normal", "Normalne"),
                          # Przyspieszone
                          SettingOption("fast", "Szybkie"),
                          # Bez animacji
                          SettingOption("off", "Wyłączone"),
                      )),
    # Sygnały dźwiękowe terminala
    SettingDefinition("sound", "Dźwięk",
                      "Sygnał dźwiękowy przy końcówce czasu i otwarciu zapadni.", True, (
                          # Dźwięk włączony
                          SettingOption(True, "Włączony"),
                          # Dźwięk wyłączony
                          SettingOption(False, "Wyłączony"),
                      )),
    # Podpowiedzi klawiszy na ekranie gry
    SettingDefinition("show_hints", "Podpowiedzi klawiszy",
                      "Pasek ze skrótami klawiszowymi na dole ekranu.", True, (
                          # Pokazuj pasek
                          SettingOption(True, "Pokazuj"),
                          # Ukryj pasek
                          SettingOption(False, "Ukryj"),
                      )),
)


class SettingsModel(Observable):
    """Przechowuje ustawienia, waliduje je i zapisuje do pliku JSON."""

    def __init__(self, path: Path | None = None) -> None:
        # Inicjalizacja mechanizmu obserwatorów
        super().__init__()
        # Ścieżka pliku (None = bez zapisu, np. w testach)
        self._path = path
        # Słownik definicji po kluczu
        self._definitions = {d.key: d for d in SETTINGS_SCHEMA}
        # Wartości domyślne
        self._values: dict[str, Any] = {d.key: d.default for d in SETTINGS_SCHEMA}
        # Wczytanie zapisanych wartości
        self.load()

    @property
    def definitions(self) -> tuple[SettingDefinition, ...]:
        """Wszystkie definicje ustawień w kolejności wyświetlania."""
        # Zwracamy schemat
        return SETTINGS_SCHEMA

    def definition(self, key: str) -> SettingDefinition:
        """Definicja ustawienia o podanym kluczu."""
        # Odczyt ze słownika
        return self._definitions[key]

    def get(self, key: str) -> Any:
        """Wartość ustawienia."""
        # Odczyt ze słownika wartości
        return self._values[key]

    def __getitem__(self, key: str) -> Any:
        """Skrót: settings["klucz"]."""
        # Delegacja do get
        return self.get(key)

    def label(self, key: str) -> str:
        """Etykieta bieżącej wartości ustawienia."""
        # Definicja ustawienia
        definition = self.definition(key)
        # Pole tekstowe – etykietą jest sama wartość
        if definition.is_text:
            # Zwracamy tekst
            return str(self._values[key])
        # Szukamy opcji z bieżącą wartością
        for option in definition.options:
            # Porównanie wartości
            if option.value == self._values[key]:
                # Znaleziona etykieta
                return option.label
        # Awaryjnie – sama wartość
        return str(self._values[key])

    def _validate(self, key: str, value: Any) -> Any:
        """Sprawdza wartość; zwraca wartość poprawioną lub zgłasza ValueError."""
        # Definicja ustawienia
        definition = self.definition(key)
        # Pole tekstowe – przycinamy i ograniczamy długość
        if definition.is_text:
            # Usunięcie białych znaków z brzegów
            text = str(value).strip()
            # Pusty tekst jest niedozwolony
            if not text:
                # Błąd walidacji
                raise ValueError("Wartość nie może być pusta.")
            # Obcięcie do maksymalnej długości
            return text[:MAX_NAME_LENGTH]
        # Wartość musi być jedną z opcji
        if value not in [option.value for option in definition.options]:
            # Błąd walidacji
            raise ValueError(f"Niedozwolona wartość: {value!r}")
        # Wartość poprawna
        return value

    def set(self, key: str, value: Any) -> None:
        """Ustawia wartość, zapisuje plik i powiadamia obserwatorów."""
        # Walidacja (może zgłosić ValueError)
        value = self._validate(key, value)
        # Bez zmiany nie robimy nic
        if self._values[key] == value:
            # Wyjście
            return
        # Zapis wartości
        self._values[key] = value
        # Zapis do pliku
        self.save()
        # Powiadomienie obserwatorów
        self.emit(EventType.SETTING_CHANGED, key=key, value=value)

    def cycle(self, key: str, step: int) -> None:
        """Przełącza ustawienie na poprzednią/następną opcję (z zawijaniem)."""
        # Definicja ustawienia
        definition = self.definition(key)
        # Pól tekstowych nie da się przełączać
        if definition.is_text:
            # Wyjście
            return
        # Lista wartości
        values = [option.value for option in definition.options]
        # Indeks bieżącej wartości (0 gdy nieznana)
        index = values.index(self._values[key]) if self._values[key] in values else 0
        # Nowa wartość z zawijaniem
        self.set(key, values[(index + step) % len(values)])

    def load(self) -> None:
        """Wczytuje ustawienia z pliku (błędne wartości są pomijane)."""
        # Bez ścieżki lub pliku nic nie wczytujemy
        if self._path is None or not self._path.exists():
            # Zostają wartości domyślne
            return
        # Próba odczytu pliku
        try:
            # Odczyt i parsowanie JSON
            stored = json.loads(self._path.read_text(encoding="utf-8"))
        # Uszkodzony plik – zostają wartości domyślne
        except (OSError, ValueError):
            # Wyjście
            return
        # Przepisujemy tylko znane i poprawne wartości
        for key, value in stored.items():
            # Pomijamy nieznane klucze
            if key not in self._definitions:
                # Następny klucz
                continue
            # Walidacja wartości
            try:
                # Zapis poprawnej wartości
                self._values[key] = self._validate(key, value)
            # Niepoprawna wartość – zostaje domyślna
            except ValueError:
                # Następny klucz
                continue

    def save(self) -> None:
        """Zapisuje ustawienia do pliku JSON."""
        # Bez ścieżki nie zapisujemy
        if self._path is None:
            # Wyjście
            return
        # Tworzymy katalog, jeśli nie istnieje
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Zapis z polskimi znakami i wcięciami
        self._path.write_text(json.dumps(self._values, ensure_ascii=False, indent=2),
                              encoding="utf-8")
