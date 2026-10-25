"""Ranking: najlepsze wyniki, historia gier i statystyki (dane z bazy SQLite)."""

# Klasy Textual
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static, TabbedContent, TabPane

# Formatowanie kwot
from pnm.config import format_money
# Zdarzenia
from pnm.model.observable import Event, EventType
# Ekran bazowy
from pnm.view.tui.screens.base import BaseScreen
# Okno potwierdzenia
from pnm.view.tui.screens.dialogs import ConfirmDialog
# Widżety
from pnm.view.tui.widgets import TrackedStatic

# Medale dla podium
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

# Nazwy źródeł pytań
SOURCES = {"local": "lokalne", "online": "Internet", "mixed": "mieszane"}


class RankingScreen(BaseScreen):
    """Ranking i statystyki."""

    # Skróty klawiszowe
    BINDINGS = [
        # Zakładka 1
        Binding("1", "tab('top')", "Top 10"),
        # Zakładka 2
        Binding("2", "tab('recent')", "Historia"),
        # Zakładka 3
        Binding("3", "tab('stats')", "Statystyki"),
        # Wyczyszczenie rankingu
        Binding("c", "clear", "Wyczyść"),
        # Powrót
        Binding("escape", "back", "Wróć"),
    ]

    def compose_content(self):
        # Kolumna ekranu
        with Vertical(id="ranking"):
            # Tytuł
            yield Static("[b]🏆  RANKING I STATYSTYKI[/b]", classes="screen-title")
            # Zakładki
            with TabbedContent(id="ranking-tabs"):
                # Najlepsze wyniki
                with TabPane("Top 10", id="top"):
                    # Tabela
                    yield DataTable(id="top-table", cursor_type="row", zebra_stripes=True)
                # Ostatnie gry
                with TabPane("Historia gier", id="recent"):
                    # Tabela
                    yield DataTable(id="recent-table", cursor_type="row", zebra_stripes=True)
                # Statystyki
                with TabPane("Statystyki", id="stats"):
                    # Tekst statystyk
                    yield TrackedStatic(id="stats-text", diag_label="Statystyki")

    def on_mount(self) -> None:
        # Kolumny tabeli najlepszych
        self.query_one("#top-table", DataTable).add_columns(
            "Miejsce", "Gracz", "Wygrana", "Pytania", "Czas", "Źródło", "Data")
        # Kolumny tabeli historii
        self.query_one("#recent-table", DataTable).add_columns(
            "Data", "Gracz", "Wygrana", "Pytania", "Czas", "Źródło")
        # Wypełnienie danymi
        self._reload()
        # Zmiany rankingu przeładowują tabele
        self.observe(self.ctx.ranking, self._on_ranking)
        # Fokus na pierwszą tabelę
        self.query_one("#top-table").focus()

    def _on_ranking(self, event: Event) -> None:
        # Tylko zmiany wyników
        if event.type is EventType.SCORES_CHANGED:
            # Przeładowanie
            self._reload()

    @staticmethod
    def _time_label(limit: int) -> str:
        """Opis limitu czasu."""
        # Bez limitu lub w sekundach
        return "∞" if limit == 0 else f"{limit} s"

    def _reload(self) -> None:
        """Wczytuje dane z modelu do tabel."""
        # Tabela najlepszych
        top = self.query_one("#top-table", DataTable)
        # Wyczyszczenie wierszy
        top.clear()
        # Wiersze najlepszych wyników
        for place, score in enumerate(self.ctx.ranking.top(10), start=1):
            # Wiersz
            top.add_row(f"{MEDALS.get(place, '  ')} {place}.", score.player,
                        format_money(score.amount), f"{score.answered}/{score.total}",
                        self._time_label(score.time_limit), SOURCES.get(score.source, score.source),
                        score.played_at.replace("T", " ")[:16])
        # Tabela historii
        recent = self.query_one("#recent-table", DataTable)
        # Wyczyszczenie wierszy
        recent.clear()
        # Wiersze ostatnich gier
        for score in self.ctx.ranking.recent(30):
            # Wiersz
            recent.add_row(score.played_at.replace("T", " ")[:16], score.player,
                           format_money(score.amount), f"{score.answered}/{score.total}",
                           self._time_label(score.time_limit), SOURCES.get(score.source, score.source))
        # Statystyki
        stats = self.ctx.ranking.stats()
        # Procent gier z wygraną
        win_rate = 100 * stats.wins / stats.games if stats.games else 0
        # Lista najaktywniejszych graczy
        players = "\n".join(f"   {name:<18}{count:>4} gier" for name, count in stats.top_players)
        # Tekst statystyk
        self.query_one("#stats-text", TrackedStatic).update(
            f"[b]Rozegrane gry:[/b]           {stats.games}\n"
            f"[b]Gry z wygraną:[/b]           {stats.wins}  ({win_rate:.0f}%)\n"
            f"[b]Najwyższa wygrana:[/b]       [b $accent]{format_money(stats.best)}[/]\n"
            f"[b]Średnia wygrana:[/b]         {format_money(round(stats.average))}\n"
            f"[b]Łącznie wygrano:[/b]         {format_money(stats.total)}\n\n"
            f"[b]Najaktywniejsi gracze:[/b]\n{players or '   (brak gier)'}")

    def action_tab(self, tab: str) -> None:
        # Przełączenie zakładki
        self.query_one(TabbedContent).active = tab

    def action_clear(self) -> None:
        # Odpowiedź z okna potwierdzenia
        def answer(confirmed: bool) -> None:
            # Potwierdzono
            if confirmed:
                # Przez kontroler
                self.ctx.app_controller.clear_ranking()

        # Okno potwierdzenia
        self.app.push_screen(ConfirmDialog("Wyczyścić ranking?",
                                           "Wszystkie zapisane wyniki zostaną usunięte."), answer)

    def action_back(self) -> None:
        # Powrót do menu
        self.ctx.app_controller.back_to_menu()
