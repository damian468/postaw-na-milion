"""Edytor bazy pytań (SQLite): przeglądanie, dodawanie i usuwanie pytań."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, OptionList, Select, Static
from textual.widgets.option_list import Option

# Escapowanie znaków markupu w tekstach z bazy
from rich.markup import escape
# Zdarzenia
from pnm.model.observable import Event, EventType
# Ikony kategorii
from pnm.view.tui.ascii_art import category_icon
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Okno potwierdzenia
from pnm.view.tui.screens.dialogs import ConfirmDialog
# Widżety
from pnm.view.tui.widgets import TrackedStatic

# Opisy poziomów trudności
DIFFICULTY_LABELS = {1: "★☆☆ łatwe", 2: "★★☆ średnie", 3: "★★★ trudne"}


class QuestionForm(ModalScreen[bool]):
    """Formularz nowego pytania."""

    # Skróty klawiszowe
    BINDINGS = [
        # Zapis
        Binding("ctrl+s", "save", "Zapisz"),
        # Anulowanie
        Binding("escape", "cancel", "Anuluj"),
    ]

    def __init__(self, ctx, category: str) -> None:
        # Konstruktor Textual
        super().__init__()
        # Kontekst aplikacji
        self.ctx = ctx
        # Domyślna kategoria
        self._category = category

    def compose(self):
        # Ramka formularza
        with Vertical(classes="dialog form"):
            # Tytuł
            yield Static("NOWE PYTANIE", classes="dialog-title")
            # Kategoria
            yield Input(self._category, placeholder="Kategoria", id="f-category")
            # Treść pytania
            yield Input(placeholder="Treść pytania", id="f-text")
            # Poprawna odpowiedź
            yield Input(placeholder="✔ Poprawna odpowiedź", id="f-correct")
            # Błędna odpowiedź 1
            yield Input(placeholder="✖ Błędna odpowiedź 1", id="f-wrong1")
            # Błędna odpowiedź 2
            yield Input(placeholder="✖ Błędna odpowiedź 2", id="f-wrong2")
            # Błędna odpowiedź 3
            yield Input(placeholder="✖ Błędna odpowiedź 3", id="f-wrong3")
            # Trudność
            yield Select([(label, value) for value, label in DIFFICULTY_LABELS.items()],
                         value=1, allow_blank=False, id="f-difficulty")
            # Przyciski
            with Horizontal(classes="dialog-buttons"):
                # Zapis
                yield Button("Zapisz [Ctrl+S]", variant="success", id="save")
                # Anulowanie
                yield Button("Anuluj [Esc]", variant="primary", id="cancel")

    def on_mount(self) -> None:
        # Fokus na treść pytania
        self.query_one("#f-text").focus()

    def _value(self, widget_id: str) -> str:
        """Tekst z pola formularza."""
        # Odczyt wartości pola
        return self.query_one(f"#{widget_id}", Input).value

    def action_save(self) -> None:
        # Zapis przez kontroler (on waliduje i pokazuje błędy)
        saved = self.ctx.app_controller.add_question(
            # Kategoria
            self._value("f-category"),
            # Treść
            self._value("f-text"),
            # Poprawna odpowiedź
            self._value("f-correct"),
            # Błędne odpowiedzi
            [self._value("f-wrong1"), self._value("f-wrong2"), self._value("f-wrong3")],
            # Trudność
            self.query_one("#f-difficulty", Select).value,
        )
        # Sukces – zamknięcie formularza
        if saved:
            # Zwrot wyniku
            self.dismiss(True)

    def action_cancel(self) -> None:
        # Zamknięcie bez zapisu
        self.dismiss(False)

    def on_input_submitted(self) -> None:
        # Enter w polu – przejście do następnego pola
        self.focus_next()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Zapis lub anulowanie wg przycisku
        if event.button.id == "save":
            # Zapis
            self.action_save()
        # Anulowanie
        else:
            # Zamknięcie
            self.action_cancel()


class QuestionBankScreen(BaseScreen):
    """Przeglądarka bazy pytań."""

    # Skróty klawiszowe
    BINDINGS = [
        # Nowe pytanie
        Binding("n", "new", "Nowe pytanie"),
        # Usunięcie pytania
        Binding("delete,d", "delete", "Usuń", key_display="Del"),
        # Przejście między listą a tabelą
        Binding("tab", "app.focus_next", "Lista/Tabela", key_display="Tab"),
        # Powrót
        Binding("escape", "back", "Wróć"),
    ]

    def compose_content(self):
        # Kolumna ekranu
        with Vertical(id="bank"):
            # Tytuł
            yield Static("[b]▤  BAZA PYTAŃ[/b]", classes="screen-title")
            # Lista kategorii i tabela pytań
            with Horizontal(id="bank-body"):
                # Kategorie
                yield OptionList(id="bank-categories")
                # Prawa część
                with Vertical(id="bank-right"):
                    # Tabela pytań
                    yield DataTable(id="bank-table", cursor_type="row", zebra_stripes=True)
                    # Szczegóły zaznaczonego pytania
                    yield TrackedStatic(id="bank-detail", diag_label="Szczegóły pytania")

    def on_mount(self) -> None:
        # Kategorie w kolejności listy
        self._categories: list[str] = []
        # Pytania wyświetlane w tabeli (po identyfikatorze)
        self._questions: dict[str, object] = {}
        # Kolumny tabeli
        self.query_one(DataTable).add_columns("Trudność", "Pytanie", "Poprawna odpowiedź")
        # Wczytanie kategorii
        self._load_categories()
        # Zmiany w bazie przeładowują widok
        self.observe(self.ctx.bank, self._on_bank)
        # Fokus na listę kategorii
        self.query_one(OptionList).focus()

    def _on_bank(self, event: Event) -> None:
        # Tylko zmiany pytań
        if event.type is EventType.QUESTIONS_CHANGED:
            # Przeładowanie z zachowaniem kategorii
            self._load_categories(event.data.get("category"))

    def _load_categories(self, keep: str | None = None) -> None:
        """Wczytuje listę kategorii z liczbą pytań."""
        # Lista kategorii
        options = self.query_one(OptionList)
        # Kategoria do zaznaczenia po przeładowaniu
        keep = keep or self._current_category()
        # Kategorie z modelu
        categories = self.ctx.bank.categories()
        # Zapamiętanie nazw
        self._categories = [name for name, _ in categories]
        # Wyczyszczenie listy
        options.clear_options()
        # Dodanie opcji
        options.add_options([Option(f"{category_icon(name)}  {escape(name)}  [dim]({count})[/dim]")
                             for name, count in categories])
        # Brak kategorii
        if not self._categories:
            # Pusta tabela
            self._load_questions(None)
            # Wyjście
            return
        # Zaznaczenie zachowanej kategorii lub pierwszej
        options.highlighted = self._categories.index(keep) if keep in self._categories else 0
        # Wczytanie pytań
        self._load_questions(self._categories[options.highlighted])

    def _current_category(self) -> str | None:
        """Nazwa zaznaczonej kategorii."""
        # Indeks zaznaczenia
        index = self.query_one(OptionList).highlighted
        # Nazwa lub None
        return self._categories[index] if index is not None and index < len(self._categories) else None

    def _load_questions(self, category: str | None) -> None:
        """Wypełnia tabelę pytaniami kategorii."""
        # Tabela
        table = self.query_one(DataTable)
        # Wyczyszczenie wierszy
        table.clear()
        # Wyczyszczenie mapy pytań
        self._questions = {}
        # Bez kategorii – pusto
        if category is None:
            # Pusty opis
            self.query_one("#bank-detail", TrackedStatic).update("Baza jest pusta – dodaj pytanie [b]N[/b].")
            # Wyjście
            return
        # Pytania kategorii
        for question in self.ctx.bank.in_category(category):
            # Klucz wiersza
            key = str(question.id)
            # Zapamiętanie pytania
            self._questions[key] = question
            # Wiersz tabeli
            table.add_row(DIFFICULTY_LABELS.get(question.difficulty, "?"),
                          question.text[:50] + ("…" if len(question.text) > 50 else ""),
                          question.correct, key=key)
        # Szczegóły pierwszego pytania
        self._show_detail(next(iter(self._questions.values()), None))

    def _show_detail(self, question) -> None:
        """Pokazuje pełną treść pytania z odpowiedziami."""
        # Panel szczegółów
        detail = self.query_one("#bank-detail", TrackedStatic)
        # Brak pytania
        if question is None:
            # Pusty panel
            detail.update("")
            # Wyjście
            return
        # Błędne odpowiedzi w jednej linii
        wrong = "   ".join(f"[$error]✖ {escape(w)}[/]" for w in question.wrong)
        # Oznaczenie pytań dodanych przez użytkownika
        origin = "  [dim](dodane przez Ciebie)[/dim]" if question.source == "user" else ""
        # Treść panelu
        detail.update(f"[b]{escape(question.text)}[/b]{origin}\n[$success]✔ {escape(question.correct)}[/]   {wrong}")

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        # Zmiana kategorii – przeładowanie tabeli
        if event.option_index < len(self._categories):
            # Pytania wybranej kategorii
            self._load_questions(self._categories[event.option_index])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # Szczegóły zaznaczonego pytania
        self._show_detail(self._questions.get(event.row_key.value))

    def _selected_question(self):
        """Pytanie zaznaczone w tabeli."""
        # Tabela
        table = self.query_one(DataTable)
        # Pusta tabela
        if not self._questions or table.cursor_row is None:
            # Brak pytania
            return None
        # Klucz zaznaczonego wiersza
        key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
        # Pytanie
        return self._questions.get(key)

    def action_new(self) -> None:
        # Formularz z bieżącą kategorią
        self.app.push_screen(QuestionForm(self.ctx, self._current_category() or ""))

    def action_delete(self) -> None:
        # Zaznaczone pytanie
        question = self._selected_question()
        # Brak pytania
        if question is None:
            # Wyjście
            return

        def answer(confirmed: bool) -> None:
            # Potwierdzono
            if confirmed:
                # Usunięcie przez kontroler
                self.ctx.app_controller.delete_question(question)

        # Okno potwierdzenia
        self.app.push_screen(ConfirmDialog("Usunąć pytanie?", question.text), answer)

    def action_back(self) -> None:
        # Powrót do menu
        self.ctx.app_controller.back_to_menu()
