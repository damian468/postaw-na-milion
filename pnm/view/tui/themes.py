"""Motywy kolorystyczne widoku tekstowego (rejestrowane w Textual)."""

# Klasa motywu z biblioteki Textual
from textual.theme import Theme

# Lista motywów – nazwy odpowiadają wartościom ustawienia „theme”
THEMES: tuple[Theme, ...] = (
    # Ciemnoniebieskie studio z zielonym światłem zapadni i złotymi banknotami
    Theme(
        # Nazwa motywu
        name="studio",
        # Kolor główny (niebieski reflektor)
        primary="#2FA4FF",
        # Kolor drugorzędny
        secondary="#1B5FBF",
        # Akcent – złoto banknotów
        accent="#FFC83D",
        # Ostrzeżenia
        warning="#FFB020",
        # Błędy / otwarte zapadnie
        error="#FF4D5E",
        # Sukces / poprawna odpowiedź
        success="#3DDC84",
        # Tło aplikacji
        background="#05070F",
        # Tło paneli
        surface="#0B1226",
        # Tło wyróżnionych paneli
        panel="#13203F",
        # Kolor tekstu
        foreground="#E6EEFF",
        # Ciemny motyw
        dark=True,
    ),
    # Fioletowo-różowy neon
    Theme(
        # Nazwa motywu
        name="neon",
        # Róż
        primary="#FF2BD6",
        # Fiolet
        secondary="#7A00FF",
        # Cyjan
        accent="#00F0FF",
        # Ostrzeżenia
        warning="#FFE14D",
        # Błędy
        error="#FF3860",
        # Sukces
        success="#39FF88",
        # Tło
        background="#0A0014",
        # Panele
        surface="#14002A",
        # Wyróżnione panele
        panel="#22003F",
        # Tekst
        foreground="#F4E9FF",
        # Ciemny motyw
        dark=True,
    ),
    # Zielony monitor fosforowy
    Theme(
        # Nazwa motywu
        name="retro",
        # Zieleń fosforu
        primary="#33FF66",
        # Ciemniejsza zieleń
        secondary="#1FAA44",
        # Bursztyn
        accent="#FFCC00",
        # Ostrzeżenia
        warning="#FFCC00",
        # Błędy
        error="#FF5533",
        # Sukces
        success="#66FF99",
        # Tło
        background="#000A00",
        # Panele
        surface="#001A05",
        # Wyróżnione panele
        panel="#002A0A",
        # Tekst
        foreground="#9CFFB0",
        # Ciemny motyw
        dark=True,
    ),
    # Złoto i czerń – skarbiec
    Theme(
        # Nazwa motywu
        name="gold",
        # Złoto
        primary="#E5B83B",
        # Brąz
        secondary="#8C6A1C",
        # Jasne złoto
        accent="#FFE08A",
        # Ostrzeżenia
        warning="#FF9F1C",
        # Błędy
        error="#E63946",
        # Sukces
        success="#7BD389",
        # Tło
        background="#0D0B07",
        # Panele
        surface="#1A160D",
        # Wyróżnione panele
        panel="#2A2214",
        # Tekst
        foreground="#F6EBD0",
        # Ciemny motyw
        dark=True,
    ),
    # Jasny motyw dzienny
    Theme(
        # Nazwa motywu
        name="day",
        # Granat
        primary="#0B5394",
        # Niebieski
        secondary="#3D85C6",
        # Ciemne złoto (czytelne na jasnym tle)
        accent="#B8860B",
        # Ostrzeżenia
        warning="#C77700",
        # Błędy
        error="#C62828",
        # Sukces
        success="#2E7D32",
        # Tło
        background="#F4F1E8",
        # Panele
        surface="#FFFFFF",
        # Wyróżnione panele
        panel="#E3DED0",
        # Tekst
        foreground="#1B1B1B",
        # Jasny motyw
        dark=False,
    ),
)
