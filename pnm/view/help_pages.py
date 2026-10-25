"""Teksty zasad gry – wspólne dla widoku tekstowego i graficznego.

Znaczniki [b]...[/b] to formatowanie Textual; widok graficzny je usuwa.
"""

# Ilustracja zapadni (czysty tekst, bez zależności od Textual)
from pnm.view.tui.ascii_art import TRAPDOOR_ART

# Strony pomocy: (tytuł, treść)
PAGES = (
    # Strona 1 – idea gry
    ("O CO CHODZI?",
     "Na start dostajesz [b $accent]1 000 000 zł[/] w [b]40 paczkach po 25 000 zł[/b].\n\n"
     "Przed każdym pytaniem wybierasz jedną z [b]dwóch kategorii[/b]. Potem rozkładasz\n"
     "pieniądze na zapadnie z odpowiedziami. Gdy zakłady się zamkną, zapadnie pod\n"
     "błędnymi odpowiedziami otwierają się – a pieniądze na nich [b $error]spadają[/].\n\n"
     "Zachowujesz to, co leżało na poprawnej odpowiedzi. Z tą kwotą grasz dalej.\n"
     "Po ostatnim pytaniu – wszystko, co zostało, jest Twoje!"),
    # Strona 2 – zasady
    ("ZASADY",
     "• Musisz rozłożyć [b]wszystkie[/b] pieniądze – nierozłożone po upływie czasu przepadają.\n"
     "• [b $warning]Co najmniej jedna zapadnia musi zostać pusta[/] – nie można obstawić wszystkiego.\n"
     "• Pierwsze pytania mają 4 odpowiedzi, kolejne 3, a finałowe tylko 2\n"
     "  (w finale stawiasz wszystko na jedną odpowiedź!).\n"
     "• Pytania są coraz trudniejsze.\n"
     "• Gra kończy się po ostatnim pytaniu lub gdy stracisz wszystkie pieniądze.\n"
     + TRAPDOOR_ART),
    # Strona 3 – sterowanie
    ("STEROWANIE",
     "[b]←  →[/b]  lub  [b]1–4[/b]      wybór odpowiedzi / kategorii\n"
     "[b]↑  +[/b]               dołóż paczkę (25 000 zł)\n"
     "[b]↓  −[/b]               zdejmij paczkę\n"
     "[b]PgUp / PgDn[/b]        dołóż / zdejmij 10 paczek (250 000 zł)\n"
     "[b]A[/b]                  wszystko, co zostało, na wybraną odpowiedź\n"
     "[b]Backspace[/b]          zdejmij wszystko z wybranej odpowiedzi\n"
     "[b]R[/b]                  zdejmij wszystko ze wszystkich odpowiedzi\n"
     "[b]Enter[/b]              zatwierdź / zamknij zakłady / dalej\n"
     "[b]Spacja[/b]             pomiń animację otwierania zapadni\n"
     "[b]P[/b]  /  [b]Esc[/b]           pauza  /  przerwanie gry\n\n"
     "[b]Mysz:[/b] kliknij kolumnę, kręć kółkiem nad kolumną, by dokładać/zdejmować paczki."),
    # Strona 4 – opcje
    ("CIEKAWOSTKI",
     "• W [b]Ustawieniach[/b] zmienisz czas, długość gry, motyw kolorystyczny i źródło pytań.\n"
     "• Źródło [b]Internet[/b] pobiera pytania z Open Trivia DB (po angielsku).\n"
     "• W [b]Bazie pytań[/b] możesz dopisać własne pytania – trafiają do bazy SQLite.\n"
     "• Klawisz [b]F2[/b] włącza panel diagnostyczny: widać w nim, ile razy odświeżył się\n"
     "  każdy element ekranu. Zegar odświeża się raz na sekundę, a dołożenie paczki\n"
     "  przerysowuje tylko jedną kolumnę – reszta ekranu pozostaje nietknięta.\n"
     "• Grę można uruchomić też w trybie graficznym:  [b]python main.py --gui[/b]\n"
     "  – ten sam model i kontroler, inny widok (architektura MVC)."),
)
