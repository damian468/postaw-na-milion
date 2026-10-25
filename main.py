"""Punkt wejścia gry „Postaw na milion”.

Uruchomienie:
    python main.py          – wersja tekstowa (terminal, Textual)
    python main.py --gui    – wersja graficzna (okno, tkinter) – ten sam model i kontroler
"""

# argparse – obsługa parametrów wiersza poleceń
import argparse
# sys – kod wyjścia
import sys

# Złożenie modeli i kontrolerów
from pnm.context import build_context


def main() -> int:
    """Buduje aplikację i uruchamia wybrany widok."""
    # Opis parametrów
    parser = argparse.ArgumentParser(description="Teleturniej „Postaw na milion”")
    # Przełącznik wersji graficznej
    parser.add_argument("--gui", action="store_true", help="uruchom w trybie graficznym (tkinter)")
    # Odczyt parametrów
    args = parser.parse_args()
    # Modele i kontrolery – identyczne dla obu widoków
    ctx = build_context()
    # Wybór widoku
    if args.gui:
        # Import widoku graficznego dopiero gdy potrzebny
        from pnm.view.gui.app import GuiView
        # Widok graficzny
        view = GuiView(ctx)
    # Domyślnie widok tekstowy
    else:
        # Import widoku tekstowego
        from pnm.view.tui.app import TuiView
        # Widok tekstowy
        view = TuiView(ctx)
    # Podłączenie widoku do kontrolera
    ctx.app_controller.attach_view(view)
    # Start pętli zdarzeń
    view.run()
    # Kod wyjścia „sukces”
    return 0


# Uruchomienie tylko przy wywołaniu pliku bezpośrednio
if __name__ == "__main__":
    # Wyjście z kodem zwróconym przez main
    sys.exit(main())
