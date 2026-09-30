---
name: MacroMic
description: Voice-first Ernährungslog — der Tag als Nährwerttabelle, wie sie auf jeder Verpackung steht.
colors:
  white: "#ffffff"
  ink: "#0f0f0d"
  ink-2: "#45453f"
  faint: "#6b6b64"
  hair: "#dcdcd6"
  tint: "#f3f3ef"
  cobalt: "#1f3fd1"
  cobalt-deep: "#1733b5"
  cobalt-soft: "#eef1fd"
  red: "#b3261e"
  red-soft: "#fbeceb"
typography:
  zahl:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "76px"
    fontWeight: 800
    lineHeight: 0.82
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
    fontVariation: "'wdth' 70"
  seitenkopf:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "44px"
    fontWeight: 900
    lineHeight: 0.95
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 72"
  abschnitt:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 800
    lineHeight: 1.15
    fontVariation: "'wdth' 85"
  betont:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.3
  text:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.45
  bedienung:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.45
  meta:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  rohdaten:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  none: "0"
spacing:
  gut: "20px"
  gut-desktop: "32px"
  gut-375: "16px"
  block: "28px"
  spalte: "56px"
  wide: "1120px"
  narrow: "760px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    typography: "{typography.text}"
    rounded: "{rounded.none}"
    padding: "0 18px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "#2b2b27"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 18px"
    height: "44px"
  button-line-hover:
    backgroundColor: "{colors.tint}"
  button-sm:
    typography: "{typography.bedienung}"
    padding: "0 14px"
    height: "40px"
  button-cta:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    typography: "{typography.betont}"
    rounded: "{rounded.none}"
    padding: "0 24px"
    height: "56px"
  voice-key:
    backgroundColor: "{colors.cobalt}"
    textColor: "{colors.white}"
    rounded: "{rounded.none}"
    size: "56px"
  voice-key-hover:
    backgroundColor: "{colors.cobalt-deep}"
  voice-key-recording:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
  link-button:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    typography: "{typography.meta}"
    padding: "6px 0"
  input-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.text}"
    rounded: "{rounded.none}"
    padding: "10px 12px"
    height: "48px"
  nav-tab:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    typography: "{typography.bedienung}"
    padding: "10px 0 11px"
  nav-tab-active:
    textColor: "{colors.ink}"
  kasten:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 14px 14px"
  quittung:
    backgroundColor: "{colors.cobalt-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px 16px 16px"
  notice:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.ink}"
    typography: "{typography.bedienung}"
    padding: "12px 14px"
  notice-error:
    backgroundColor: "{colors.red-soft}"
    textColor: "{colors.ink}"
  notice-ok:
    backgroundColor: "{colors.cobalt-soft}"
    textColor: "{colors.ink}"
---

# Design-System — MacroMic

Referenz für alle UI-Arbeiten. Farben, Schriften, Komponenten und Regeln hier sind
verbindlich — **nichts dazuerfinden.**

Es gibt **eine** Welt: die Nährwert-Oberfläche. Jedes Template erbt von
`app/dashboard/templates/base_app.html` (Admin über `admin_base.html`, das die Navigation
ersetzt, sonst aber dieselben Tokens und Bausteine nutzt). Der Tagesbon und die alte
Creme-/Newsreader-/Terrakotta-Welt sind am 2026-09-28 gelöscht worden
(`base.html`, `base_bon.html`, `_wordmark.html`, `fonts.css`, `fonts-bon.css`). Ihre
Tokens (`--paper`-Grain, `--table`, `--accent`, `--surface` …) gibt es nicht mehr — wer sie
in einem alten Branch, einem Mockup oder einer Erinnerung findet, übernimmt sie nicht.

Der Direction contract mit Begründung steht in
`.impeccable/surfaces/app-dashboard-templates-dashboard-html.md`. Die Tokenwerte oben
(Frontmatter) sind normativ; die Namen im Text verweisen auf die Custom Properties in
`base_app.html` (`--bg`, `--ink`, `--blue`, …).

## Regeln, die überall gelten

- **Alles ist Deutsch** — UI-Texte, Fehlermeldungen, `detail`-Strings auf `HTTPException`.
  Einige davon werden dem Nutzer unverändert angezeigt.
- Ton: direkt, selbstbewusst, leicht trocken. **Du-Ansprache.** Kein Marketing-Sprech,
  keine Superlative, **keine Emojis**. **Kein Dark Mode.**
- Responsive bis **375px** runter, **kein horizontales Scrollen** der Seite. Breite
  Admin-Tabellen scrollen in ihrem eigenen `.tab-scroll`, nie die Seite.
- Animationen nur CSS-basiert; `prefers-reduced-motion: reduce` wird **immer**
  respektiert — global im Shell (`*{animation:none!important;transition:none!important}`),
  und jede Animation, die etwas sichtbar macht, hat einen Endzustand, der ohne sie
  steht (Aufnahmepunkt `opacity:1`, Landing-Demo sofort vollständig).
- CSS steht **inline pro Template**. Ausnahmen unter `/static`: die Brand-Assets
  ([BRAND.md](BRAND.md)) und die selbst gehostete Schrift (`app/static/fonts-app.css`,
  Dateien in `app/static/fonts/`).
- **Nie** von `fonts.googleapis.com` einbinden. Das CDN überträgt die IP-Adresse jedes
  Besuchers an Google, bevor irgendjemand zugestimmt hat — genau der Punkt aus
  **LG München I, 20.01.2022 (3 O 17493/20)**. Die Datenschutzerklärung sagt zu, dass
  kein Dritter eine IP sieht; ein Template, das zum CDN greift, macht diese Seite
  stillschweigend zur Lüge. `fonts-app.css` ist aus dem css2-Endpunkt generiert und
  unverändert; wer etwas ändert, erzeugt Datei und CSS neu, statt von Hand zu editieren.
  Einbindung (steht im Shell, nicht wiederholen):

```html
<link rel="preload" href="/static/fonts/archivo-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/static/fonts-app.css">
```

- **Zahlen sind deutsch.** Dezimalkomma über die Jinja-Filter `de_num` (Schätzwerte: runde
  Zahl ohne `,0`) und `de_fixed` (Messwerte wie Gewicht: `71,0 kg` behält die Stelle);
  fehlender Wert ist ein Geviertstrich `—`. Ein negativer Wert trägt das **echte
  Minuszeichen `−` (U+2212)**, nie den Bindestrich; ein positiver Trend das `+`.

## Overview

**Creative North Star: „Die Nährwerttabelle"**

Der Tag ist eine Nährwertkennzeichnung, wie sie auf jeder Verpackung steht — eine Form,
die jeder lesen kann, ohne dass sie ein Kostüm ist. Weißer Grund, schwarze Schrift,
schwarze Balken. Rang entsteht aus der **Linienstärke der Tabelle** (12px, 5px, 3px, 1px
Schwarz, Haarlinie) und aus **Gewicht und Breite** einer einzigen variablen Schrift, nicht
aus Farbe oder Fläche. Die Seite sagt sofort, wie viel heute noch offen ist; darunter
Energie und Makros als Gegessen / Ziel / Offen.

Es ist ein Produkt, keine Metapher: kein Papier, kein Tisch, kein Bon, keine Körnung, kein
Schatten. Die Dichte ist die einer Tabelle — Haarlinien statt Kästen, Zeilen statt
Karten. Genau ein schwarz gerahmter Kasten pro Ansicht trägt die Zusammenfassung, um die
sich die Seite dreht.

Verweigert werden Makro-Ringe, gefüllte Fortschrittsbalken, Kartenraster mit Icons und
jede Materialmetapher. Farbe ist knapp: Kobalt markiert die Sprachtaste und was gerade
passiert (Fokus, frisch gebucht), Rot was falsch ist oder gerade aufnimmt.

**Key Characteristics:**
- Weißer Grund, Schwarz `#0f0f0d`, zwei Grauebenen, eine Haarlinie.
- Eine Schrift: Archivo variabel — normale Breite für Text, schmal (70–72 %) und 800–900
  für Seitenkopf und die eine große Zahl.
- Rang aus Linienstärke und Gewicht; rechte Winkel ohne Ausnahme außer dem Aufnahmepunkt.
- Ein Kasten pro Ansicht, sonst Tabellen und Zeilen mit Haarlinien.
- Kobalt nur für Sprachtaste, Fokus und „gerade gespeichert"; Primärknöpfe sind schwarz.
- Überschreitung ist Schraffur plus Wort „über Ziel", nie nur Farbe.

## Colors

Schwarz auf Weiß mit zwei Grauebenen; zwei Signalfarben, beide knapp, beide mit je einer
hellen Fläche. Mehr Grundfarben gibt es nicht.

### Primary
- **Kobalt** (`--blue`): die Sprachtaste (Dashboard, Rezepte, Demo-Taste der Landing
  Page), der Fokusring (`:focus-visible` 2px mit 2px Versatz; an Feldern Kante plus
  1px-Ring), `::selection`, die Einfügemarke (`caret-color`), die Marke „Gebucht" und die
  Uhrzeit der frisch gebuchten Zeile, „Gespeichert" auf `/goals`.
- **Kobalt tief** (`--blue-2`): nur Hover der Sprachtaste.
- **Kobalt hell** (`--blue-soft`): die Quittung nach einer Buchung, die frisch gebuchte
  Zeile, der Erfolgshinweis (`.notice.ok`).

### Secondary
- **Signalrot** (`--red`): Fehlertext (`.status.error`), Fehlerhinweis-Kante, der
  blinkende Aufnahmepunkt, gesperrte Credits, fehlgeschlagene KI-Anfragen, und der
  Hover einer Löschen-Aktion.
- **Rot hell** (`--red-soft`): Fläche hinter `.notice.error` und dem Verifizierungs-Banner,
  jeweils mit 1px-Kante in `--red`.

### Neutral
- **Weiß** (`--bg`): Seitengrund, Feldgrund, Schrift auf Schwarz und Kobalt.
- **Schwarz** (`--ink`): Schrift, Rahmen, die Tabellenbalken, Primärknöpfe, aktiver Reiter.
- **Grau 2** (`--ink-2`): zweite Ebene — sekundärer Text, Werte ohne Gewicht (Gegessen,
  Ziel), Feld-Labels, inaktive Reiter.
- **Grau 3** (`--faint`): dritte Ebene — Meta, Einheiten, Uhrzeiten, Platzhalter, Fußzeile.
  5,4:1 auf Weiß; **tiefer gibt es keine Textfarbe.**
- **Haarlinie** (`--hair`): Trennung zwischen Zeilen, deaktivierte Kanten, Scrollbar-Daumen.
- **Ruhefläche** (`--tint`): Hover von Zeilen und Umriss-Knöpfen, neutraler Hinweis,
  Rohdaten-Block im Admin.

### Named Rules
**Die Schwarze-Taste-Regel.** Kobalt ist die Farbe der **Sprachtaste** und dessen, was
gerade passiert (Fokus, frisch gebucht, gerade gespeichert). Ein Primärknopf ist
**schwarz** — auch „Jetzt registrieren" auf der Landing Page, auch „Speichern". In einem
Viewport gibt es höchstens eine Kobaltfläche. Test: Ist die kobaltblaue Stelle eine
Sprachtaste, ein Fokus oder die Bestätigung einer Aktion, die gerade eben passiert ist?
Wenn nein, ist sie schwarz.

**Die Rot-Regel.** `--red` sagt „falsch", „gesperrt", „wird gelöscht" oder „nimmt gerade
auf". Ein Angebot, ein Ziel, eine Überschreitung sind nie rot. Die laufende Aufnahme
färbt nicht die Taste (die wird schwarz), sondern trägt den roten Punkt im Feld daneben.

**Die Keine-neuen-Grundfarben-Regel.** Die Liste oben ist abgeschlossen. Eine zusätzliche
Fläche wird aus `--tint` oder einer Linie gebaut, nicht aus einem neuen Ton.

## Typography

**Schrift:** Archivo (variabel, Gewicht 100–900, Breite 62–125 %), mit `ui-sans-serif`,
`system-ui`, `sans-serif`. Selbst gehostet, latin und latin-ext.
**Rohdaten:** `ui-monospace, SFMono-Regular, Menlo, monospace` — nur Admin.

**Character:** Eine Grotesk in zwei Lagen. Normale Breite liest sich wie der Fließtext
einer Verpackung; schmal und schwer ist sie die fette Überschrift „Nährwerte" und die Zahl,
die man aus einem Meter Entfernung liest. Ziffern stehen als Tabellenziffern
(`tabular-nums`) überall, wo Zahlen untereinander stehen.

### Hierarchie
- **Zahl** (`--t-xxl` 76px, 66px unter 380px; 800, Breite 70 %, Zeilenhöhe .82,
  −.02em; Einheit dahinter auf 24px/700/85 %): die eine große Zahl — „Noch offen" im
  Dashboard, Ø pro erfasstem Tag im Verlauf, aktuelles Gewicht.
- **Seitenkopf** (`--t-xl` 44px, 56px ab 960px; 900, Breite 72 %, Zeilenhöhe .95,
  −.01em): genau ein `.page-h` pro Seite; im Dashboard „Nährwerte" im Kasten (52px ab
  960px). Der Kastenkopf `.kasten-h` ist dieselbe Lage in 28px.
- **Abschnitt** (`--t-l` 24px; 800, Breite 85 %): `.sec-h` über 2px Schwarz, Zähler rechts
  in 15px/500/`--faint`.
- **Betont** (`--t-m` 18px; 700–800): Rückfrage, Buchungstitel, kcal einer Zeile,
  Energiezeile der Tabelle, Label neben der großen Zahl.
- **Text** (`--t-b` 16px; 400, Zeilenhöhe 1.45): Lesetext und jede Eingabe, max. 62ch.
- **Bedienung** (15px; 500, aktiv 700): Reiter, Kopf-Links, kleine Knöpfe, Hinweise,
  Unterzeilen. Im Build ein Literal, kein Custom Property — ein echter, geteilter Grad.
- **Meta** (`--t-s` 13px): Makrozeile, Uhrzeit-Meta, Feld-Labels (600, `--ink-2`),
  Tabellenkopf (700), Fußzeile, Credits.

Auf der Landing Page (Persuade-Fläche) dürfen Aufmacher und Abschnittsköpfe dieselbe
schmale, schwere Lage größer tragen: Aufmacher `clamp(50px,14vw,92px)` bzw. 76–96px ab
900px, Abschnitt `clamp(36px,9vw,56px)`. Das sind die einzigen `clamp()`-Grade im System.

### Named Rules
**Die Zwei-Lagen-Regel.** Schmal (70–85 %) und 800–900 nur für Seitenkopf, Kastenkopf,
Abschnittskopf und die eine Zahl. Alles andere steht in normaler Breite. Eine schmale
Fließtextzeile ist ein Fehler.

**Die Ein-Zahl-Regel.** `--t-xxl` erscheint **genau einmal** pro Ansicht. Eine zweite große
Zahl halbiert die erste.

**Die Rohdaten-Regel.** Monospace gibt es nur für echte Rohdaten: die Prompt-/Antwort-Dumps
im Admin (`.log-text`). Codes und Variablennamen stehen in Archivo 600 mit
`tabular-nums slashed-zero` und .04em Sperrung, nicht in Monospace.

**Die Keine-Versalien-Regel.** Beschriftungen stehen in gemischter Schreibung. Es gibt
keine gesperrten Versalienzeilen und keine Eyebrows über Überschriften.

## Layout

Eine Spur, zentriert: `--wide` 1120px mit `--gut` Seitenrinne (20px; 32px ab 960px; 16px
unter 380px). Lese- und Formularseiten (Auth, FAQ, Rechtliches, Ziele, Feedback) nutzen
`.page.narrow` mit 760px. Blöcke in `.page` stehen 28px auseinander.

**Seite mit Kasten** (Dashboard, Gewicht): mobil untereinander; ab 960px zwei Spalten
`1fr 400px` mit 56px Spaltenabstand, der Kasten rechts. Im Dashboard ist er `sticky`
(24px), links stehen Eingabe und Mahlzeiten. Mobil steht im Dashboard die Eingabe als
**Dock fest unten** am Daumen (2px schwarze Oberkante, `safe-area-inset-bottom`), ab 960px
wandert sie statisch über die Mahlzeiten. Eine gerade entstandene Quittung steht mobil
über dem Kasten.

**Landing Page:** ab 900px zweispaltig (Aufmacher `1.05fr .95fr`, Abschnitte `.9fr
1.1fr`, Funktionen `1fr 1fr`), Abschnitte durch 8px Schwarz getrennt.

Formulare: `.felder` als Raster mit 14px Abstand, `.zwei` (unter 560px einspaltig) und
`.vier` (unter 560px zweispaltig). Aktionen als umbrechende Zeile, 8px/12px Abstand.

Breakpoints sind Abfragen, kein Set: 960px (Spalten, Rinne, Seitenkopf), 900px (Landing),
560px (Formularraster, Verlauf blendet die Mahlzeiten-Spalte aus), 430px
(Korrekturfelder 4 → 2), 380px (Rinne, große Zahl, Reiter 14px), `pointer: coarse`
(jedes kleine Bedienelement auf 44px).

### Named Rules
**Die 375px-Regel.** Fünf Bereiche passen auf 375px in eine Zeile, weil sie Wörter sind und
keine Icons. Wird es enger, **bricht die Navigation um**, sie scrollt nicht. Tabellen
verlieren am Handy lieber eine redundante Spalte, als quer zu scrollen.

## Elevation & Depth

Das System ist **flach**. Es gibt keinen `box-shadow` außer dem 1px-Fokusring an Feldern
(`0 0 0 1px` in Kobalt) — der ist eine Kantenverstärkung, keine Erhebung. Tiefe entsteht
aus Linienstärke, einem schwarzen Rahmen um den einen Kasten und Flächen in `--tint`
bzw. `--blue-soft`. Sticky-Kasten und Dock heben sich nicht ab; das Dock trennt sich mit
2px Schwarz.

### Named Rules
**Die Keine-Erhebung-Regel.** Kein Schatten, keine Hover-Anhebung, kein Versatz-Schatten,
kein Verlauf. Was sich absetzen soll, bekommt eine Linie.

## Shapes

**Rechtwinklig, ausnahmslos.** `border-radius: 0` an Knöpfen, Feldern und Selects ist
explizit gesetzt. Einziger Kreis ist der 10px-Aufnahmepunkt — eine Leuchte, kein Kasten.

Die Linien sind die Grammatik der Nährwertkennzeichnung, von oben nach unten im Rang:
- **12px Schwarz** — unter dem Kopf des Kastens „Nährwerte" (Dashboard, Landing-Demo).
- **8px Schwarz** — unter dem Kopf eines anderen Kastens (`.kasten-h`: Verlauf, Gewicht);
  auf der Landing Page zwischen den Abschnitten.
- **5px Schwarz** — unter der großen Zahl.
- **3px Schwarz** — unter der Energiezeile einer Nährwerttabelle; aktiver Reiter.
- **2px Schwarz** — Kastenrahmen; Oberkante jeder Liste (`.sec-h`, Ablauf, KI-Log);
  Tabellenfuß mit Summe; Dock.
- **1,5px Schwarz** — Kante von Feldern und Knöpfen.
- **1px Schwarz** — unter dem Tabellenkopf; über der Fußnote im Kasten.
- **1px Haarlinie** (`--hair`) — zwischen Zeilen, unter der Navigation, Fußzeile.

Die **Schraffur** (`--hatch`, −45°, 5px frei / 2px Schwarz bei 14 %) ist die einzige Textur.

### Named Rules
**Die Linienrang-Regel.** Eine Linie ist nie Dekoration: ihre Stärke sagt, wie weit oben
in der Tabelle man steht. Keine neue Stärke, keine gestrichelte oder gepunktete Linie,
keine vertikalen Seitenbalken.

## Components

### Buttons
Schwarz, rechtwinklig, fett — die Drucktaste einer Verpackung, keine Pille.
- **Primär** (`.btn`): Fläche und Kante Schwarz, Schrift Weiß 700, min. 44px, 0/18px.
  Hover `#2b2b27`, `.15s ease-out`. `:disabled` 40 %.
- **Umriss** (`.btn.line`): transparent, 1,5px Schwarz; Hover `--tint`. Zweite Wahl
  („Zurück"/„Weiter", „Abbrechen", Quittung „Korrigieren").
- **Klein** (`.btn.sm`): 40px, 15px Schrift, 0/14px.
- **CTA** (`.btn.cta`, Landing): 56px, 0/24px, 18px — **schwarz**, „Jetzt registrieren".
  In der Kopfzeile heißt derselbe Knopf nur „Registrieren" (`.btn.sm`). `/login` steht
  nie als zweiter großer Knopf daneben, sondern als Textlink („Schon dabei? Anmelden").
- **Textknopf** (`.link-btn`): 13px `--ink-2`, Unterstreichung in `--hair`, Hover Schwarz —
  für Aktionen im Satz („Abmelden", „Korrigieren", „Mail erneut senden"). Unter
  `pointer: coarse` 44px hoch.
- **Löschen**: 40px-Quadrat mit 1px `--hair`-Kante und Mülleimer-SVG in `--faint`;
  Hover Kante und Symbol `--red`.

### Sprachtaste (Signatur)
56px-Quadrat in Kobalt, weißes Mikrofon-SVG 26px, rechts neben dem Eingabefeld. Hover
`--blue-2`, deaktiviert `--hair`. **Während der Aufnahme wird sie zur schwarzen
Stopptaste**, und an Stelle des Feldes steht die Aufnahmezeile: 1,5px Schwarz, roter
Punkt (blinkt `1.2s steps(1,end)`), Text 600, Laufzeit rechts in Tabellenziffern. Dieselbe
Taste steht im Dashboard-Dock, bei den Zutaten auf `/recipes` und als Abbild in der
Landing-Demo — nirgends sonst.

### Inputs / Fields
- **Stil** (`.feld`): Label darüber (13px/600/`--ink-2`), Feld 48px, 1,5px Schwarz,
  Weiß, 10px/12px, 16px Schrift; Hinweis darunter 13px `--faint`. Select mit eigenem
  Chevron-SVG. Textarea ab 110px, vertikal ziehbar. Einheit (`kcal`, `g`) rechts im Feld
  in 15px `--faint`.
- **Eingabezeile** (Dashboard/Rezepte): 56px, Feld mit Pfeil-Sendeknopf (48px) innen
  rechts, daneben die Sprachtaste.
- **Fokus:** Kante Kobalt plus 1px-Ring (`box-shadow: 0 0 0 1px`); sonst global
  `:focus-visible` 2px Kobalt, 2px Versatz.
- **Deaktiviert:** Kante `--hair`, Schrift `--faint`. Checkbox/Radio 18px, `accent-color`
  Schwarz. Platzhalter sind Beispiele, keine Labels.

### Navigation
Kopfzeile: Wortmarke „MacroMic" als **Text** (Archivo 800, 18px) links; rechts der
Tageswechsel (Dashboard) bzw. FAQ/Anmelden/Registrieren (öffentlich). Darunter angemeldet
fünf Bereiche als **Unterstreich-Reiter**: Heute, Verlauf, Gewicht, Rezepte, Ziele —
15px/500/`--ink-2`, aktiv Schwarz 700 mit 3px schwarzer Unterkante auf der Haarlinie.
Dieselbe Geste trägt der Woche/Monat-Umschalter im Verlauf. Admin ersetzt die Reiter
durch eigene (`_admin_bar.html`) und markiert sich mit dem Wort „Admin" in `--faint`
neben der Wortmarke — keine eigene Palette. Fußzeile: 1px Haarlinie, 13px, Links in
`--ink-2`.

### Der Kasten (Signatur)
2px schwarzer Rahmen, 12px/14px/14px innen, **höchstens einer pro Ansicht**, für die
Zusammenfassung, um die sich die Seite dreht. Aufbau wie auf der Verpackung: Kopf
(Seitenkopf-Lage), Unterzeile in 15px `--ink-2`, dicker Balken, Label links + große Zahl
rechts über 5px, Tabelle, Fußnote über 1px Schwarz in 13px `--faint`.
- **Nährwerttabelle:** Kopf 13px/700 rechtsbündig über 1px Schwarz, Nährwert links 700
  mit Einheit in 13px `--faint`, Werte rechtsbündig in `--ink-2`, Offen-Spalte Schwarz 800,
  Energiezeile 18px über 3px Schwarz, Haarlinien zwischen den Makros. Fehlendes Ziel:
  Geviertstrich in `--faint`, der Kasten verlinkt `/goals`.
- **Überschreitung (nur Dashboard):** Zelle bzw. große Zahl mit Schraffur hinterlegt, Wert
  mit `+`, darunter das Wort „über Ziel". Nur dort, wo es für **denselben Tag** ein Ziel
  gibt.

### Tabellen und Zeilen
`.tab`: Kopf 13px/700 über 1px Schwarz, Zeilen 10px mit Haarlinie, Zahlen rechtsbündig in
Tabellenziffern, Hover `--tint` bei klickbaren Zeilen, Summe im Fuß über 2px Schwarz/800.
Admin verdichtet auf 15px, 8px Zeilen, kein Umbruch, Freitext-Zellen dürfen umbrechen.
**Mahlzeitenzeile:** Uhrzeit 15px `--faint` in einer 48px-Spur, Beschreibung 500, kcal
rechts 800/18px, darunter die Makrozeile 13px `--faint` mit Werten in 600/`--ink-2`
(„22 g Eiweiß · 20 g KH · 1 g Fett"), rechts „Korrigieren".

### Quittung und frisch gebucht
Nach einer Buchung: Fläche `--blue-soft`, 14/16px, Marke „Gebucht" mit Haken-SVG in Kobalt
700, Titel 18px/700, Werte 13px, `.btn.line` „Korrigieren" auf Weiß. Fährt einmal ein
(`.5s cubic-bezier(.16,1,.3,1)`, 6px). Die neue Zeile in der Liste liegt auf
`--blue-soft`, ihre Uhrzeit in Kobalt 700.

### Rückfrage
Steht direkt über dem Feld, in dem sie beantwortet wird, und ersetzt solange das
Eingabefeld: „Du:"-Zeile 13px `--faint`, Frage 18px/700, max. 40ch, Zähler 13px. Höchstens
zwei.

### Hinweise und Zustände
`.notice` 12/14px, 15px auf `--tint`; `.error` `--red-soft` mit 1px `--red`; `.ok`
`--blue-soft`. `.status` 13px `--ink-2`, verschwindet leer, `.error` rot 600, `.ok`
(Ziele) Kobalt 600. `.empty`: 22px Luft, `--faint`, Haarlinie darunter. Admin-Zustände
sind Text, keine Pillen: aktiv Schwarz 600, erledigt `--faint`, Fehler rot.

### Icons
Nur inline-SVG (`svg.i`): 22px, `stroke-width` 1.8 (2.2–2.4 bei 16–20px), runde Enden,
`currentColor`. Keine Icon-Fonts, keine Emoji, keine Glyphen als Icon.

### Diagramm (Gewicht)
Linie Schwarz 2px, Punkte `--faint`, Raster `--hair`. Achsenbeschriftung als HTML in 13px
Tabellenziffern neben dem SVG, weil sie im `viewBox` auf 7px schrumpfen würde.

### Bewegung
Ein Moment pro Ansicht: im Dashboard die Quittung, auf der Landing Page Frage, Antwort
und Kasten, die dem Beispielsatz folgen (`.45s`, Verzögerung .5/1.3/2s). Dazu der
blinkende Aufnahmepunkt, solange wirklich aufgenommen wird. Zustandswechsel an Knöpfen
`.15s ease-out`. Alles unter `prefers-reduced-motion` aus, Endzustand steht.

## Do's and Don'ts

### Do:
- **Do** jedes Template von `base_app.html` erben lassen und nur dessen Tokens und
  Bausteine (`.page`, `.page-h`, `.sec-h`, `.kasten`, `.big`, `.feld`, `.felder`, `.tab`,
  `.notice`, `.btn`, `.link-btn`, `.status`, `.empty`) verwenden; eigenes CSS inline im
  Template.
- **Do** Primärknöpfe schwarz setzen; Kobalt bleibt der Sprachtaste, dem Fokus und dem
  „gerade gespeichert".
- **Do** Rang über Linienstärke (12/8/5/3/2/1px, Haarlinie) und Gewicht vergeben.
- **Do** Zahlen in `tabular-nums`, rechtsbündig, mit `de_num`/`de_fixed` und echtem `−`.
- **Do** eine Überschreitung mit Schraffur **und** dem Wort „über Ziel" zeigen — nur wo
  ein Ziel für denselben Tag existiert.
- **Do** im Verlauf Durchschnitte nur über **erfasste Tage bis heute** bilden; leere und
  künftige Tage drücken sonst die eine große Zahl.
- **Do** jedes kleine Bedienelement unter `pointer: coarse` auf min. 44px bringen.
- **Do** `--faint` als Kontrastboden behandeln.

### Don't:
- **Don't** vergangene Tage im Verlauf am **heutigen** Ziel messen. Kein „über Ziel", keine
  Häkchen „Ziel erreicht", keine Adherence-Quote pro Tag — das Ziel kann seitdem geändert
  worden sein. Das ist Absicht (Kommentar in `dashboard/router.py`, `/history`), kein
  vergessenes Feature; nicht „reparieren".
- **Don't** Kobalt für einen Primärknopf, einen Link, eine Überschrift oder Dekoration
  verwenden.
- **Don't** Rot für ein Angebot oder eine Überschreitung verwenden.
- **Don't** Makro-Ringe, gefüllte Fortschrittsbalken, Donut-Charts oder Kartenraster mit
  Icons bauen.
- **Don't** einen zweiten Kasten oder eine zweite große Zahl in dieselbe Ansicht setzen.
- **Don't** Schatten, Radius, Verlauf, Körnung oder eine Materialmetapher (Papier, Tisch,
  Bon) einführen.
- **Don't** Monospace außerhalb echter Rohdaten verwenden.
- **Don't** gesperrte Versalienzeilen oder Eyebrows über Überschriften setzen.
- **Don't** Emojis, Icon-Fonts oder Glyphen als Icons verwenden.
- **Don't** `fonts.googleapis.com` einbinden (siehe oben, LG München I).
- **Don't** Tokens der gelöschten Welten (`--paper`, `--table`, `--accent`, `--surface`,
  Sometype Mono, Big Shoulders, Newsreader, Inter) wiederbeleben.

## Feature-Wording (nur diese, nichts dazuerfinden)
- Sprachaufnahme im Browser → transkribiert → Makros.
- Freitext-Eingabe in natürlicher Sprache, keine Dropdowns/Gramm-Angaben.
- Stellt eine kurze **Rückfrage**, wenn eine wichtige Angabe fehlt, statt eine Zahl zu
  erfinden — das Alleinstellungsmerkmal.
- Makroziele mit Tagesstand, plus Auswertung Woche/Monat.
- Rezepte mit Makros pro Portion, Zutaten auch per Sprache.
- Verlauf mit Wochen-/Monatsansicht, Mahlzeiten nachträglich bearbeitbar.
- Gewichts-Log mit 7-Tage-Schnitt, Wochenveränderung und geschätztem Tagesverbrauch;
  daraus ein **Vorschlag** fürs kcal-Ziel — nie automatisch übernommen.
- „Zugang aktuell nur mit Invite-Code." steht, solange Codes nötig sind, auf der Landing
  Page neben dem CTA und auf `/register` als Feldhinweis.

## Offene Entscheidungen
- **Wortmarke und Favicon.** Im Kopf steht die Wortmarke als Text in Archivo 800. Die
  SVGs in `app/static/brand/` (Wortmarken und `macromic-mark.svg`, das als Favicon
  eingebunden ist) tragen noch Terrakotta auf Creme aus der gelöschten alten Welt;
  [BRAND.md](BRAND.md) ist entsprechend veraltet. Umzeichnen oder neue Farbvariante —
  Markenentscheidung, vor dem Launch klären. Bis dahin: nicht auflösen, die SVG-Farben
  nicht in die Oberfläche übernehmen.
- **Space Grotesk** liegt nur noch unter `app/static/fonts/`, weil die Wortmarken-SVGs sie
  als inline-`<text>` brauchen. Nie für UI-Text; fällt mit der Markenentscheidung weg.

## Detector-Ausnahmen
`.impeccable/config.json` unterdrückt die Regel `side-tab` für `dashboard.html`,
`history.html`, `weight.html` und `landing.html`. Gemeldet werden dort die horizontalen
12px/5px/3px-Balken der Nährwerttabelle über die volle Breite — die Grammatik dieser Welt,
kein Seitenakzent. Die Ausnahme ist **Absicht**. Ein echter vertikaler Seitenbalken bleibt
verboten (siehe Die Linienrang-Regel); wer eine neue Datei ausnimmt, prüft vorher, dass es
wirklich nur volle Breite ist.
