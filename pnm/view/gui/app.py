"""Widok graficzny (tkinter) – druga implementacja interfejsu View.

Korzysta z DOKŁADNIE tych samych modeli i kontrolerów co widok tekstowy.
Pokazuje, że przeniesienie gry z trybu tekstowego do graficznego wymaga
napisania jedynie nowej warstwy widoku – logika gry pozostaje bez zmian.
"""

# queue – przekazywanie wyników z wątku roboczego do wątku UI
import queue
# re – usuwanie znaczników formatowania z tekstów pomocy
import re
# threading – zadania w tle (pobieranie pytań)
import threading
# time – pomiar upływu czasu
import time
# tkinter – standardowa biblioteka okienkowa Pythona
import tkinter as tk
# messagebox – okna dialogowe, ttk – nowocześniejsze kontrolki
from tkinter import messagebox, ttk
# Typy funkcji zwrotnych
from typing import Any, Callable

# Stałe i formatowanie
from pnm.config import ANSWER_LETTERS, bundles_to_money, format_money
# Kontekst aplikacji
from pnm.context import AppContext
# Interfejs widoku
from pnm.controller.view_interface import ScreenId, View
# Model gry
from pnm.model.game import GamePhase
# Zdarzenia
from pnm.model.observable import Event, EventType

# Palety kolorów odpowiadające motywom widoku tekstowego
PALETTES = {
    # Studio TV
    "studio": dict(bg="#05070F", surface="#0B1226", panel="#13203F", fg="#E6EEFF",
                   primary="#2FA4FF", accent="#FFC83D", success="#3DDC84", error="#FF4D5E",
                   warning="#FFB020"),
    # Neon
    "neon": dict(bg="#0A0014", surface="#14002A", panel="#22003F", fg="#F4E9FF",
                 primary="#FF2BD6", accent="#00F0FF", success="#39FF88", error="#FF3860",
                 warning="#FFE14D"),
    # Retro terminal
    "retro": dict(bg="#000A00", surface="#001A05", panel="#002A0A", fg="#9CFFB0",
                  primary="#33FF66", accent="#FFCC00", success="#66FF99", error="#FF5533",
                  warning="#FFCC00"),
    # Złoty skarbiec
    "gold": dict(bg="#0D0B07", surface="#1A160D", panel="#2A2214", fg="#F6EBD0",
                 primary="#E5B83B", accent="#FFE08A", success="#7BD389", error="#E63946",
                 warning="#FF9F1C"),
    # Dzienny
    "day": dict(bg="#F4F1E8", surface="#FFFFFF", panel="#E3DED0", fg="#1B1B1B",
                primary="#0B5394", accent="#B8860B", success="#2E7D32", error="#C62828",
                warning="#C77700"),
}

# Czcionka nagłówków
TITLE_FONT = ("Segoe UI", 28, "bold")
# Czcionka zwykła
FONT = ("Segoe UI", 12)
# Czcionka pogrubiona
BOLD = ("Segoe UI", 12, "bold")
# Czcionka dużych kwot
BIG = ("Segoe UI", 22, "bold")


class GuiView(View):
    """Widok okienkowy gry."""

    def __init__(self, ctx: AppContext) -> None:
        # Modele i kontrolery
        self.ctx = ctx
        # Główne okno
        self.root = tk.Tk()
        # Tytuł okna
        self.root.title("Postaw na milion")
        # Rozmiar startowy
        self.root.geometry("1180x760")
        # Minimalny rozmiar
        self.root.minsize(980, 640)
        # Bieżąca paleta
        self.c = PALETTES["studio"]
        # Ramka bieżącego ekranu
        self._frame: tk.Frame | None = None
        # Identyfikator bieżącego ekranu
        self._screen: ScreenId | None = None
        # Funkcje wypisujące subskrypcje bieżącego ekranu
        self._unsubscribers: list[Callable[[], None]] = []
        # Obsługa klawiatury bieżącego ekranu
        self._key_handler: Callable[[tk.Event], None] | None = None
        # Kolejka wyników zadań w tle
        self._results: queue.Queue = queue.Queue()
        # Czas ostatniego tyknięcia
        self._last = time.monotonic()
        # Etykieta powiadomień (tworzona przy pierwszym użyciu)
        self._toast: tk.Label | None = None
        # Jedno globalne przechwytywanie klawiszy
        self.root.bind("<Key>", self._on_key)

    # ============================================================ interfejs View

    def run(self) -> None:
        # Start zegara gry
        self.root.after(100, self._tick)
        # Start kontrolera po uruchomieniu pętli
        self.root.after(0, self.ctx.app_controller.start)
        # Pętla zdarzeń tkinter
        self.root.mainloop()

    def navigate(self, screen: ScreenId) -> None:
        # Wypisanie subskrypcji poprzedniego ekranu
        for unsubscribe in self._unsubscribers:
            # Wypisanie
            unsubscribe()
        # Wyczyszczenie listy
        self._unsubscribers = []
        # Usunięcie poprzedniego ekranu
        if self._frame is not None:
            # Zniszczenie ramki z całą zawartością
            self._frame.destroy()
        # Nowa ramka ekranu
        self._frame = tk.Frame(self.root, bg=self.c["bg"])
        # Wypełnienie okna
        self._frame.pack(fill="both", expand=True)
        # Zapamiętanie ekranu
        self._screen = screen
        # Brak obsługi klawiszy do czasu zbudowania ekranu
        self._key_handler = None
        # Budowa ekranu
        getattr(self, f"_build_{screen.name.lower()}")(self._frame)

    def notify(self, message: str, severity: str = "information") -> None:
        # Kolor zależny od wagi komunikatu
        color = {"warning": self.c["warning"], "error": self.c["error"]}.get(severity, self.c["primary"])
        # Usunięcie poprzedniego komunikatu
        if self._toast is not None:
            # Zniszczenie etykiety
            self._toast.destroy()
        # Nowa etykieta w prawym dolnym rogu
        self._toast = tk.Label(self.root, text=message, bg=color, fg=self.c["bg"], font=BOLD,
                               padx=14, pady=8, wraplength=420, justify="left")
        # Umieszczenie nad zawartością
        self._toast.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        # Zapamiętanie etykiety do zamknięcia
        toast = self._toast
        # Automatyczne ukrycie po 3,5 s
        self.root.after(3500, lambda: toast.winfo_exists() and toast.destroy())

    def run_background(self, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        def work() -> None:
            # Wynik zadania trafia do kolejki
            self._results.put((on_done, task()))

        # Wątek roboczy (daemon – nie blokuje zamknięcia)
        threading.Thread(target=work, daemon=True).start()

    def apply_theme(self, theme: str) -> None:
        # Nowa paleta
        self.c = PALETTES.get(theme, PALETTES["studio"])
        # Tło okna
        self.root.configure(bg=self.c["bg"])
        # Style kontrolek ttk
        self._style_ttk()
        # Przebudowa bieżącego ekranu w nowych kolorach
        if self._screen is not None:
            # Ponowne wejście na ten sam ekran
            self.navigate(self._screen)

    def bell(self) -> None:
        # Dźwięk systemowy
        self.root.bell()

    def quit(self) -> None:
        # Zamknięcie okna
        self.root.destroy()

    # ============================================================ mechanika

    def _tick(self) -> None:
        """Zegar gry i odbiór wyników zadań w tle (10 razy na sekundę)."""
        # Bieżący czas
        now = time.monotonic()
        # Upływ czasu do kontrolera
        self.ctx.game_controller.tick(min(0.5, now - self._last))
        # Zapamiętanie czasu
        self._last = now
        # Odbiór zakończonych zadań w tle
        while not self._results.empty():
            # Funkcja zwrotna i wynik
            on_done, result = self._results.get()
            # Wywołanie w wątku UI
            on_done(result)
        # Kolejne tyknięcie
        self.root.after(100, self._tick)

    def _on_key(self, event: tk.Event) -> None:
        """Przekazuje naciśnięcia klawiszy do bieżącego ekranu."""
        # Ekran ma obsługę klawiszy
        if self._key_handler is not None:
            # Wywołanie obsługi
            self._key_handler(event)

    def _observe(self, model, handler) -> None:
        """Subskrypcja modelu na czas życia ekranu."""
        # Zapamiętanie funkcji wypisującej
        self._unsubscribers.append(model.subscribe(handler))

    def _style_ttk(self) -> None:
        """Dopasowuje kontrolki ttk do palety."""
        # Obiekt stylów
        style = ttk.Style(self.root)
        # Motyw bazowy pozwalający zmieniać kolory
        style.theme_use("clam")
        # Tabele
        style.configure("Treeview", background=self.c["surface"], fieldbackground=self.c["surface"],
                        foreground=self.c["fg"], rowheight=26, font=FONT)
        # Nagłówki tabel
        style.configure("Treeview.Heading", background=self.c["panel"], foreground=self.c["accent"],
                        font=BOLD)
        # Zaznaczony wiersz
        style.map("Treeview", background=[("selected", self.c["primary"])],
                  foreground=[("selected", self.c["bg"])])
        # Zakładki
        style.configure("TNotebook", background=self.c["bg"])
        # Pojedyncza zakładka
        style.configure("TNotebook.Tab", background=self.c["panel"], foreground=self.c["fg"],
                        font=BOLD, padding=(14, 6))
        # Wybrana zakładka
        style.map("TNotebook.Tab", background=[("selected", self.c["accent"])],
                  foreground=[("selected", self.c["bg"])])

    # ------------------------------------------------------- pomocnicze widżety

    def _label(self, parent, text="", font=FONT, fg=None, bg=None, **kw) -> tk.Label:
        """Etykieta w kolorach motywu."""
        # Utworzenie etykiety
        return tk.Label(parent, text=text, font=font, fg=fg or self.c["fg"],
                        bg=bg or self.c["bg"], **kw)

    def _button(self, parent, text, command, accent=False, padx=16, **kw) -> tk.Button:
        """Przycisk w kolorach motywu."""
        # Kolor tła przycisku
        background = self.c["accent"] if accent else self.c["panel"]
        # Utworzenie przycisku
        return tk.Button(parent, text=text, command=command, font=BOLD, relief="flat",
                         bg=background, fg=self.c["bg"] if accent else self.c["fg"],
                         activebackground=self.c["primary"], activeforeground=self.c["bg"],
                         cursor="hand2", padx=padx, pady=8, **kw)

    def _title(self, parent, text) -> None:
        """Tytuł ekranu."""
        # Etykieta tytułu
        self._label(parent, text, TITLE_FONT, fg=self.c["accent"]).pack(pady=(24, 12))

    def _back_button(self, parent) -> None:
        """Przycisk powrotu do menu."""
        # Przycisk na dole ekranu
        self._button(parent, "◀  Menu główne (Esc)", self.ctx.app_controller.back_to_menu).pack(pady=14)

    def _escape_goes_back(self, event: tk.Event) -> None:
        """Obsługa klawiszy ekranów z samym powrotem."""
        # Esc – powrót do menu
        if event.keysym == "Escape":
            # Przez kontroler
            self.ctx.app_controller.back_to_menu()

    # ============================================================ ekrany

    def _build_main_menu(self, frame: tk.Frame) -> None:
        """Menu główne."""
        # Pierwsze uruchomienie – style ttk
        self._style_ttk()
        # Logo
        self._label(frame, "POSTAW NA MILION", ("Segoe UI Black", 46), fg=self.c["primary"]).pack(pady=(50, 0))
        # Hasło
        self._label(frame, "T E L E T U R N I E J   ·   1 000 000 zł", BOLD, fg=self.c["accent"]).pack(pady=(0, 30))
        # Przyciski menu (pozycje z kontrolera – te same co w wersji tekstowej)
        buttons = []
        # Każda pozycja menu
        for item in self.ctx.app_controller.menu_items:
            # Przycisk pozycji
            button = self._button(frame, item.label, lambda i=item.id: self.ctx.app_controller.select_menu(i),
                                  width=28)
            # Ułożenie
            button.pack(pady=4)
            # Zapamiętanie
            buttons.append(button)
        # Opis pozycji
        description = self._label(frame, self.ctx.app_controller.menu_items[0].description,
                                  fg=self.c["primary"])
        # Ułożenie opisu
        description.pack(pady=18)
        # Indeks wybranej pozycji
        state = {"index": 0}

        def highlight(index: int) -> None:
            # Indeks z zawijaniem
            index %= len(buttons)
            # Odznaczenie poprzedniego przycisku (zmiana tylko dwóch przycisków)
            buttons[state["index"]].configure(bg=self.c["panel"], fg=self.c["fg"])
            # Zapamiętanie
            state["index"] = index
            # Zaznaczenie nowego
            buttons[index].configure(bg=self.c["accent"], fg=self.c["bg"])
            # Opis pozycji
            description.configure(text=self.ctx.app_controller.menu_items[index].description)

        def on_key(event: tk.Event) -> None:
            # Strzałka w górę
            if event.keysym == "Up":
                # Poprzednia pozycja
                highlight(state["index"] - 1)
            # Strzałka w dół
            elif event.keysym == "Down":
                # Następna pozycja
                highlight(state["index"] + 1)
            # Enter
            elif event.keysym == "Return":
                # Zatwierdzenie
                buttons[state["index"]].invoke()

        # Najechanie myszą podświetla pozycję
        for index, button in enumerate(buttons):
            # Zdarzenie najechania
            button.bind("<Enter>", lambda _e, i=index: highlight(i))
        # Podświetlenie pierwszej pozycji
        highlight(0)
        # Obsługa klawiatury
        self._key_handler = on_key

    def _build_loading(self, frame: tk.Frame) -> None:
        """Ekran ładowania."""
        # Napis
        self._label(frame, "Przygotowuję pytania…", TITLE_FONT, fg=self.c["primary"]).pack(expand=True)

    def _build_help(self, frame: tk.Frame) -> None:
        """Zasady gry."""
        # Strony pomocy (tekst wspólny z wersją tekstową)
        from pnm.view.help_pages import PAGES
        # Tytuł
        self._title(frame, "Jak grać?")
        # Pole tekstowe z zasadami
        text = tk.Text(frame, font=("Consolas", 12), bg=self.c["surface"], fg=self.c["fg"],
                       relief="flat", padx=20, pady=16, wrap="word")
        # Każda strona pomocy
        for title, body in PAGES:
            # Treść bez znaczników formatowania
            plain = re.sub(r"\[/?[^\]]*\]", "", body)
            # Dopisanie strony
            text.insert("end", f"{title}\n\n{plain}\n\n")
        # Tylko do odczytu
        text.configure(state="disabled")
        # Ułożenie
        text.pack(fill="both", expand=True, padx=40)
        # Powrót
        self._back_button(frame)
        # Esc – powrót
        self._key_handler = self._escape_goes_back

    def _build_settings(self, frame: tk.Frame) -> None:
        """Ustawienia – te same definicje co w wersji tekstowej."""
        # Tytuł
        self._title(frame, "Ustawienia")
        # Siatka ustawień
        grid = tk.Frame(frame, bg=self.c["bg"])
        # Ułożenie
        grid.pack(pady=10)
        # Każde ustawienie ze schematu modelu
        for row, definition in enumerate(self.ctx.settings.definitions):
            # Etykieta
            self._label(grid, definition.label, BOLD).grid(row=row, column=0, sticky="w", padx=12, pady=8)
            # Pole tekstowe
            if definition.is_text:
                # Zmienna z wartością
                var = tk.StringVar(value=self.ctx.settings[definition.key])
                # Pole edycji
                entry = tk.Entry(grid, textvariable=var, font=FONT, width=30)
                # Ułożenie
                entry.grid(row=row, column=1, sticky="w", padx=12)
                # Zapis po wciśnięciu Enter lub utracie fokusu
                save = lambda _e, k=definition.key, v=var: self.ctx.app_controller.set_setting(k, v.get())
                # Enter
                entry.bind("<Return>", save)
                # Utrata fokusu
                entry.bind("<FocusOut>", save)
            # Lista wyboru
            else:
                # Etykiety opcji
                labels = [option.label for option in definition.options]
                # Lista rozwijana
                combo = ttk.Combobox(grid, values=labels, state="readonly", font=FONT, width=30)
                # Bieżąca wartość
                combo.set(self.ctx.settings.label(definition.key))
                # Ułożenie
                combo.grid(row=row, column=1, sticky="w", padx=12)

                def changed(_e, d=definition, c=combo) -> None:
                    # Wartość odpowiadająca wybranej etykiecie
                    value = d.options[c.current()].value
                    # Zmiana przez kontroler
                    self.ctx.app_controller.set_setting(d.key, value)

                # Zdarzenie wyboru
                combo.bind("<<ComboboxSelected>>", changed)
            # Opis ustawienia
            self._label(grid, definition.description, ("Segoe UI", 10), fg=self.c["primary"]).grid(
                row=row, column=2, sticky="w", padx=12)
        # Powrót
        self._back_button(frame)
        # Esc – powrót
        self._key_handler = self._escape_goes_back

    def _build_ranking(self, frame: tk.Frame) -> None:
        """Ranking i statystyki."""
        # Tytuł
        self._title(frame, "Ranking i statystyki")
        # Zakładki
        notebook = ttk.Notebook(frame)
        # Ułożenie
        notebook.pack(fill="both", expand=True, padx=30)
        # Kolumny tabel
        columns = ("player", "amount", "answered", "time", "date")
        # Nagłówki kolumn
        headings = ("Gracz", "Wygrana", "Pytania", "Czas", "Data")
        # Dwie tabele: najlepsze i ostatnie
        for title, scores in (("Top 10", self.ctx.ranking.top(10)),
                              ("Historia gier", self.ctx.ranking.recent(30))):
            # Tabela
            tree = ttk.Treeview(notebook, columns=columns, show="headings")
            # Nagłówki
            for column, heading in zip(columns, headings):
                # Ustawienie nagłówka
                tree.heading(column, text=heading)
            # Wiersze
            for score in scores:
                # Dodanie wiersza
                tree.insert("", "end", values=(score.player, format_money(score.amount),
                                               f"{score.answered}/{score.total}",
                                               "∞" if score.time_limit == 0 else f"{score.time_limit} s",
                                               score.played_at.replace("T", " ")[:16]))
            # Zakładka z tabelą
            notebook.add(tree, text=title)
        # Statystyki
        stats = self.ctx.ranking.stats()
        # Tekst statystyk
        text = (f"Rozegrane gry: {stats.games}\nGry z wygraną: {stats.wins}\n"
                f"Najwyższa wygrana: {format_money(stats.best)}\n"
                f"Średnia wygrana: {format_money(round(stats.average))}\n"
                f"Łącznie wygrano: {format_money(stats.total)}")
        # Zakładka statystyk
        notebook.add(self._label(notebook, text, ("Segoe UI", 15), bg=self.c["surface"], justify="left"),
                     text="Statystyki")
        # Powrót
        self._back_button(frame)
        # Esc – powrót
        self._key_handler = self._escape_goes_back

    def _build_question_bank(self, frame: tk.Frame) -> None:
        """Baza pytań: lista kategorii, tabela pytań, formularz dodawania."""
        # Tytuł
        self._title(frame, "Baza pytań")
        # Część główna
        body = tk.Frame(frame, bg=self.c["bg"])
        # Ułożenie
        body.pack(fill="both", expand=True, padx=30)
        # Lista kategorii
        categories = tk.Listbox(body, font=FONT, bg=self.c["surface"], fg=self.c["fg"], width=28,
                                selectbackground=self.c["primary"], relief="flat", exportselection=False)
        # Ułożenie
        categories.pack(side="left", fill="y")
        # Tabela pytań
        tree = ttk.Treeview(body, columns=("d", "q", "a"), show="headings")
        # Nagłówek trudności
        tree.heading("d", text="Trudność")
        # Nagłówek pytania
        tree.heading("q", text="Pytanie")
        # Nagłówek odpowiedzi
        tree.heading("a", text="Poprawna odpowiedź")
        # Szerokość kolumny trudności
        tree.column("d", width=80, stretch=False)
        # Ułożenie
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0))
        # Pytania wyświetlane w tabeli (po identyfikatorze wiersza)
        shown: dict[str, Any] = {}

        def load_categories() -> None:
            # Wyczyszczenie listy
            categories.delete(0, "end")
            # Kategorie z modelu
            for name, count in self.ctx.bank.categories():
                # Dodanie pozycji
                categories.insert("end", f"{name} ({count})")

        def load_questions(_e=None) -> None:
            # Zaznaczona kategoria
            selection = categories.curselection()
            # Brak zaznaczenia
            if not selection:
                # Wyjście
                return
            # Nazwa kategorii (bez licznika)
            name = self.ctx.bank.categories()[selection[0]][0]
            # Wyczyszczenie tabeli
            tree.delete(*tree.get_children())
            # Wyczyszczenie mapy
            shown.clear()
            # Pytania kategorii
            for question in self.ctx.bank.in_category(name):
                # Wiersz tabeli
                row = tree.insert("", "end", values=("★" * question.difficulty, question.text, question.correct))
                # Zapamiętanie pytania
                shown[row] = question

        # Zmiana kategorii przeładowuje tabelę
        categories.bind("<<ListboxSelect>>", load_questions)
        # Formularz nowego pytania
        form = tk.Frame(frame, bg=self.c["bg"])
        # Ułożenie
        form.pack(fill="x", padx=30, pady=10)
        # Pola formularza
        fields = {}
        # Etykiety i klucze pól
        for column, (key, label) in enumerate((("category", "Kategoria"), ("text", "Pytanie"),
                                               ("correct", "Poprawna"), ("w1", "Błędna 1"),
                                               ("w2", "Błędna 2"), ("w3", "Błędna 3"))):
            # Etykieta pola
            self._label(form, label, ("Segoe UI", 10)).grid(row=0, column=column, sticky="w", padx=4)
            # Pole tekstowe (pytanie szersze)
            fields[key] = tk.Entry(form, font=FONT, width=34 if key == "text" else 14)
            # Ułożenie
            fields[key].grid(row=1, column=column, padx=4)

        def add() -> None:
            # Zapis przez kontroler (on waliduje)
            if self.ctx.app_controller.add_question(
                    fields["category"].get(), fields["text"].get(), fields["correct"].get(),
                    [fields["w1"].get(), fields["w2"].get(), fields["w3"].get()], 1):
                # Wyczyszczenie pól (poza kategorią)
                for key in ("text", "correct", "w1", "w2", "w3"):
                    # Wyczyszczenie
                    fields[key].delete(0, "end")

        def delete() -> None:
            # Zaznaczony wiersz
            selection = tree.selection()
            # Brak zaznaczenia
            if not selection:
                # Wyjście
                return
            # Potwierdzenie
            if messagebox.askyesno("Usunąć pytanie?", shown[selection[0]].text):
                # Usunięcie przez kontroler
                self.ctx.app_controller.delete_question(shown[selection[0]])

        # Przycisk dodawania
        self._button(form, "Dodaj", add, accent=True).grid(row=1, column=6, padx=8)
        # Przycisk usuwania
        self._button(form, "Usuń zaznaczone", delete).grid(row=1, column=7, padx=8)

        def on_bank(event: Event) -> None:
            # Zmiana w bazie – przeładowanie listy i tabeli
            if event.type is EventType.QUESTIONS_CHANGED:
                # Zaznaczona kategoria
                selection = categories.curselection()
                # Przeładowanie listy
                load_categories()
                # Przywrócenie zaznaczenia
                if selection:
                    # Zaznaczenie
                    categories.selection_set(selection[0])
                # Przeładowanie tabeli
                load_questions()

        # Subskrypcja zmian bazy
        self._observe(self.ctx.bank, on_bank)
        # Wczytanie kategorii
        load_categories()
        # Zaznaczenie pierwszej
        categories.selection_set(0)
        # Wczytanie pytań
        load_questions()
        # Powrót
        self._back_button(frame)
        # Esc – powrót
        self._key_handler = self._escape_goes_back

    def _build_summary(self, frame: tk.Frame) -> None:
        """Podsumowanie gry."""
        # Model gry
        game = self.ctx.game
        # Czy gracz coś wygrał
        won = game.bundles > 0
        # Nagłówek
        self._title(frame, "GRATULACJE! WYGRYWASZ" if won else "Tym razem się nie udało…")
        # Kwota
        self._label(frame, format_money(game.money), ("Segoe UI Black", 54),
                    fg=self.c["accent"] if won else self.c["error"]).pack()
        # Informacje
        self._label(frame, f"{game.player} · pytania {game.answered_rounds}/{game.total_rounds} · "
                           f"miejsce w rankingu: {self.ctx.game_controller.last_rank}", BOLD).pack(pady=8)
        # Tabela rund
        tree = ttk.Treeview(frame, columns=("n", "c", "q", "a", "m"), show="headings", height=8)
        # Nagłówki
        for column, heading in zip(("n", "c", "q", "a", "m"),
                                   ("Nr", "Kategoria", "Pytanie", "Poprawna", "Po rundzie")):
            # Ustawienie nagłówka
            tree.heading(column, text=heading)
        # Wąska kolumna numeru
        tree.column("n", width=40, stretch=False)
        # Wiersze rund
        for record in game.history:
            # Dodanie wiersza
            tree.insert("", "end", values=(record.number, record.category, record.question,
                                           record.answers[record.correct_index],
                                           format_money(bundles_to_money(record.bundles_after))))
        # Ułożenie
        tree.pack(fill="x", padx=40, pady=10)
        # Przyciski
        buttons = tk.Frame(frame, bg=self.c["bg"])
        # Ułożenie
        buttons.pack(pady=10)
        # Nowa gra
        self._button(buttons, "Zagraj ponownie (Enter)", self.ctx.app_controller.new_game,
                     accent=True).pack(side="left", padx=8)
        # Menu
        self._button(buttons, "Menu główne (Esc)", self.ctx.app_controller.back_to_menu).pack(side="left", padx=8)

        def on_key(event: tk.Event) -> None:
            # Enter – nowa gra
            if event.keysym == "Return":
                # Przez kontroler
                self.ctx.app_controller.new_game()
            # Esc – menu
            elif event.keysym == "Escape":
                # Przez kontroler
                self.ctx.app_controller.back_to_menu()

        # Obsługa klawiatury
        self._key_handler = on_key

    def _build_game(self, frame: tk.Frame) -> None:
        """Ekran gry – budowa i obsługa zdarzeń w klasie GameBoard."""
        # Plansza gry
        GameBoard(self, frame)


class GameBoard:
    """Plansza gry w wersji okienkowej. Odświeża tylko widżety, których dotyczy zdarzenie."""

    def __init__(self, view: GuiView, frame: tk.Frame) -> None:
        # Widok główny
        self.v = view
        # Paleta
        self.c = view.c
        # Model gry
        self.game = view.ctx.game
        # Kontroler gry
        self.ctrl = view.ctx.game_controller
        # Wybrana kolumna
        self.selected = 0
        # Wybrana kategoria
        self.category = 0
        # Kolumny odpowiedzi (słowniki widżetów)
        self.columns: list[dict] = []
        # Nagłówek
        header = tk.Frame(frame, bg=self.c["surface"])
        # Ułożenie
        header.pack(fill="x")
        # Numer pytania
        self.round_label = view._label(header, font=BOLD, bg=self.c["surface"])
        # Ułożenie
        self.round_label.pack(side="left", padx=20, pady=10)
        # Stan konta
        self.bank_label = view._label(header, font=BIG, fg=self.c["accent"], bg=self.c["surface"])
        # Ułożenie
        self.bank_label.pack(side="left", expand=True)
        # Zegar
        self.timer_label = view._label(header, font=BIG, bg=self.c["surface"], width=8)
        # Ułożenie
        self.timer_label.pack(side="right", padx=20)
        # Pasek czasu
        self.timer_bar = tk.Canvas(frame, height=8, bg=self.c["panel"], highlightthickness=0)
        # Ułożenie
        self.timer_bar.pack(fill="x")
        # Obszar zmienny (kategorie / plansza)
        self.body = tk.Frame(frame, bg=self.c["bg"])
        # Ułożenie
        self.body.pack(fill="both", expand=True)
        # Linia statusu
        self.status = view._label(frame, font=BOLD)
        # Ułożenie
        self.status.pack(pady=6)
        # Podpowiedź klawiszy
        view._label(frame, "←→ wybór · ↑↓ ±25 tys. · PgUp/PgDn ±250 tys. · A wszystko · "
                           "Backspace zdejmij · Enter zatwierdź · Spacja pomiń · P pauza · Esc przerwij",
                    ("Segoe UI", 10), fg=self.c["primary"]).pack(pady=(0, 8))
        # Subskrypcja zdarzeń modelu
        view._observe(self.game, self.on_event)
        # Obsługa klawiatury
        view._key_handler = self.on_key
        # Nagłówek
        self.update_header()
        # Zegar
        self.update_timer()
        # Stan początkowy (wybór kategorii)
        if self.game.phase is GamePhase.CATEGORY:
            # Karty kategorii
            self.show_categories()

    # ---------------------------------------------------------- zdarzenia

    def on_event(self, event: Event) -> None:
        """Reakcja na zdarzenia modelu – aktualizacja tylko powiązanych widżetów."""
        # Typ zdarzenia
        kind = event.type
        # Nowe kategorie
        if kind is EventType.CATEGORIES_OFFERED:
            # Karty kategorii
            self.show_categories()
        # Start rundy
        elif kind is EventType.ROUND_STARTED:
            # Plansza
            self.show_board()
        # Zmiana stawki – jedna kolumna i pula
        elif kind is EventType.BETS_CHANGED:
            # Odświeżenie kolumny
            self.draw_column(event.data["answer"])
            # Odświeżenie puli
            self.update_pool()
        # Zmiana sekundy – tylko zegar
        elif kind is EventType.TIME_CHANGED:
            # Odświeżenie zegara
            self.update_timer()
        # Zamknięcie zakładów
        elif kind is EventType.BETS_LOCKED:
            # Komunikat
            self.status.configure(text="Zakłady zamknięte – otwieramy zapadnie…  (Spacja – pomiń)",
                                  fg=self.c["primary"])
            # Odświeżenie konta i puli
            self.update_header()
            # Pula
            self.update_pool()
        # Otwarcie zapadni – animacja w jednej kolumnie
        elif kind is EventType.TRAPDOOR_OPENED:
            # Animacja
            self.open_trapdoor(event.data["answer"])
            # Konto
            self.update_header()
            # Dźwięk
            if self.v.ctx.settings["sound"]:
                # Sygnał
                self.v.bell()
        # Poprawna odpowiedź
        elif kind is EventType.CORRECT_REVEALED:
            # Podświetlenie kolumny
            self.mark_correct(event.data["answer"])
            # Konto
            self.update_header()
            # Komunikat końca rundy
            self.status.configure(text=self.round_over_text(), fg=self.c["accent"])
        # Złamanie zasad
        elif kind is EventType.RULE_VIOLATION:
            # Powiadomienie
            self.v.notify(event.data["message"], "warning")

    def round_over_text(self) -> str:
        """Komunikat po zakończeniu rundy."""
        # Przegrana
        if self.game.bundles == 0:
            # Tekst
            return "Niestety, wszystkie pieniądze spadły…  Enter – podsumowanie"
        # Ostatnie pytanie
        if not self.game.can_continue:
            # Tekst
            return f"BRAWO! Wygrywasz {format_money(self.game.money)}!  Enter – podsumowanie"
        # Kolejna runda
        return f"Zostaje Ci {format_money(self.game.money)}.  Enter – następne pytanie"

    # ------------------------------------------------------------ widoki

    def update_header(self) -> None:
        """Numer pytania i stan konta."""
        # Numer pytania
        self.round_label.configure(text=f"PYTANIE {self.game.round_number}/{self.game.total_rounds}\n"
                                        f"{self.game.answers_count} odpowiedzi")
        # Konto
        self.bank_label.configure(text=f"{self.game.player}: {format_money(self.game.money)}")

    def update_timer(self) -> None:
        """Zegar i pasek czasu."""
        # Brak limitu
        if self.game.time_limit <= 0:
            # Napis
            self.timer_label.configure(text="∞")
            # Wyjście
            return
        # Sekundy
        seconds = self.game.seconds_left if self.game.phase is GamePhase.BETTING else self.game.time_limit
        # Udział pozostałego czasu
        ratio = seconds / self.game.time_limit
        # Kolor zależny od czasu
        color = self.c["success"] if ratio > 0.34 else self.c["warning"] if seconds > 10 else self.c["error"]
        # Tekst zegara
        self.timer_label.configure(text=f"{seconds // 60}:{seconds % 60:02}", fg=color)
        # Wyczyszczenie paska
        self.timer_bar.delete("all")
        # Wypełniona część paska
        self.timer_bar.create_rectangle(0, 0, self.timer_bar.winfo_width() * ratio, 8, fill=color, width=0)

    def update_pool(self) -> None:
        """Pasek nierozłożonych pieniędzy."""
        # Nierozłożone paczki
        unplaced = self.game.unplaced
        # Faza odsłaniania
        if self.game.phase is not GamePhase.BETTING:
            # Informacja o stracie przez czas
            text = (f"Czas minął – przepadło {format_money(bundles_to_money(self.game.lost_unplaced))}"
                    if self.game.lost_unplaced else "Zakłady zamknięte")
            # Kolor
            color = self.c["error"] if self.game.lost_unplaced else self.c["primary"]
        # Wszystko rozłożone
        elif unplaced == 0:
            # Zachęta
            text, color = "✔ Wszystko rozłożone – Enter zamyka zakłady", self.c["success"]
        # Coś zostało
        else:
            # Kwota do rozłożenia
            text = f"Do rozłożenia: {unplaced} paczek = {format_money(bundles_to_money(unplaced))}"
            # Kolor
            color = self.c["warning"]
        # Aktualizacja etykiety
        self.pool.configure(text=text, fg=color)

    def clear_body(self) -> None:
        """Czyści obszar zmienny."""
        # Usunięcie wszystkich dzieci
        for child in self.body.winfo_children():
            # Zniszczenie widżetu
            child.destroy()

    def show_categories(self) -> None:
        """Wybór kategorii."""
        # Wyczyszczenie
        self.clear_body()
        # Brak kolumn
        self.columns = []
        # Pierwsza karta wybrana
        self.category = 0
        # Nagłówek
        self.update_header()
        # Zegar
        self.update_timer()
        # Tytuł
        self.v._label(self.body, "WYBIERZ KATEGORIĘ", BIG, fg=self.c["accent"]).pack(pady=(60, 30))
        # Rząd kart
        row = tk.Frame(self.body, bg=self.c["bg"])
        # Ułożenie
        row.pack()
        # Przyciski kategorii
        self.category_buttons = []
        # Każda kategoria
        for index, name in enumerate(self.game.category_options):
            # Duży przycisk kategorii
            button = self.v._button(row, f"\n{name.upper()}\n", lambda i=index: self.ctrl.choose_category(i),
                                    width=24)
            # Ułożenie
            button.pack(side="left", padx=20)
            # Zapamiętanie
            self.category_buttons.append(button)
        # Podświetlenie pierwszej
        self.highlight_category(0)
        # Status
        self.status.configure(text="←→ wybór kategorii · Enter zatwierdź", fg=self.c["fg"])

    def highlight_category(self, index: int) -> None:
        """Podświetla kartę kategorii."""
        # Indeks z zawijaniem
        self.category = index % len(self.category_buttons)
        # Każda karta
        for i, button in enumerate(self.category_buttons):
            # Wybrana – akcent, pozostałe – panel
            button.configure(bg=self.c["accent"] if i == self.category else self.c["panel"],
                             fg=self.c["bg"] if i == self.category else self.c["fg"])

    def show_board(self) -> None:
        """Plansza z kolumnami odpowiedzi."""
        # Wyczyszczenie
        self.clear_body()
        # Pytanie rundy
        question = self.game.current
        # Kategoria
        self.v._label(self.body, question.category.upper(), BOLD, fg=self.c["accent"]).pack(pady=(14, 0))
        # Treść pytania
        self.v._label(self.body, question.text, ("Segoe UI", 18, "bold"), wraplength=1000).pack(pady=(4, 8))
        # Pasek puli
        self.pool = self.v._label(self.body, font=BOLD)
        # Ułożenie
        self.pool.pack()
        # Rząd kolumn
        row = tk.Frame(self.body, bg=self.c["bg"])
        # Ułożenie
        row.pack(fill="both", expand=True, padx=20, pady=10)
        # Jedyny wiersz siatki rozciąga się w pionie
        row.rowconfigure(0, weight=1)
        # Kolumny
        self.columns = []
        # Każda odpowiedź
        for index, answer in enumerate(question.answers):
            # Ramka kolumny
            box = tk.Frame(row, bg=self.c["surface"], highlightthickness=3,
                           highlightbackground=self.c["panel"])
            # Kolumny siatki o równej szerokości (mieszczą się w oknie)
            row.columnconfigure(index, weight=1, uniform="answers")
            # Ułożenie w siatce
            box.grid(row=0, column=index, sticky="nsew", padx=8)
            # Litera
            letter = self.v._label(box, ANSWER_LETTERS[index], BIG, fg=self.c["primary"], bg=self.c["surface"])
            # Ułożenie
            letter.pack()
            # Treść odpowiedzi
            self.v._label(box, answer, BOLD, bg=self.c["surface"], wraplength=180).pack()
            # Płótno na stos paczek i zapadnię
            canvas = tk.Canvas(box, height=200, bg=self.c["surface"], highlightthickness=0)
            # Ułożenie
            canvas.pack(fill="both", expand=True, pady=6)
            # Kwota
            amount = self.v._label(box, font=BOLD, bg=self.c["surface"])
            # Ułożenie
            amount.pack()
            # Przyciski +/- i „wszystko”
            buttons = tk.Frame(box, bg=self.c["surface"])
            # Ułożenie
            buttons.pack(pady=6)
            # Zdjęcie paczki
            self.v._button(buttons, "−", lambda i=index: self.ctrl.remove(i), padx=10).pack(side="left", padx=2)
            # Dołożenie paczki
            self.v._button(buttons, "+", lambda i=index: self.ctrl.add(i), padx=10).pack(side="left", padx=2)
            # Wszystko tutaj
            self.v._button(buttons, "Wszystko", lambda i=index: self.ctrl.all_in(i), padx=8).pack(side="left", padx=2)
            # Kliknięcie kolumny wybiera ją
            for widget in (box, canvas, letter):
                # Zdarzenie kliknięcia
                widget.bind("<Button-1>", lambda _e, i=index: self.select(i))
            # Kółko myszy dokłada/zdejmuje paczki
            canvas.bind("<MouseWheel>", lambda e, i=index: self.ctrl.add(i) if e.delta > 0 else self.ctrl.remove(i))
            # Zapamiętanie widżetów kolumny
            self.columns.append(dict(box=box, canvas=canvas, amount=amount, letter=letter, state="closed"))
            # Rysowanie po ustaleniu rozmiaru płótna
            canvas.bind("<Configure>", lambda _e, i=index: self.draw_column(i))
        # Przycisk zatwierdzenia
        self.v._button(self.body, "Zamknij zakłady (Enter)", self.ctrl.lock, accent=True).pack(pady=4)
        # Poprzednia runda mogła mieć więcej kolumn – zaczynamy od pierwszej
        self.selected = 0
        # Wybór pierwszej kolumny
        self.select(0)
        # Pula
        self.update_pool()
        # Status
        self.status.configure(text="Rozłóż wszystkie pieniądze – co najmniej jedna zapadnia musi zostać pusta!",
                              fg=self.c["warning"])
        # Zegar
        self.update_timer()

    def select(self, index: int) -> None:
        """Wybiera kolumnę – zmienia ramkę tylko dwóch kolumn."""
        # Brak kolumn
        if not self.columns:
            # Wyjście
            return
        # Odznaczenie poprzedniej
        self.columns[self.selected]["box"].configure(highlightbackground=self.c["panel"])
        # Nowy indeks z zawijaniem
        self.selected = index % len(self.columns)
        # Zaznaczenie nowej
        self.columns[self.selected]["box"].configure(highlightbackground=self.c["accent"])

    def draw_column(self, index: int, offset: int = 0) -> None:
        """Rysuje stos paczek i zapadnię jednej kolumny."""
        # Widżety kolumny
        column = self.columns[index]
        # Płótno
        canvas = column["canvas"]
        # Wymiary płótna
        width, height = canvas.winfo_width(), canvas.winfo_height()
        # Wyczyszczenie płótna
        canvas.delete("all")
        # Stan zapadni
        state = column["state"]
        # Liczba paczek do narysowania
        bundles = self.game.bets[index] if state != "opened" else 0
        # Kolor paczek
        color = self.c["success"] if state == "correct" else self.c["error"] if offset else self.c["accent"]
        # Wymiary cegiełki
        brick_w, brick_h = max(6, (width - 40) // 10), 12
        # Każda paczka
        for n in range(bundles):
            # Rząd i kolumna cegiełki
            row, col = divmod(n, 10)
            # Lewy górny róg
            x = 20 + col * brick_w
            # Pozycja pionowa (od dołu, z przesunięciem przy spadaniu)
            y = height - 20 - (row + 1) * (brick_h + 2) + offset
            # Cegiełka
            canvas.create_rectangle(x, y, x + brick_w - 2, y + brick_h, fill=color, width=0)
        # Kolor zapadni
        door = self.c["error"] if state == "opened" else self.c["success"] if state == "correct" else self.c["primary"]
        # Zapadnia zamknięta – pełna klapa
        if state != "opened":
            # Linia klapy
            canvas.create_line(10, height - 8, width - 10, height - 8, fill=door, width=6)
        # Zapadnia otwarta – opadnięte skrzydła
        else:
            # Lewe skrzydło
            canvas.create_line(10, height - 8, 30, height, fill=door, width=6)
            # Prawe skrzydło
            canvas.create_line(width - 10, height - 8, width - 30, height, fill=door, width=6)
        # Kwota pod kolumną
        column["amount"].configure(text=format_money(bundles_to_money(self.game.bets[index])),
                                   fg=self.c["error"] if state == "opened" else self.c["accent"])

    def open_trapdoor(self, index: int) -> None:
        """Animacja spadających paczek w jednej kolumnie."""
        # Widżety kolumny
        column = self.columns[index]
        # Ramka w kolorze błędu
        column["box"].configure(highlightbackground=self.c["error"])
        # Litera w kolorze błędu
        column["letter"].configure(fg=self.c["error"])
        # Liczba klatek (bez animacji – od razu koniec)
        frames = 0 if self.v.ctx.settings["animation"] == "off" else 10

        def step(frame: int) -> None:
            # Kolumna mogła zniknąć (np. koniec gry)
            if not column["canvas"].winfo_exists():
                # Wyjście
                return
            # Ostatnia klatka – zapadnia otwarta
            if frame >= frames:
                # Stan końcowy
                column["state"] = "opened"
                # Narysowanie
                self.draw_column(index)
                # Wyjście
                return
            # Rysowanie z przesunięciem w dół
            self.draw_column(index, offset=frame * 14)
            # Następna klatka
            self.v.root.after(35, step, frame + 1)

        # Start animacji
        step(0)

    def mark_correct(self, index: int) -> None:
        """Podświetla poprawną odpowiedź."""
        # Widżety kolumny
        column = self.columns[index]
        # Stan
        column["state"] = "correct"
        # Zielona ramka
        column["box"].configure(highlightbackground=self.c["success"])
        # Zielona litera
        column["letter"].configure(fg=self.c["success"], text=f"{ANSWER_LETTERS[index]} ✔")
        # Narysowanie
        self.draw_column(index)

    # ------------------------------------------------------------ klawiatura

    def on_key(self, event: tk.Event) -> None:
        """Sterowanie klawiaturą – te same skróty co w wersji tekstowej."""
        # Nazwa klawisza
        key = event.keysym
        # Faza gry
        phase = self.game.phase
        # Przerwanie gry
        if key == "Escape":
            # Wstrzymanie zegara
            self.ctrl.set_paused(True)
            # Pytanie o potwierdzenie
            if messagebox.askyesno("Przerwać grę?", "Wynik tej gry nie zostanie zapisany."):
                # Przerwanie
                self.ctrl.abandon()
            # Rezygnacja
            else:
                # Wznowienie
                self.ctrl.set_paused(False)
        # Wybór kategorii
        elif phase is GamePhase.CATEGORY:
            # Strzałki
            if key in ("Left", "Right"):
                # Zmiana karty
                self.highlight_category(self.category + (1 if key == "Right" else -1))
            # Zatwierdzenie
            elif key == "Return":
                # Przez kontroler
                self.ctrl.choose_category(self.category)
            # Klawisze 1/2
            elif key in ("1", "2"):
                # Przez kontroler
                self.ctrl.choose_category(int(key) - 1)
        # Rozkładanie pieniędzy
        elif phase is GamePhase.BETTING:
            # Mapowanie klawiszy na akcje
            actions = {
                # Poprzednia kolumna
                "Left": lambda: self.select(self.selected - 1),
                # Następna kolumna
                "Right": lambda: self.select(self.selected + 1),
                # Dołożenie paczki
                "Up": lambda: self.ctrl.add(self.selected),
                # Zdjęcie paczki
                "Down": lambda: self.ctrl.remove(self.selected),
                # Dołożenie 10 paczek
                "Prior": lambda: self.ctrl.add(self.selected, 10),
                # Zdjęcie 10 paczek
                "Next": lambda: self.ctrl.remove(self.selected, 10),
                # Wszystko na wybraną
                "a": lambda: self.ctrl.all_in(self.selected),
                # Wyczyszczenie wybranej
                "BackSpace": lambda: self.ctrl.clear_answer(self.selected),
                # Wyczyszczenie wszystkich
                "r": self.ctrl.clear_all,
                # Zamknięcie zakładów
                "Return": self.ctrl.lock,
                # Pauza
                "p": self.pause,
            }
            # Wybór kolumny cyfrą
            if key in ("1", "2", "3", "4"):
                # Zaznaczenie (jeśli kolumna istnieje)
                if int(key) <= len(self.columns):
                    # Wybór
                    self.select(int(key) - 1)
            # Pozostałe akcje
            elif key in actions:
                # Wykonanie akcji
                actions[key]()
        # Odsłanianie – pominięcie animacji
        elif phase is GamePhase.REVEAL and key in ("space", "Return"):
            # Przez kontroler
            self.ctrl.skip_reveal()
        # Koniec rundy – dalej
        elif phase is GamePhase.ROUND_OVER and key == "Return":
            # Przez kontroler
            self.ctrl.continue_game()

    def pause(self) -> None:
        """Pauza – okno informacyjne wstrzymuje zegar."""
        # Wstrzymanie zegara
        self.ctrl.set_paused(True)
        # Okno modalne
        messagebox.showinfo("Pauza", "Gra wstrzymana. Kliknij OK, aby wrócić.")
        # Wznowienie
        self.ctrl.set_paused(False)
