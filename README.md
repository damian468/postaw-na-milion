# Postaw na milion – teleturniej w trybie tekstowym

Konsolowa wersja teleturnieju „Postaw na milion” (format *The Million Pound Drop*).
Gracz dostaje **1 000 000 zł w 40 paczkach po 25 000 zł** i rozkłada je na zapadnie
z odpowiedziami. Zapadnie pod błędnymi odpowiedziami się otwierają, a pieniądze spadają.

## Uruchomienie (cmd / PowerShell / Windows Terminal)

```bat
cd postaw_na_milion
pip install -r requirements.txt
python main.py
```

Wymagany Python 3.10+ (testowane na 3.14). Najlepiej wygląda w Windows Terminal
(domyślny terminal w Windows 11). Okno powinno mieć co najmniej 100×30 znaków.

Opcjonalnie: `python main.py --gui` uruchamia tę samą grę w oknie (tkinter).
To demonstracja architektury MVC: ten sam model i kontroler, inny widok.

Testy: `python -m unittest discover tests` (logika + automatyczny „gracz” w trybie tekstowym).

## Zasady gry

* Przed każdym pytaniem wybierasz jedną z dwóch kategorii.
* Musisz rozłożyć **wszystkie** pieniądze. To, czego nie rozłożysz przed końcem czasu, przepada.
* **Co najmniej jedna zapadnia musi zostać pusta.**
* Pytania 1–4 mają 4 odpowiedzi, 5–7 mają 3, a finałowe ma 2 (gra pełna, 8 pytań).
* Zachowujesz pieniądze z poprawnej odpowiedzi. Gra kończy się po ostatnim pytaniu albo gdy stracisz wszystko.

## Sterowanie

| Klawisz | Działanie |
|---|---|
| `←` `→` / `1`–`4` | wybór odpowiedzi lub kategorii |
| `↑` `+` / `↓` `−` | dołóż / zdejmij paczkę (25 000 zł) |
| `PgUp` / `PgDn` | dołóż / zdejmij 10 paczek |
| `A` | cała reszta na wybraną odpowiedź |
| `Backspace` / `R` | wyczyść odpowiedź / wszystkie odpowiedzi |
| `Enter` | zatwierdź / zamknij zakłady / dalej |
| `Spacja` | pomiń animację otwierania zapadni |
| `P` / `Esc` | pauza / przerwanie gry |
| `F2` | panel diagnostyczny odświeżania |
| mysz | klik wybiera kolumnę, kółko dokłada/zdejmuje paczki |

Pasek na dole ekranu pokazuje tylko skróty dostępne w bieżącej fazie gry.

## Funkcje

* **Menu strzałkowe**, animowane logo ASCII z refleksem światła, „deszcz pieniędzy”.
* **Animacja ASCII otwierania zapadni**: skrzydła się rozsuwają, paczki spadają.
* Zegar z dużymi cyframi i paskiem, który zmienia kolor i miga w ostatnich sekundach.
* Drabinka pytań z wynikami rund, ekran podsumowania z iskierkami i tabelą przebiegu gry.
* **Ustawienia** (zapis w `data/settings.json`): imię, czas na pytanie (30–90 s lub bez limitu),
  długość gry (5/8 pytań), źródło pytań, 5 motywów kolorystycznych z podglądem na żywo,
  tempo animacji, dźwięk, podpowiedzi klawiszy.
* **Baza danych SQLite** (`data/pnm.db`): ok. 140 pytań w 10 kategoriach z 3 poziomami
  trudności. Edytor pozwala przeglądać, dodawać (z walidacją) i usuwać pytania.
* **Ranking i statystyki** w SQLite: Top 10, historia gier, statystyki zbiorcze.
* **Internet**: pytania z Open Trivia DB (opentdb.com, po angielsku), samodzielnie
  lub razem z pytaniami lokalnymi. Bez sieci gra wraca do bazy lokalnej i wyświetla komunikat.

## Architektura MVC

```
pnm/
├── model/          – dane i zasady gry, BEZ żadnego kodu interfejsu
│   ├── game.py         zasady teleturnieju (stan, zakłady, zegar, zapadnie)
│   ├── observable.py   wzorzec Obserwator – model wysyła zdarzenia
│   ├── settings.py     ustawienia + JSON
│   ├── database.py     SQLite (pytania, ranking)
│   ├── repositories.py obserwowalny bank pytań i ranking
│   ├── question_pool.py losowanie kategorii i pytań
│   └── online.py       klient Open Trivia DB
├── controller/     – akcje użytkownika → operacje na modelu, nawigacja
│   ├── view_interface.py  abstrakcyjny interfejs View (kontrakt dla każdego UI)
│   ├── app_controller.py  menu, ustawienia, ranking, baza pytań
│   └── game_controller.py przebieg gry, zegar, sekwencja otwierania zapadni
└── view/
    ├── tui/        – widok TEKSTOWY (Textual), domyślny
    └── gui/        – widok GRAFICZNY (tkinter), dowód przenośności
```

* Kontroler zna wyłącznie interfejs `View` (`navigate`, `notify`, `run_background`,
  `apply_theme`, `bell`, `quit`), a nie konkretną bibliotekę.
* Widoki czytają model i subskrybują jego zdarzenia. Zmieniają go **tylko** przez kontroler.
* Przejście z trybu tekstowego do graficznego wymagało wyłącznie napisania
  `view/gui/app.py`. Model i kontrolery nie zmieniły się ani o linijkę.
* Logikę testuje się bez interfejsu (`tests/test_logic.py`, atrapa widoku `FakeView`).

## Odświeżanie tylko zmienionych elementów

Każdy element ekranu (zegar, kolumna odpowiedzi, pula, drabinka…) to osobny widżet,
który subskrybuje tylko „swoje” zdarzenia modelu:

* `TIME_CHANGED` jest wysyłane **raz na sekundę** (przy zmianie pełnej sekundy), więc
  odświeża się wyłącznie zegar.
* `BETS_CHANGED(answer=i)` odświeża **tylko kolumnę i** oraz pasek puli.
* zmiana zaznaczenia w menu lub ustawieniach przerysowuje tylko 2 pozycje: poprzednią i nową;
* animacja zapadni przerysowuje tylko jedną kolumnę.

Klawisz **F2** pokazuje licznik odświeżeń każdego widżetu, więc można to sprawdzić na żywo.
