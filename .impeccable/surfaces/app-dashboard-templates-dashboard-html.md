---
version: 1
slug: "app-dashboard-templates-dashboard-html"
primary_target: "app/dashboard/templates/dashboard.html"
related_targets: []
---

## Scope

Dashboard `/dashboard` (Heute-Ansicht und Rueckblick auf einen einzelnen Tag).
Modus: Operate. Gewaehlt vom Nutzer am 2026-09-28 aus zwei gebauten Mockups
(Vorschlag A "Naehrwerte" gegen B "Instrument"). Ersetzt den Tagesbon, den der Nutzer
als zu metaphorisch, zu dunkel, schwer lesbar und "nicht wie ein Produkt" verworfen hat.
Alle Oberflaechen (Landing, FAQ, Rechtliches, Auth, Admin, Verlauf, Ziele, Rezepte,
Gewicht, KI-Log, Feedback) wurden am selben Tag auf `base_app.html` umgestellt;
`base.html`, `base_bon.html` und `_wordmark.html` sind geloescht.

## Direction contract

THESIS: Der Tag ist eine Naehrwerttabelle, wie sie auf jeder Verpackung steht — eine
Form, die jeder lesen kann, ohne dass sie ein Kostuem ist. Verweigert: Makro-Ringe,
gefuellte Balken, Kartenraster mit Icons, und jede Materialmetapher (Papier, Tisch, Bon).

OWN-WORLD: Weisser Grund, Schwarz #0f0f0d, zwei Grauebenen, Haarlinie #dcdcd6. Kobalt
#1f3fd1 nur fuer die Sprachtaste, Fokus und die frisch gebuchte Zeile. Rot #b3261e nur
fuer Fehler und laufende Aufnahme. Archivo: normale Breite fuer Text, schmal (70–72 %)
und 800–900 fuer Ueberschrift und die eine grosse Zahl. Rang aus Linienstaerke der
Tabelle (12px-Balken, 5px, 3px, 1px schwarz, Haarlinie) und Gewicht. Rechte Winkel.
Ueberschreitung = Schraffur plus Wort "über Ziel", nie nur Farbe.

STORY: Ich sehe sofort, wie viel heute noch offen ist, und darunter Energie und Makros
als Gegessen / Ziel / Offen. Ich tippe oder spreche unten am Daumen; fehlt eine Angabe,
steht die Rueckfrage direkt ueber dem Feld, hoechstens zwei.

FIRST VIEWPORT: Mobil: Kopfzeile (Wortmarke links, Tageswechsel rechts), 5 Bereiche als
Unterstreich-Tabs, darunter der schwarz gerahmte Kasten "Nährwerte" mit Datum, dickem
Balken, "Noch offen" und der grossen Zahl rechts, dann die Tabelle. Eingabefeld und
quadratische Kobalt-Sprachtaste fest unten. Desktop: links Eingabe + Mahlzeiten, rechts
der Kasten sticky.

FORM: Naehrwertkennzeichnung auf Verpackungen, Kandidat 1 der eigenen Liste
(IMPECCABLE'S PICK gegen die gewuerfelte Richtung 3 "Instrument"); Seed-Key 7a6acee1,
Scope direction, Mode operate. Erhebung aus dem Camcorder-Sucher (abgelehnt):
Ueberschreitung traegt eine Textur, nicht nur eine Farbe.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Offene Entscheidungen

- Wortmarke: im Kopf als Text in Archivo 800 gesetzt; die SVG-Wortmarke traegt noch die
  Farben der alten Welt. Umzeichnen oder neue Farbvariante — vor dem Launch klaeren.
- Favicon `static/brand/macromic-mark.svg` traegt noch Terrakotta auf Creme (alte Welt) —
  Markenentscheidung, mit der Wortmarke zusammen klaeren.
