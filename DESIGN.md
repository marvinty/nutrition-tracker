---
name: MacroMic
description: Voice-first Ernährungslog — der Tag als laufende Rechnung auf Thermopapier.
colors:
  table: "#123028"
  table-dark: "#0c231d"
  paper: "#efeee6"
  paper-2: "#e6e4da"
  ink: "#1b1a15"
  ink-2: "#4a473e"
  faint: "#696558"
  red: "#c4200d"
  red-soft: "#f6e3df"
  rule: "#c9c6b8"
  rule-soft: "#dedbcd"
  lead: "#b3afa0"
  on-table: "#cfe0d8"
  on-table-faint: "#8fa89e"
typography:
  label:
    fontFamily: "Sometype Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.1em–0.22em"
    textTransform: "uppercase"
  print:
    fontFamily: "Sometype Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.5
  line:
    fontFamily: "Sometype Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
  datum:
    fontFamily: "Big Shoulders Display, Sometype Mono, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0.01em"
  kopf:
    fontFamily: "Big Shoulders Display, Sometype Mono, sans-serif"
    fontSize: "44px"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "0.015em"
    textTransform: "uppercase"
  zahl:
    fontFamily: "Big Shoulders Display, Sometype Mono, sans-serif"
    fontSize: "62px"
    fontWeight: 800
    lineHeight: 0.82
    letterSpacing: "0.005em"
rounded:
  none: "0"
spacing:
  haar: "3px"
  innen: "9px"
  block: "18px"
  rinne: "26px"
  rinne-sm: "17px"
components:
  btn-stempel:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.print}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "46px"
  btn-stempel-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  btn-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "46px"
  btn-ink-recording:
    backgroundColor: "{colors.red}"
    textColor: "{colors.paper}"
  btn-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "46px"
  btn-red:
    backgroundColor: "transparent"
    textColor: "{colors.red}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "46px"
  btn-sm:
    typography: "{typography.label}"
    padding: "0 13px"
    height: "38px"
  input-zeile:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.line}"
    rounded: "{rounded.none}"
    padding: "10px 2px"
    height: "46px"
  input-zeile-focus:
    backgroundColor: "{colors.paper-2}"
  nav-bereich:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "5px 7px 4px"
  nav-bereich-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  rolle:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 26px 26px"
    width: "560px"
  block-abgesetzt:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "16px 26px 18px"
  beleg:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "26px 24px 24px"
  beleg-kopf:
    backgroundColor: "transparent"
    textColor: "{colors.faint}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 0 8px"
  btn-papier:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 15px"
    height: "40px"
  btn-papier-hover:
    backgroundColor: "transparent"
    textColor: "{colors.paper}"
  btn-papier-gross:
    typography: "{typography.print}"
    padding: "0 26px"
    height: "56px"
---

# Design-System — MacroMic

Referenz für alle UI-Arbeiten. Farben, Schriften, Komponenten und Regeln hier sind
verbindlich — **nichts dazuerfinden.**

Es gibt aktuell **zwei Welten**, und welche gilt, hängt an der Datei, die du gerade
bearbeitest:

| Welt | Gilt für | Quelle |
|---|---|---|
| **Bon** (System of Record) | alles, was von `app/dashboard/templates/base_bon.html` erbt — heute `/dashboard` und `/` — und **jede neue Arbeit** | dieses Dokument, Abschnitte Overview bis Do's and Don'ts |
| **Alte Welt** (Bestand, eingefroren) | alles, was von `app/dashboard/templates/base.html` oder den übrigen Landing-/Auth-Templates erbt: `/faq`, `/impressum`, `/datenschutz`, Auth, Admin, `/history`, `/goals`, `/recipes`, `/weight`, `/ai-log`, `/feedback` | Abschnitt *Nicht migrierte Oberflächen* am Ende |

Die alte Welt wird nicht weiterentwickelt und nicht gemischt. Sie wird **Seite für
Seite** auf den Bon umgestellt; bis eine Seite umgezogen ist, gelten für sie die alten
Tokens unverändert. Ein neues Muster erfindest du nur im Bon.

## Regeln, die in beiden Welten gelten

- **Alles ist Deutsch** — UI-Texte, Fehlermeldungen, `detail`-Strings auf `HTTPException`.
  Einige davon werden dem Nutzer unverändert angezeigt.
- Ton: direkt, selbstbewusst, leicht trocken. **Du-Ansprache.** Kein Marketing-Sprech,
  keine Superlative, **keine Emojis**. Kein Dark Mode.
- Responsive bis **375px** runter, **kein horizontales Scrollen**.
- Animationen nur CSS-basiert; `prefers-reduced-motion: reduce` wird **immer**
  respektiert (im Bon global: `*{animation:none!important;transition:none!important}`
  plus ein Ruhezustand für jede Animation, die etwas sichtbar macht).
- CSS steht **inline pro Template**. Ausnahmen unter `/static`: die Brand-Assets
  ([BRAND.md](BRAND.md)) und die selbst gehosteten Schriften.
- **Nie** von `fonts.googleapis.com` einbinden. Das CDN überträgt die IP-Adresse jedes
  Besuchers an Google, bevor irgendjemand zugestimmt hat — genau der Punkt aus
  **LG München I, 20.01.2022 (3 O 17493/20)**. Die Datenschutzerklärung sagt zu, dass
  kein Dritter eine IP sieht; ein Template, das zum CDN greift, macht diese Seite
  stillschweigend zur Lüge. Die Dateien liegen unter `app/static/fonts/`, die
  `@font-face`-Regeln in `app/static/fonts.css` (alte Welt) und
  `app/static/fonts-bon.css` (Bon). Beide sind generiert; wer eine Schnittstärke
  ergänzt, erzeugt die Dateien neu, statt die CSS von Hand zu editieren.

## Overview

**Creative North Star: „Der Tagesbon"**

Der Tag ist eine **laufende Rechnung**, kein Feed und kein Karten-Dashboard. Eine Rolle
Thermopapier liegt auf einer dunkelgrünen Tischfläche; oben die abgerissene Kante, unten
die Schnittkante mit der Schere. Dazwischen wird gedruckt: Bonkopf, Bereichszeile, die
Eingabe, die Positionen in Druckreihenfolge, die doppelte Linie, die Summe, der Rest als
einzige große Zahl, die Nährwerttabelle. Die Reihenfolge ist Teil der Form — die Arbeit
(„sag, was du gegessen hast") steht **vor** der Bilanz, weil das der Job der Seite ist.

Die Welt kennt **zwei Anordnungen desselben Materials**. Im System of Record läuft eine
durchgehende **Rolle** (`.roll`); eine Oberfläche, die keine laufende Rechnung ist, legt
stattdessen **einzelne Belege** (`.beleg`) auf denselben Tisch — so die Landing Page. Papier
bleibt dabei Papier: dieselben Tokens, dasselbe Korn, dieselbe Abrisskante, derselbe
Schatten. Was nicht auf Papier steht, steht direkt auf dem Grün. Austauschbar ist nur die
Hülle (`{% block shell %}`), nie das Material.

Das Material trägt die Gestaltung, nicht die Dekoration. Papier ist nie ein glatter
Farbwert, sondern eine gekachelte `feTurbulence`-Körnung bei 5,5 % Deckkraft; Ränge
entstehen aus Gewicht, Versalien, Punktführung und Linienstärke, nicht aus einer
Größenleiter; Zustände entstehen aus Umkehrung (Ink-Fläche, Papier-Schrift), nicht aus
Füllfarben. Registrier-Rot ist die einzige zweite Farbe und wird knapp gehalten.

Verweigert wird beides: die Kategorie-Anordnung (Makro-Ringe, gefüllte Fortschritts-
balken, gleich große Karten mit Icon) **und** ihr Gegenteil, der frühere Ist-Zustand aus
Creme, Serifen-Display und Terracotta.

**Key Characteristics:**
- Thermopapier auf dunkelgrünem Tisch; ein einspaltiger Bon, max. 560px breit.
- Zwei Anordnungen: die durchgehende Rolle (App) und einzelne Belege auf dem Tisch.
- Sechs Textgrade, geschlossen. Rang aus Gewicht, Versalien, Punktführung, Linie.
- Rechtwinklig durchgehend, kein Radius über 0.
- Monospace trägt alles Gedruckte; die Display-Schrift nur Kopf, Datum und die eine Zahl.
- Tabellen und Zeilen statt Balken und Ringe.
- Knöpfe sind Stempelfelder mit harter 1,5px-Kontur, nie gefüllte Pillen.
- Registrier-Rot nur für Offenes, Fehler, Überschreitung und die laufende Aufnahme.

## Colors

Zwei Materialien und eine Signalfarbe: Papier (warm, entsättigt), Tisch (dunkel, grün)
und Registrier-Rot. Mehr Grundfarben gibt es nicht.

### Primary
- **Registrier-Rot** (`--red`): die einzige zweite Farbe. Offene Beträge, Fehlerzustände,
  Zielüberschreitung, die laufende Aufnahme, der Fokusring, die Textauswahl und die
  Oberkante des Rückfrage-Blocks. Nie für eine normale, einladende Aktion.
- **Rot-Papier** (`--red-soft`): einzige rote Fläche im System, ausschließlich für den
  Verifizierungs-Hinweis (`.verify-banner`) hinter einer 1px-Kante in `--red`.

### Neutral — Papier
- **Thermopapier** (`--paper`): die Rolle, jede Eingabefläche, Schrift auf umgekehrten
  Flächen (Ink-Knopf, aktiver Bereich, Auswahl).
- **Abgesetzter Druck** (`--paper-2`): Blöcke, die als eigener Druckvorgang gelesen werden
  sollen — Rückfrage, Quittung, Eingabefeld im Fokus, die frisch gebuchte Zeile.
- **Druckfarbe** (`--ink`): Fließtext, Zahlen, Konturen, umgekehrte Flächen.
- **Druckfarbe, zweite Ebene** (`--ink-2`): Labels, Summenzeilen, sekundäre Knöpfe, Links
  in der Bereichszeile.
- **Verblasst** (`--faint`): dritte Ebene — Makro-Unterzeile, Meta, Hinweise, Platzhalter,
  Fußzeile. **Das ist der Boden**; 4,5:1 auf `--paper`, tiefer geht nichts.
- **Linie** (`--rule`) und **Linie hell** (`--rule-soft`): Trennlinien auf Papier, Konturen
  inaktiver Bedienelemente.
- **Führungspunkt** (`--lead`): die gepunktete Punktführung zwischen Bezeichnung und Wert
  sowie die Schnittkante. Steht im Build noch als Literal (`#b3afa0`, Schnittkante
  `#b9b5a6`) statt als Custom Property — beim nächsten Anfassen tokenisieren.

### Neutral — Tisch
- **Tischfläche** (`--table`) und **Tischrand** (`--table-dark`): der Radialverlauf hinter
  der Rolle (`130% 70% at 50% 0`), `background-attachment: fixed`, plus die Scrollbar-Spur.
- **Text auf dem Tisch** (`--on-table`) und **Text auf dem Tisch, gedämpft**
  (`--on-table-faint`): die **Tischebene** — alles, was nicht auf Papier liegt. Auf der
  Landing Page tragen sie Wortmarke, Leistenlinks, Überschriften, Lede, Hinweise und
  Fußzeile: `--on-table` ist dort der Lesewert, `--on-table-faint` die zweite Ebene und die
  Farbe der Punktführung. Trennlinien und Unterstreichungen auf dem Tisch sind
  Alpha-Abstufungen genau dieser beiden Werte, kein dritter Ton. Papierfarben
  (`--ink`, `--ink-2`, `--faint`, `--rule`) haben auf dem Tisch nichts zu suchen und
  umgekehrt.

### Named Rules
**Die Rot-Regel.** `--red` steht für **Offenes, Fehler, Überschreitung und die laufende
Aufnahme** — sonst nirgends. Ein Knopf ist erst rot, wenn er einen offenen Vorgang
abbricht oder eine Aufnahme läuft; ein Angebot ist nie rot. Test: kann man den roten
Punkt der Seite mit einem Satz erklären, der „noch offen", „falsch", „zu viel" oder
„läuft gerade" enthält? Wenn nein, ist er falsch.

**Die Keine-neuen-Grundfarben-Regel.** Die Liste oben ist abgeschlossen. Eine zusätzliche
Fläche wird aus `--paper-2` und einer Linie gebaut, nicht aus einem neuen Ton.

**Die Tisch-Ring-Regel.** Der Fokusring des Shells ist für Papier gemacht: `--red` erreicht
gegen die Tischfläche nur **~2,4:1** und verschwindet dort. Eine Oberfläche, die
Bedienelemente direkt auf den Tisch stellt, überschreibt den Ring deshalb auf **2px
`--paper`** mit 3px Versatz; auf Papier bleibt er rot. Zwei Materialien, zwei Ringe — einen
dritten gibt es nicht.

**Die Kein-Weiß-Regel.** Es gibt kein `#fff` im Bon. Die hellste Farbe ist `--paper`;
umgekehrter Text steht in `--paper`, nicht in Weiß.

## Typography

**Print Font:** Sometype Mono (mit `ui-monospace`, `SFMono-Regular`, `Menlo`, `monospace`)
**Display Font:** Big Shoulders Display (mit Sometype Mono als Fallback)

Beide selbst gehostet als Variable Fonts, `app/static/fonts-bon.css`, mit
`<link rel="preload">` auf `sometype-mono-normal-latin.woff2` und
`big-shoulders-normal-latin.woff2`.

**Character:** Die Monospace druckt; sie hält Spalten ohne Raster und lässt Zahlen
untereinander stehen (`font-variant-numeric: tabular-nums` global auf `body`). Die
Display-Schrift ist schmal, hoch und laut — sie darf genau dreimal auftreten: Bonkopf,
Datum, die eine große Zahl.

### Hierarchie
Sechs Grade, geschlossen. Drei Textgrade und drei Displaygrade:

- **Label** (`--t-label`, 11px, Versalien, `letter-spacing` 0.1–0.22em): Spaltenköpfe,
  Feld-Labels, Blocküberschriften, Statusmarken. **Nur Versalien-Beschriftung, nie
  Lesetext** — 11px ist der Boden des Systems und trägt nur einzelne Wörter.
- **Zweitdruck** (`--t-print`, 12.5px): Makro-Unterzeile, Meta, Hinweise, Credits,
  Knopfbeschriftung, Fußzeile.
- **Zeile** (`--t-line`, 15px, `line-height` 1.5): Zeilentext, Bezeichnungen, Eingaben,
  Fragen, kcal-Werte. Der Lesegrad.
- **Datum** (`--d-datum`, 26px, Display 700): `<h1>` im Bonkopf. Auf der Tischebene trägt
  dieser Grad die Wortmarke in der Leiste — der einzige Auftritt der Displayschrift auf der
  Landing Page.
- **Bonkopf** (`--d-kopf`, 44px → 36px unter 430px, Display 800, Versalien): die Wortmarke
  im Bonkopf. Derselbe Grad trägt auf einer Persuade-Fläche die Abschnittsüberschrift —
  dort in Sometype Mono 700, gemischte Schreibung, Laufweite −.03em.
- **Zahl** (`--d-zahl`, 62px → 52px unter 430px, `line-height` 0.82): die Displayschrift 800
  für Rest bzw. Tagessumme. Auf einer Persuade-Fläche trägt der Grad den einen
  Aufmacher-Titel, in Sometype Mono 700 mit eigener Zeilenhöhe (1.04) und −.035em.
  **Genau einmal pro Ansicht** — in beiden Fällen.

### Named Rules
**Die Sechs-Grade-Regel.** Ein `font-size` außerhalb der sechs Tokens gibt es nicht — kein
`14px`, kein `1.1rem`, kein `clamp()`. Wer einen siebten Grad braucht, braucht in
Wahrheit ein anderes Gewicht, Versalien oder eine Linie.

**Die Rang-ohne-Größe-Regel.** Rang entsteht aus **Gewicht** (400 / 500 / 700 / 800),
**Versalien mit Sperrung**, **Punktführung** und **Linienstärke** — nicht aus einer
Größenleiter. Eine feine Größentreppe ist genau das, was diese Oberfläche verweigert.

**Die Drei-Auftritte-Regel.** Big Shoulders Display erscheint ausschließlich im Bonkopf,
im Datum und in der einen großen Zahl. Alles andere, inklusive jeder Überschrift, ist
Sometype Mono. **Das gilt auch auf einer Persuade-Fläche:** die Landing Page setzt ihre
Überschriften auf den Displaygraden, aber in Sometype Mono. Die Displaygrade sind
**Größen, keine Schriftschnitte**. Die Frage, ob eine Landing-Überschrift die Displayschrift
bekommen darf, wurde beim Bau gestellt und **verneint** — nicht neu aufrollen.

**Die Betonungs-Regel.** Betonung eines Wortes ist die **Punktführung**:
`text-decoration: underline dotted`, 3px Stärke, 8px Versatz, Farbe eine Stufe unter dem
Text (auf dem Tisch `--on-table-faint`). **Nie kursiv** — die Displayschrift hat keine
Kursive, und die Monospace täuscht sie nur — und **nie über Farbe**, denn die einzige
zweite Farbe ist reserviert.

**Wortmarke — offene Entscheidung.** Der Name steht im Bonkopf derzeit als **Text in Big
Shoulders Display**, nicht als SVG aus `app/static/brand/`. Space Grotesk bleibt weiterhin
selbst gehostet, weil die Wortmarken-SVG sie als inline-`<text>` braucht. Ob die Wortmarke
umgezeichnet wird oder das SVG in den Bonkopf wandert, ist **vor dem Launch zu klären**
und im Surface-Brief festgehalten (`.impeccable/surfaces/app-dashboard-templates-dashboard-html.md`).
Bis dahin: nicht auflösen, nicht kopieren.

## Layout

Eine Spalte, zentriert, `max-width: 560px`. Die Rolle (`.roll`) hat 26px Seitenrinne,
unter 430px 17px; darum liegt `.sheet` mit 22px/12px Polsterung, die den Tisch sichtbar
lässt. Blöcke, die als eigener Druckvorgang gelesen werden (Rückfrage, Quittung), ziehen
sich mit negativem Außenabstand über die volle Papierbreite und **müssen im 430px-Block
mitgehen** (`margin-left/right: -17px`), sonst schieben sie die Seite über den Viewport.

**Die Hülle ist ein Block.** `base_bon.html` rendert seinen Standardaufbau — `.sheet` um
`.roll`, darin Bonkopf, Bereichszeile, Inhalt, Fuß und Schnittkante — in
`{% block shell %}`. Eine Oberfläche, die keine durchgehende Rolle ist, **ersetzt diesen
Block** und bezieht Tokens, Knöpfe, Eingaben, Linien und Browser-Flächen unverändert aus
dem Shell. Die Landing Page tut genau das: `.tisch` (max. 1180px, Rinne
`clamp(16px, 4vw, 40px)`) statt `.sheet`/`.roll`, darin einzelne `.beleg`-Blätter. Ein
Beleg bekommt seine Breite von der Spalte, in der er liegt, nicht von einer eigenen
`max-width`.

Kein Grid-System, sondern **eine benannte Spur**: `.pos-liste` und `.pos-kopf` teilen
sich `--pos-cols: 26px 46px 1fr auto` (Nummer, Zeit, Bezeichnung, kcal). Die Zeile selbst
ist ein zweizeiliges Grid mit `grid-template-areas: "nr zeit bez kcal" ". . fuss fuss"` —
Makro-Unterzeile und „Korrigieren" teilen sich die beiden rechten Spuren.

Kein Breakpoint-Set, sondern Abfragen: `max-width: 430px` (Rinnen, `--d-kopf`, `--d-zahl`,
Korrekturfelder von 4 auf 2 Spalten) und `pointer: coarse` (jedes kleine Bedienelement auf
min. 44px). **Beide Grad-Schritte stehen im Shell** und gelten damit für jede Oberfläche;
ein Template setzt `--d-kopf`/`--d-zahl` im 430px-Block nicht noch einmal. Eine
Tisch-Oberfläche darf einen Aufbau-Breakpoint ergänzen: die Landing Page wird ab
`min-width: 900px` zweispaltig (Aufmacher `1.05fr .95fr`, Abschnitt mit Beleg
`.85fr 1.15fr`, zwei gleiche Belege `1fr 1fr`) und stapelt darunter in Quellreihenfolge.
Alles andere fließt.

Rhythmus (keine Tokens im Build, aber gelebte Bänder): 2–4px haarfein, 6–10px innerhalb
einer Komponente, 12–18px zwischen Blöcken, 22–26px Rinne und Sektionsabstand.

### Named Rules
**Die Spurenregel.** Ein Spaltenkopf und seine Zeilen teilen **dieselbe** Variable für
`grid-template-columns`. Zwei getrennte Raster bemessen ihre `auto`-Spalten am eigenen
Inhalt, und ein Spaltenkopf, der seine Spalte verfehlt, ist in einer gedruckten Tabelle
genau der Fehler, den die Form vermeidet.

**Die 375px-Regel.** Sieben Bereiche passen auf 375px nicht in eine Zeile: die
Bereichszeile **bricht um**, sie scrollt nicht. Eine halb abgeschnittene Beschriftung
sieht aus wie ein Fehler. Nichts im Bon scrollt horizontal.

## Elevation & Depth

Das System kennt genau **eine** Erhebung: die Papierrolle liegt auf dem Tisch. Innerhalb
des Papiers gibt es **keine Schatten** — Tiefe entsteht dort durch Fläche (`--paper-2`),
Linie und Korn.

### Shadow Vocabulary
- **Papier auf Tisch** (`box-shadow: 0 22px 48px -16px rgba(0,0,0,.62), 0 2px 5px rgba(0,0,0,.34)`):
  auf `.roll` und auf `.beleg` — derselbe Wert, weil beide dasselbe Blatt auf demselben
  Tisch sind. Weicher, weiter Schlagschatten plus harte Kontaktkante.

### Named Rules
**Die Kornregel.** Jede Fläche, die Papier ist, trägt `--grain` — auch die Abrisskante
(`.roll::before`) und die randlosen Blöcke. Sonst sind genau diese Stellen kornfrei und
verraten den Trick. `background: var(--grain) repeat, <farbe>`.

**Die Ein-Erhebung-Regel.** Genau **ein** `box-shadow`-Wert im System, und er gehört dem
Papier auf dem Tisch — der Rolle wie dem einzelnen Beleg. Keine Hover-Anhebung, kein
Karten-Schatten, kein harter Versatz-Schatten.

**Die Rasterkosten-Regel.** Die Abrisskante ist ein eigener 8px-Streifen über dem Papier,
keine Maske auf ihm: eine Maske über die volle Bonhöhe ist eine Compositing-Schicht von
mehreren tausend Pixeln, die beim Scrollen neu gerastert wird. `.roll::before` und
`.beleg::before` teilen sich diese Regel, damit die Maskendefinition **genau einmal** im
Projekt steht.

## Shapes

**Rechtwinklig, ausnahmslos.** `border-radius: 0` ist kein Default, sondern eine Ansage —
Knöpfe und Eingaben setzen ihn explizit. Einziger Kreis im System ist der 9px-Punkt der
Aufnahmeanzeige (`border-radius: 50%`): eine Leuchte, kein Kasten.

Form entsteht aus **Linien**, und davon gibt es drei Stärken:

- **1px `solid` / `dotted` `--rule`** — Trennung zwischen Zeilen (gepunktet), Rahmen der
  Meta-Zeile und kleiner Bedienelemente (durchgezogen).
- **2px `solid --ink`** (`.rule-2`) — Anfang eines Blocks; trägt auch die Oberkante von
  Erfassung und Quittung. In Rot (`--red`) die Oberkante der Rückfrage.
- **3px `double --ink`** (`.rule-d`) — **nur** über der Summe. Die Abschlusslinie des Bons.

Kanten statt Flächen: Unterstreichungen (`text-underline-offset: 3px`,
`text-decoration-color: --rule`), 1,5px-Unterkanten an Eingaben, 1,5px-Konturen an
Stempelknöpfen. Die einzige gestrichelte Linie ist die Schnittkante im Fuß.

### Named Rules
**Die Rechtwinkel-Regel.** Kein Radius über 0. Ein Element, das rund sein will, ist im
Bon das falsche Element.

**Die Drei-Linien-Regel.** Einfach, gepunktet, doppelt — mehr Linienvokabular gibt es
nicht. Eine vierte Stärke erfindet einen Rang, den die Typografie schon vergibt.

## Components

### Papier: Rolle (`.roll`) und Beleg (`.beleg`)
Zwei Anordnungen desselben Materials, beide aus dem Shell.
- **Rolle:** die durchgehende Bahn der App-Oberflächen — max. 560px, 26px Rinne (17px unter
  430px), Abrisskante oben, Schnittkante im Fuß, außen `.sheet` als Tischluft.
- **Beleg:** ein einzelnes Blatt — Korn auf `--paper`, Polsterung 26px/24px/24px, dieselbe
  Abrisskante, derselbe Schatten, **keine** Schnittkante (ein Beleg ist bereits abgerissen).
  Randlose Blöcke im Beleg ziehen mit `-24px` nach, wie sie im Bon mit `-26px`/`-17px`
  nachziehen.
- **Belegkopf** (`.beleg-kopf`): die gedruckte Kopfzeile des Blatts — `--t-label` in
  `--faint`, Bezeichnung links, Qualifizierer rechts, 1px `--rule` darunter. Sie beschriftet
  **das Blatt**, nicht den Text darunter; sie ist kein Eyebrow und ersetzt keine Überschrift.

### Stempelknöpfe (`.btn`)
Charakter: ein Stempelfeld, das man aufs Papier drückt — harte Kontur, Versalien, weite
Sperrung, kein Radius.
- **Form:** rechtwinklig (0), 1,5px Kontur, min. 46px hoch, 0/20px Polsterung,
  `--t-print`, `font-weight: 700`, `letter-spacing: .14em`, Versalien.
- **Standard (Outline):** transparent auf Papier, Kontur und Schrift `--ink`.
- **Hover / Focus:** Umkehrung — Fläche `--ink`, Schrift `--paper`, `.12s ease-out`.
  `:active` setzt `translateY(1px)`, das einzige Drücken im System. `:disabled` 42 %.
- **`.ink`:** die Umkehrung im Ruhezustand — die Hauptaktion eines Voice-first-Logs
  („Sprechen") trägt den invertierten Druck; Hover kehrt zurück auf transparent.
- **`.ink.is-recording`:** Fläche `--red`. Rot erst, wenn wirklich aufgenommen wird —
  dann ist es ein offener Vorgang, kein Angebot.
- **`.ghost`:** Kontur `--rule`, Schrift `--ink-2`, Gewicht 400 — die zweite Wahl neben
  einer Hauptaktion („Abbrechen", „Korrigieren").
- **`.red`:** Kontur und Schrift `--red`, Hover füllt rot. Nur destruktiv.
- **`.sm`:** 38px (unter `pointer: coarse` 44px), `--t-label`, 0/13px.
- **`.link-btn`:** randloser Textknopf mit 1px-Unterkante in `--rule` — für Aktionen, die
  in einem Satz stehen („Abmelden", „Mail erneut senden").
- **`.btn-papier` (Tischebene):** der Stempel auf dem Grün — Fläche `--paper` **mit Korn**,
  1,5px Kontur in `--paper`, Schrift `--ink`, `--t-label`/700/.16em, 40px (`.gross`: 56px,
  `--t-print`). Hover kehrt um auf transparent mit Schrift `--paper`. Auf dem Tisch ist
  Papier das, was auf dem Papier `.ink` ist: der Primär-CTA trägt die Umkehrung und ist
  **nie rot**. Das CSS steht im Template der Tisch-Oberfläche, nicht im Shell.

### Eingaben
- **Stil:** keine Box — Papierfläche mit **1,5px-Unterkante in `--ink`**, kein Radius,
  46px hoch, `--t-line`, Polsterung 10px/2px, volle Breite.
- **Fokus:** Fläche wechselt auf `--paper-2`; `:focus-visible` legt zusätzlich den roten
  2px-Ring mit 2px Versatz an.
- **Disabled:** Schrift `--faint`, Kante `--rule`.
- **Label:** `--t-label`, Versalien, `letter-spacing: .12em`, `--faint`. Wo die
  Blocküberschrift schon das Label ist, wird sie per `aria-labelledby` verwendet statt
  ein zweites daneben zu setzen. Platzhalter sind Beispiele, keine Labels.

### Bereichszeile (`.bon-nav`)
Gedruckte Bereichsliste, umbrechend, 3px Abstand. Ruhezustand: `--t-label`, Versalien,
`--ink-2`, transparente 1px-Kontur. Hover zeigt die Kontur in `--rule`. **Aktiv: volle
Umkehrung** — Fläche `--ink`, Schrift `--paper`, Gewicht 500. Kein Unterstrich, kein
Balken.

### Positionszeile (`.pos`) — Signaturkomponente
Die Zeile des Bons: Nummer (`--faint`), Uhrzeit (`--faint`), Bezeichnung (`--t-line`,
Gewicht 500) mit Punktführung, kcal rechtsbündig (Gewicht 700). Darunter die Makro-Unter-
zeile in `--t-print`/`--faint`, deren Werte nie zwischen Zahl und Einheit brechen
(`white-space: nowrap` je Makro), und rechts „Korrigieren" als Textknopf mit Unterkante.
Zeilentrennung: 1px `dotted --rule`.

**Die Punktführung.** Die Punktreihe ist ein **Geschwisterelement**
(`.pos-bez__lead`, `flex: 1 1 12px`, `border-bottom: 1px dotted`, `translateY(-4px)`),
kein Pseudoelement in einem `overflow: hidden`-Kasten: ein Scroll-Container exportiert
keine Grundlinie, und die Zeile richtet sich an der Grundlinie aus. Dieselbe Technik
trägt die Summenzeilen (`.summe-zeile .lead`).

### Rückfrage (`.clarify`)
Der rote Zwischendruck und der Kern des Produkts. Randloser Block über die volle
Papierbreite, Fläche `--paper-2` **mit Korn**, Oberkante 2px `--red`, Unterkante 1px
`--rule`. Darüber die zentrierte Druckmarke „— Rückfrage —" in `--t-label`/700/`.2em`/
`--red`; darunter die Frage in `--t-line`, Gewicht 700, max. 34ch. Der Kasten trägt
`role="status"` / `aria-live="polite"`, das Antwortfeld wird von der Frage benannt.
Die Marke ist ein **gedruckter Abschnittsmarker des Bons**, kein Eyebrow — sie steht
mittig, ohne Überschrift darunter, und wird nicht auf andere Blöcke übertragen.

### Quittung (`.gebucht`)
Gleicher randloser Block, Oberkante 2px `--ink`. Marke „Gebucht" mit 15px-Haken-SVG,
Bezeichnung in `--t-line`/700, die vier Werte als Zweitdruck (`<b>` in `--ink`, Einheit
in `--faint`), darunter ein `.btn.sm.ghost` „Korrigieren".

### Summe (`.summe`) und Nährwerttabelle (`.mtab`)
Summe: 3px `double --ink` als Abschlusslinie, darunter Versalienzeilen mit Punktführung
(„Gebucht", „Tagesziel"), dann `.rest` — Label links, **die eine große Zahl** rechts
(`--d-zahl`), Einheit als Zweitdruck. Ohne kcal-Ziel trägt die Tagessumme selbst die
große Zahl und ein Hinweis verlinkt `/goals`. Überschreitung: Label und Zahl in `--red`.

Tabelle: `border-collapse`, rechtsbündige Werte, Kopfzeile `--t-label` mit 1px `--ink`
darunter, Zeilen 1px `dotted --rule`. Ist-Spalte 700, Offen-Spalte `--ink-2`, über Ziel
`--red`, fehlendes Ziel als Gedankenstrich in `--faint`. **Keine Balken, keine Ringe.**

### Statuszeilen und Leerzustand
`.status` ist `--t-print`/`--ink-2` und verschwindet, solange sie leer ist
(`:empty{display:none}`); `.status.error` ist rot. `.empty` ist zentrierter Zweitdruck in
`--faint` mit 26px Luft und gepunkteter Unterkante — dieselbe Linie wie eine
Positionszeile, damit die Leere wie ein leerer Druck aussieht und nicht wie ein Loch.

### Icons
Ausschließlich **inline-SVG**, `stroke-width` 1.6–2.2, `stroke-linecap/linejoin: round`,
15–16px. Keine Icon-Fonts, keine Emoji, keine Glyphen als Icon-Ersatz. Keine SVGs von
Hand malen, die komplexer sind als Grundformen.

### Browser-Flächen
Auch was der Browser stellt, gehört zur Gestaltung und ist im Bon gesetzt:
`::selection` (Fläche `--red`, Schrift `--paper`), `:focus-visible` (2px `--red`, 3px
Versatz), `::-webkit-scrollbar` (10px, Daumen `#2c5347` mit 2px Rand in `--table-dark`,
Spur `--table`-dunkel) und `font-variant-numeric: tabular-nums` global. Auf der Tischebene
wird `:focus-visible` lokal auf `--paper` überschrieben (siehe **Die Tisch-Ring-Regel**).

### Bewegung
**Ein gestalteter Moment:** die Buchung. Die Quittung fährt einmal ein
(`.38s cubic-bezier(.16,1,.3,1)`, 8px), und die frisch gebuchte Position leuchtet einmal
auf (`1.8s ease-out`, `--paper-2` → transparent). Dazu **eine Zustandsanzeige**: der rote
Punkt blinkt, solange wirklich aufgenommen wird (`1.4s steps(1,end)`), und sonst nie.
Zustandswechsel an Knöpfen laufen in `.12s ease-out`.

Bei `prefers-reduced-motion: reduce` sind alle Animationen und Übergänge global
abgeschaltet — **und jede Animation, die etwas sichtbar macht, hat einen Ruhezustand**:
`.pos--neu` bleibt auf `--paper-2`, der Aufnahmepunkt bleibt auf `opacity: 1`.

### Named Rules
**Die Stempel-Regel.** Knöpfe sind Stempelfelder mit harter 1,5px-Kontur. Es gibt keine
gefüllte Pille, keinen Verlauf, keinen Schatten an einem Knopf. Die Füllung ist ein
**Zustand** (Hover, `.ink`, Aufnahme), nie der Ruhezustand eines Angebots.

**Die Ein-Zahl-Regel.** `--d-zahl` erscheint **genau einmal** pro Ansicht. Eine zweite
große Zahl halbiert die erste.

**Die Ein-Moment-Regel.** Pro Ansicht wird **ein** Ereignis animiert — hier die Buchung.
Alles andere ist ein Zustandswechsel unter 150ms oder gar nichts.

## Do's and Don'ts

### Do:
- **Do** neue Bon-Oberflächen von `base_bon.html` erben lassen und ihr CSS inline im
  eigenen Template halten.
- **Do** Rang über Gewicht, Versalien, Punktführung und Linienstärke vergeben und dabei
  bei den sechs Grad-Tokens bleiben.
- **Do** `border-radius: 0` an jedem Knopf und jeder Eingabe explizit setzen.
- **Do** jede Papierfläche mit `var(--grain) repeat` unterlegen — auch randlose Blöcke.
- **Do** Spaltenkopf und Zeilen dieselbe `--pos-cols`-Variable teilen lassen.
- **Do** Werte als Tabelle oder Zeile mit Punktführung zeigen.
- **Do** jedes kleine Bedienelement unter `pointer: coarse` auf min. 44px bringen.
- **Do** randlose Blöcke im 430px-Block mit `-17px` nachziehen.
- **Do** `--faint` als Kontrastboden behandeln — darunter gibt es keine Textfarbe.
- **Do** für jede Animation einen Ruhezustand unter `prefers-reduced-motion` mitschreiben.
- **Do** eine Oberfläche, die keine durchgehende Rolle ist, über `{% block shell %}` bauen
  und Tokens, Knöpfe, Eingaben und Linien trotzdem aus `base_bon.html` beziehen.
- **Do** Text, der direkt auf dem Grün steht, in `--on-table`/`--on-table-faint` setzen und
  dort in `--paper` ringen.
- **Do** Betonung als Punktführung setzen (`underline dotted`, 3px, 8px Versatz).

### Don't:
- **Don't** Tokens der alten Welt (`--accent`, `--surface`, `--bg`, `--text`) in einem
  Bon-Template verwenden — und umgekehrt keine Bon-Tokens in `base.html`-Seiten.
- **Don't** einen siebten Schriftgrad, eine vierte Linienstärke oder eine neue Grundfarbe
  einführen.
- **Don't** `--red` für ein Angebot, einen Primärknopf oder eine Dekoration verwenden.
- **Don't** Fortschrittsbalken, Makro-Ringe, Donut-Charts oder gleich große Icon-Karten
  bauen. Der Bon rechnet, er visualisiert nicht.
- **Don't** einen Schatten innerhalb des Papiers setzen — keine Hover-Anhebung, kein
  Karten-Schatten, kein harter Versatz-Schatten.
- **Don't** eine zweite große Zahl auf dieselbe Ansicht drucken.
- **Don't** eine gesperrte Versalienzeile als **Eyebrow/Kicker über eine Überschrift**
  setzen. `--t-label` beschriftet Spalten, Felder und Blöcke; es kündigt keine Überschrift
  an. Die zentrierte Druckmarke der Rückfrage ist ein Abschnittsmarker des Bons und
  bleibt bei ihr.
- **Don't** Emojis, Icon-Fonts oder Glyphen als Icons verwenden — nur inline-SVG.
- **Don't** `#fff` oder einen Systemschriftschnitt als Display-Fallback einsetzen.
- **Don't** `fonts.googleapis.com` einbinden (siehe oben, LG München I).
- **Don't** eine Überschrift auf einer Persuade-Fläche in die Displayschrift setzen — die
  Displaygrade sind Größen, die Schrift bleibt Sometype Mono.
- **Don't** Betonung kursiv oder farbig setzen; sie ist die Punktführung.
- **Don't** den roten Fokusring auf der Tischebene stehen lassen (~2,4:1 gegen `--table`).
- **Don't** Papierfarben auf den Tisch tragen (oder `--on-table` aufs Papier).
- **Don't** die Bereichszeile horizontal scrollen lassen.

---

# Nicht migrierte Oberflächen (alte Welt, eingefroren)

**Gilt nur für Templates, die von `app/dashboard/templates/base.html` oder den
übrigen Landing-/Auth-Templates erben:** `/faq`, `/impressum`, `/datenschutz`, Auth
(`/login`, `/register`, `/reset-password`, …), der gesamte `/admin`-Bereich sowie
`/history`, `/goals`, `/recipes`, `/weight`, `/ai-log`, `/feedback`.

Die Landing Page `/` ist am 2026-09-19 als zweite Oberfläche auf den Bon umgezogen und
steht **nicht** mehr in dieser Liste.

Diese Welt wird **nicht weiterentwickelt** und **nicht mit dem Bon gemischt**. Sie wird
Seite für Seite umgestellt; bis eine Seite umgezogen ist, gelten für sie die Tokens und
Komponenten unten unverändert. Wer hier etwas repariert, repariert es in diesen Tokens.
Neue Muster entstehen nur im Bon.

## Fonts (alte Welt, selbst gehostet)
- **Newsreader** — Überschriften und Zahlenwerte (Serif, echte Kursiven für Betonung).
- **Inter** — Fließtext und UI.
- **Space Grotesk** — **ausschließlich** die Wortmarke (`_wordmark.html`), nie für
  UI-Text. Sie liegt nur bei, weil die Wortmarke als inline-`<text>` vorliegt; sobald der
  offene BRAND.md-Punkt erledigt ist (Text in Pfade umwandeln), fällt sie weg.

```html
<link rel="preload" href="/static/fonts/newsreader-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/static/fonts/inter-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/static/fonts.css">
```

Große typografische Momente in Newsreader; Betonung als `<em>` (kursiv, in `--accent`).

## Farb-Tokens (alte Welt — exakt, keine neuen Grundfarben)
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
Innerhalb der Palette darf man mutig werden: großflächige Accent-Blöcke, invertierte
Sektionen (Text auf `--accent`), dunkle Panels (Text auf `--text`). Nur keine neuen
Grundfarben.

### Tints auf invertierten Flächen
Auf `--text` und `--accent` als Fläche trägt keiner der Text-Tokens genug Kontrast.
**Keine neuen Grundfarben**, sondern dieselben Familien heller gezogen; die Liste ist
abgeschlossen.

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
--on-accent-muted:#f6d9cc;  /* sekundär */
--on-accent-subtle:#f0c3b1; /* tertiär, Einheiten */
```

`#fff` ist der einzige erlaubte Weißwert (nur alte Welt). Er gilt auf beiden Flächen für
Überschriften, Button-Text, große Zahlenwerte und Icons auf `--accent`. Fließtext nie in
`#fff`, dafür sind `--on-dark` und `--on-accent` da.

**Danger vs. Accent:** `--danger` ist ein dunklerer, rotstichigerer Ton derselben Familie.
Nur für Fehlertexte, Löschaktionen, erreichte Limits und Ziel-Überschreitung verwenden;
**nie für Buttons oder Flächen, die zu einer normalen Aktion einladen.**

## Komponenten (alte Welt)

Die Werte stammen ursprünglich aus `landing.html`. Diese Datei lebt seit dem
2026-09-19 im Bon; gültig sind sie nur noch für die Templates, die weiter von
`app/dashboard/templates/base.html` oder den Auth-Templates erben.
- **Button** `.btn`: Höhe 44px (`.lg` 54px), Radius 11–13px, `--accent` → Hover
  `--accent-hover`, leichter `translateY(-1px)`. Ghost: transparent, 1px `--border`.
- **Karte** `.card`: `--surface`, 1px `--border`, Radius 20px, Padding 32px; Hover hebt an
  (`translateY(-3px)` + weicher Schatten). Abgesetzt: `--surface-2`.
- **Icon-Badge**: 46px, Radius 13px, `--accent-soft` Hintergrund, `--accent` Icon.
- **Bestätigungs-Badge**: 26px, Kreis, `--accent` Hintergrund, Icon in `#fff`. Nur für den
  Abschluss einer Aktion, nie als Dekoration, nie mehr als eines pro Ansicht.
- **Invertierter Accent-Block**: Hintergrund `--accent`, Text
  `--on-accent`/`--on-accent-muted`, Radius 32px.
- **Bento-Grid**: `repeat(6,1fr)`, Karten spannen 2/3 Spalten; auf Mobile 1 Spalte.
- **Reveal-on-scroll** `.rv`: `IntersectionObserver`, bei reduced-motion sofort sichtbar.
- **Icons**: ausschließlich inline-SVG, `stroke-width` 2, `stroke-linecap/linejoin round`.

## Routen / CTAs (beide Welten)
- Primär-CTA im Seiteninhalt → `/register` („Jetzt registrieren"). In der Nav heißt
  derselbe Button nur „Registrieren" — bei 40px Höhe und neben der Wortmarke passt die
  lange Variante nicht, ohne auf 375px zu drängen.
- `/login` **nur** als dezenter Textlink („Schon dabei? Anmelden"), nie als zweiter großer
  Button neben dem Primär-CTA. In der Nav ist der schlichte Textlink erlaubt.
- Hinweis in `--text-subtle`: „Zugang aktuell nur mit Invite-Code." — **nur auf der
  Landing Page** (`.hero-note`/`.outro-note`). Auf `/register` steht derselbe Satz in
  `.auth-footer`; `--text-subtle` erreicht gegen `--surface` nur 2,62:1, deshalb gilt im
  Auth-Bereich `--text-muted`.

## Feature-Wording (beide Welten — nur diese, nichts dazuerfinden)
- Sprachaufnahme im Browser → transkribiert → Makros.
- Freitext-Eingabe in natürlicher Sprache, keine Dropdowns/Gramm-Angaben.
- Stellt eine kurze **Rückfrage**, wenn eine wichtige Angabe fehlt, statt eine Zahl zu
  erfinden — das Alleinstellungsmerkmal.
- Makroziele mit Tagesfortschritt, plus Auswertung Woche/Monat.
- Rezepte mit Makros pro Portion, Zutaten auch per Sprache.
- Verlauf mit Wochen-/Monatsansicht, Mahlzeiten nachträglich bearbeitbar.
- Gewichts-Log mit 7-Tage-Schnitt, Wochenveränderung und geschätztem Tagesverbrauch;
  daraus ein **Vorschlag** fürs kcal-Ziel — nie automatisch übernommen.
