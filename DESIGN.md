# Design-System — MacroMic

Referenz für alle UI-Arbeiten. Baustein-Vorlage ist `landing.html`.
Ton, Farben, Fonts und Komponenten hier sind verbindlich — nichts dazuerfinden.

## Prinzipien
- Voice-first Ernährungslog. Kernversprechen: „Sag einfach, was du gegessen hast.“
- Ton: direkt, selbstbewusst, leicht trocken. **Du-Ansprache.**
- Kein Marketing-Sprech, keine Superlative, **keine Emojis**. Alles auf Deutsch.
- Responsive bis 375px runter, kein horizontales Scrollen.
- Animationen nur CSS-basiert und dezent; `prefers-reduced-motion` immer respektieren.
- Kein Dark Mode.

## Fonts (Google Fonts)
- **Newsreader** — Überschriften und Zahlenwerte (Serif, echte Kursiven für Betonung).
- **Inter** — Fließtext und UI.
- **Space Grotesk** — **ausschließlich** die Wortmarke (`_wordmark.html`), nie für UI-Text.

```html
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap" rel="stylesheet">
```

Große typografische Momente in Newsreader; Betonung als `<em>` (kursiv, in `--accent`).

Space Grotesk wird nur geladen, weil die Wortmarke als inline-`<text>` vorliegt. Sobald
der offene BRAND.md-Punkt erledigt ist (Text in Pfade umwandeln), fällt der Font aus dem
Link und aus dieser Liste — dann ist die Marke font-unabhängig.

## Farb-Tokens (exakt, keine neuen Grundfarben)
```css
:root{
  --bg:#eeece4;            /* Seitenhintergrund */
  --surface:#fbf8f2;       /* Karten/Flächen */
  --surface-2:#f2ede2;     /* abgesetzte Flächen */
  --text:#2b241f;          /* Fließtext */
  --text-muted:#7a7164;    /* sekundär */
  --text-subtle:#a39a8d;   /* tertiär (Hinweise, Fußzeilen) */
  --accent:#c96442;        /* Buttons, Akzente */
  --accent-hover:#b4553a;
  --accent-soft:#f2e2d6;   /* helle Accent-Fläche/Chip */
  --border:#e4dcc9;
  --danger:#a33520;        /* Fehler, Löschen, Limit erreicht */
  --danger-soft:#f4ded6;   /* helle Danger-Fläche (Hover auf Löschen) */
}
```
Innerhalb der Palette darf man mutig werden: großflächige Accent-Blöcke,
invertierte Sektionen (Text auf `--accent`), dunkle Panels (Text auf `--text`).
Nur keine neuen Grundfarben.

### Tints auf invertierten Flächen

Auf `--text` und `--accent` als Fläche trägt keiner der Text-Tokens genug Kontrast —
`--text-muted` auf einem dunklen Panel ist unlesbar. Dafür gibt es diese abgestuften
Helligkeiten. **Keine neuen Grundfarben**, sondern dieselben Familien heller gezogen;
die Liste ist abgeschlossen, genau wie die Palette oben.

```css
/* auf dunklem Panel (Fläche = --text) */
--on-dark:#f4efe6;          /* Fließtext */
--on-dark-muted:#b7ab99;    /* Labels, sekundär */
--on-dark-label:#a49887;    /* Label auf --on-dark-surface (eine Stufe tiefer) */
--on-dark-subtle:#8a7f6f;   /* tertiär, Einheiten */
--on-dark-surface:#39312a;  /* abgesetzte Fläche im Panel */
--on-dark-border:#4a4038;   /* Trennlinie im Panel */

/* auf Accent-Fläche (Fläche = --accent) */
--on-accent:#fdf3ee;        /* Fließtext */
--on-accent-soft:#fbe7de;   /* Aufzählungen */
--on-accent-muted:#f6d9cc;  /* sekundär, Eyebrow */
--on-accent-subtle:#f0c3b1; /* tertiär, Einheiten */
```

`#fff` ist der einzige erlaubte Weißwert. Er gilt auf beiden Flächen für Überschriften,
Button-Text, große Zahlenwerte und Icons auf `--accent` — überall dort, wo der Ton den
maximalen Kontrast tragen soll. Fließtext nie in `#fff`, dafür sind `--on-dark` und
`--on-accent` da.

**Danger vs. Accent:** `--danger` ist ein dunklerer, rotstichigerer Ton derselben
Familie — kein neuer Grundton, aber deutlich genug von `--accent` unterscheidbar,
damit eine Fehlermeldung nicht wie ein primärer Button aussieht. Nur für
Fehlertexte, Löschaktionen, erreichte Limits und Ziel-Überschreitung verwenden;
**nie für Buttons oder Flächen, die zu einer normalen Aktion einladen.**

## Komponenten (aus `landing.html`)
- **Button** `.btn`: Höhe 44px (`.lg` 54px), Radius 11–13px, `--accent` → Hover `--accent-hover`,
  leichter `translateY(-1px)`. Ghost-Variante: transparent, 1px `--border`.
- **Karte** `.card`: `--surface`, 1px `--border`, Radius 20px, Padding 32px;
  Hover hebt an (`translateY(-3px)` + weicher Schatten). Abgesetzt: `--surface-2`.
- **Icon-Badge**: 46px, Radius 13px, `--accent-soft` Hintergrund, `--accent` Icon.
- **Invertierter Accent-Block**: Hintergrund `--accent`, Text `--on-accent`/`--on-accent-muted`, Radius 32px.
- **Bento-Grid**: `repeat(6,1fr)`, Karten spannen 2/3 Spalten; auf Mobile 1 Spalte.
- **Reveal-on-scroll** `.rv`: `IntersectionObserver`, bei reduced-motion sofort sichtbar.
- **Icons**: ausschließlich inline-SVG, `stroke-width` 2, `stroke-linecap/linejoin round`.
  Keine SVGs von Hand malen, die komplexer sind als Grundformen.

## Routen / CTAs
- Primär-CTA im Seiteninhalt → `/register` („Jetzt registrieren“).
  In der Nav heißt derselbe Button nur „Registrieren“ — bei 40px Höhe und neben der
  Wortmarke passt die lange Variante nicht, ohne auf 375px zu drängen.
- `/login` **nur** als dezenter Textlink („Schon dabei? Anmelden“), nie als zweiter
  großer Button neben dem Primär-CTA: zwei gleich große Buttons teilen die
  Aufmerksamkeit, und Anmelden ist nicht das Ziel der Seite. In der Nav ist der
  schlichte Textlink erlaubt.
- Hinweis in `--text-subtle`: „Zugang aktuell nur mit Invite-Code.“

## Feature-Wording (nur diese, nichts dazuerfinden)
- Sprachaufnahme im Browser → transkribiert → Makros.
- Freitext-Eingabe in natürlicher Sprache, keine Dropdowns/Gramm-Angaben.
- Stellt eine kurze **Rückfrage**, wenn eine wichtige Angabe fehlt, statt eine Zahl
  zu erfinden — das Alleinstellungsmerkmal.
- Makroziele mit Tagesfortschritt, plus Auswertung Woche/Monat.
- Rezepte mit Makros pro Portion, Zutaten auch per Sprache.
- Verlauf mit Wochen-/Monatsansicht, Mahlzeiten nachträglich bearbeitbar.
