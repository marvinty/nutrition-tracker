# MacroMic — Wortmarke (Richtung 02 · Präzisionswerkzeug / Grotesk)

Handoff für Claude Code. Dies sind fertige Brand-Assets, kein Code-Refactor.

## Dateien

Lege den Ordner `brand/` nach `app/static/brand/` (oder wo eure statischen Assets liegen):

| Datei | Verwendung |
|---|---|
| `macromic-wordmark.svg` | **Primär.** Farbig, gedacht auf Creme (#fbf8f2). Header + Landing Page. |
| `macromic-wordmark-mono.svg` | Einfarbig (#2b241f). Für Kontexte ohne Farbe (Rechnung, Print, Wasserzeichen). |
| `macromic-wordmark-dark.svg` | Dark Mode — helle Schrift auf dunklem Grund (#2b241f). |
| `macromic-mark.svg` | Monogramm / App-Icon / Favicon. Quadratisch, lesbar bis 32×32px. |

## Palette (bereits in den SVGs)

- Terracotta `#c96442` · Terracotta dunkel `#a33520` · Warmgrau `#7a7164`
- Creme `#fbf8f2` · Fast-Schwarz `#2b241f`

## Einbau

- Wortmarke inline oder als `<img>` einbinden; `width` setzen, `height:auto` (viewBox skaliert sauber).
- Favicon: `<link rel="icon" href="/static/brand/macromic-mark.svg">`.
- Dark-Mode-Umschaltung: per `prefers-color-scheme` bzw. eurem Theme-Toggle zwischen `-wordmark.svg` und `-wordmark-dark.svg` wechseln.

## WICHTIG — Font vor echtem Launch fixieren

Die SVGs nutzen bewusst einen generischen Font-Stack (`Space Grotesk, system-ui, sans-serif`), damit sie ohne externe Fonts überall rendern. Für einen wirklich pixel-identischen Auftritt:

1. SVG in Figma/Inkscape öffnen, echten Font setzen (`Space Grotesk` ist gratis via Google Fonts, kommerziell nutzbar).
2. **Text in Pfade umwandeln** (Text → Outline / Object to Path).
3. Exportieren. Danach ist das SVG font-unabhängig und produktionsreif.

Für den Validierungs-Test (Landing, Demo-Video, Stripe) reichen die Dateien so wie sie sind.
