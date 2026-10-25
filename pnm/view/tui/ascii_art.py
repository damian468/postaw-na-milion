"""Grafika ASCII: duża czcionka blokowa, logo i ikony kategorii."""

# Czcionka 5x5 – „#” oznacza zapalony piksel
FONT: dict[str, list[str]] = {
    # Litera A
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    # Litera C
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    # Litera E
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    # Litera G
    "G": [" ####", "#    ", "#  ##", "#   #", " ### "],
    # Litera I (węższa)
    "I": ["###", " # ", " # ", " # ", "###"],
    # Litera K
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    # Litera L
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    # Litera Ł
    "Ł": ["#    ", "# #  ", "##   ", "#    ", "#####"],
    # Litera M
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    # Litera N
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    # Litera O
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    # Litera P
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    # Litera R
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    # Litera S
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    # Litera T
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    # Litera W
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    # Litera Y
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    # Litera Z
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    # Cyfra 0
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    # Cyfra 1
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    # Cyfra 2
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"],
    # Cyfra 3
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    # Cyfra 4
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    # Cyfra 5
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    # Cyfra 6
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    # Cyfra 7
    "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    # Cyfra 8
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    # Cyfra 9
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    # Dwukropek (zegar)
    ":": [" ", "#", " ", "#", " "],
    # Wykrzyknik
    "!": ["#", "#", "#", " ", "#"],
    # Spacja (węższa – separator tysięcy)
    " ": ["  ", "  ", "  ", "  ", "  "],
}

# Zamiana pary pikseli (góra, dół) na znak półbloku – czcionka o połowę niższa
HALF_BLOCKS = {
    # Oba piksele zapalone
    (True, True): "█",
    # Tylko górny
    (True, False): "▀",
    # Tylko dolny
    (False, True): "▄",
    # Żaden
    (False, False): " ",
}


def big_text(text: str, compact: bool = False) -> list[str]:
    """Zamienia tekst na linie dużej czcionki (5 linii lub 3 w trybie kompaktowym)."""
    # Pięć pustych wierszy wyniku
    rows = ["", "", "", "", ""]
    # Każdy znak tekstu
    for char in text.upper():
        # Glif znaku (nieznane znaki jako spacja)
        glyph = FONT.get(char, FONT[" "])
        # Doklejamy wiersze glifu z odstępem jednej kolumny
        for index in range(5):
            # Wiersz glifu + przerwa
            rows[index] += glyph[index] + " "
    # Usuwamy ostatnią przerwę z każdego wiersza
    rows = [row[:-1] for row in rows]
    # Tryb pełny – każdy piksel to pełny blok
    if not compact:
        # Zamiana „#” na „█”
        return [row.replace("#", "█") for row in rows]
    # Tryb kompaktowy – dokładamy pusty szósty wiersz do pary
    rows.append(" " * len(rows[0]))
    # Wynik w trzech liniach
    result = []
    # Łączymy wiersze parami (0+1, 2+3, 4+5)
    for top, bottom in zip(rows[0::2], rows[1::2]):
        # Każda kolumna pary to jeden znak półbloku
        result.append("".join(HALF_BLOCKS[(t == "#", b == "#")] for t, b in zip(top, bottom)))
    # Zwracamy trzy linie
    return result


# Linie logo (dwie linijki tekstu)
LOGO_WORDS = ("POSTAW NA", "MILION")

# Ikony kategorii (pojedyncze znaki Unicode o szerokości 1)
CATEGORY_ICONS = {
    # Historia – wieża
    "Historia": "♜",
    # Geografia – kula ziemska
    "Geografia": "◎",
    # Nauka – suma
    "Nauka": "∑",
    # Sport – piłka
    "Sport": "◉",
    # Literatura – pióro
    "Literatura i sztuka": "✎",
    # Film i muzyka – nuty
    "Film i muzyka": "♫",
    # Przyroda – kwiat
    "Przyroda": "❀",
    # Polska – korona
    "Polska": "♛",
    # Technologia – klawisz
    "Technologia": "⌘",
    # Rozmaitości – gwiazdka
    "Rozmaitości": "✦",
}


def category_icon(name: str) -> str:
    """Ikona kategorii (gwiazdka dla nieznanych)."""
    # Odczyt z tabeli z wartością domyślną
    return CATEGORY_ICONS.get(name, "★")


# Ilustracja zapadni do ekranu zasad
TRAPDOOR_ART = r"""
     ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
     │    A     │   │    B     │   │    C     │   │    D     │
     │  ▆▆▆▆▆▆  │   │          │   │  ▆▆▆▆    │   │          │
     │  ▆▆▆▆▆▆  │   │          │   │  ▆▆▆▆    │   │          │
     ▀▀▀▀▀▀▀▀▀▀▀▀   ▀▀▀▘  ▝▀▀▀   ▀▀▀▀▀▀▀▀▀▀▀▀   ▀▀▀▘  ▝▀▀▀
                       ▆  ▆                         (pusta)
                     ▆   ▆  ▆
"""
