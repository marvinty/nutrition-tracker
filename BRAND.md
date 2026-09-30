# MacroMic — Marke

Die Marke folgt der Oberfläche „Nährwerte“ (siehe [DESIGN.md](DESIGN.md)): Schwarz auf
Weiß, Archivo, rechte Winkel. Keine weitere Markenfarbe.

## Dateien (`app/static/brand/`)

| Datei | Verwendung |
|---|---|
| `macromic-wordmark.svg` | Wortmarke „MacroMic“, Schwarz `#0f0f0d`. Überall, wo keine Webfont lädt: Mail, Print, Präsentation, Social. |
| `macromic-wordmark-white.svg` | Dieselbe Wortmarke in Weiß, für dunkle Flächen. |
| `macromic-mark.svg` | Monogramm: weißes „M“ auf schwarzem Quadrat. Favicon und App-Icon. |
| `apple-touch-icon.png` | Das Monogramm als 180×180-PNG für den iOS-Homescreen. |

Alle SVGs bestehen aus **Pfaden, nicht aus Text** — sie rendern ohne Schrift identisch.

## Aufbau

- **Wortmarke:** Archivo, Gewicht 800, normale Breite, Laufweite −0,01em, Kerning aus der
  Schrift. Entspricht exakt der Kopfzeile der App, dort als Text gesetzt.
- **Monogramm:** Archivo, Gewicht 900, Breite 72 % — die Lage der Seitenüberschriften.
  Versalhöhe 64 % der Fläche, zentriert, Quadrat ohne Rundung. Lesbar ab 16px.
- Kein Mikrofon- oder Wellenmotiv; die Sprachfunktion zeigt die App selbst.

## Regeln

- Nur Schwarz oder Weiß. Keine Tönung, kein Verlauf, kein Schatten, kein Radius.
- Wortmarke nicht nachbauen, verzerren oder in eine andere Schrift setzen.
- Schutzraum: mindestens die Höhe des „M“ der Wortmarke auf allen Seiten.

## Neu erzeugen

Die Pfade wurden mit fontTools und HarfBuzz aus `app/static/fonts/archivo-normal-latin.woff2`
instanziert (wght/wdth wie oben). Ändert sich die Schrift, werden die Dateien neu erzeugt
statt von Hand editiert; das PNG ist eine 180px-Rasterung von `macromic-mark.svg`.
