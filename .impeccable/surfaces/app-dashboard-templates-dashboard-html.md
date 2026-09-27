---
version: 1
slug: "app-dashboard-templates-dashboard-html"
primary_target: "app/dashboard/templates/dashboard.html"
related_targets: []
---

## Scope

Dashboard `/dashboard` (Heute-Ansicht und Rueckblick auf einen einzelnen Tag).
Modus: Operate. Gewaehlt vom Nutzer am 2026-09-19 aus zwei gebauten Mockups.
Die uebrigen Oberflaechen (Verlauf, Ziele, Rezepte, Gewicht, Auth, Landing) laufen
vorerst weiter auf `base.html` und der alten DESIGN.md-Welt; sie folgen spaeter.

## Direction contract

THESIS: Der Tag ist eine **laufende Rechnung**, kein Feed und kein Karten-Dashboard.
Verweigert wird die Kategorie-Anordnung (Makro-Ringe, gefuellte Fortschrittsbalken,
gleich grosse Karten mit Icon) und ihr Gegenteil, der Ist-Zustand aus Creme, Serifen-
Display und Terracotta — der Cluster, in dem generierte Oberflaechen landen.

OWN-WORLD: Thermopapier (#efeee6, abgesetzt #e6e4da) auf dunkelgruener Tischflaeche
(#123028 auf #0c231d), Ink #1b1a15, Registrier-Rot #c4200d als einzige zweite Farbe
und nur fuer Offenes, Fehler und Ueberschreitung. Sometype Mono traegt alles Gedruckte;
Big Shoulders Display nur fuer den Bonkopf und die eine grosse Zahl. Rang kommt aus
Gewicht, Versalien, Punkt-Fuehrung und Linie (einfach, gepunktet, doppelt), nicht aus
einer Groessenleiter. Tabellen statt Balken. Knoepfe sind Stempelfelder mit harter
1,5px-Kontur, nie gefuellte Pillen. Ecken sind rechtwinklig; kein Radius ueber 0.

STORY: Ich sehe die Positionen des Tages in Druckreihenfolge, die Summe, das Tagesziel
und den Rest. Was noch offen ist, steht rot. Ich spreche oder tippe eine Zeile dazu;
wenn eine Angabe fehlt, druckt der Bon eine Rueckfrage dazwischen, bevor er bucht.

FIRST VIEWPORT: Bonkopf mit Wortmarke, Datum und Tagesnavigation; darunter die
gedruckte Bereichszeile mit invertiertem aktiven Feld. Dann das Eingabefeld mit
Stempelknopf "Loggen" und "Sprechen" direkt unter dem Kopf — der Job der Seite steht
vor der Bilanz. Dann die Positionsliste mit Nummer, Uhrzeit, Bezeichnung, Punkt-
fuehrung und kcal rechtsbuendig; Makros als graue Unterzeile. Darunter doppelte Linie,
Summe, Tagesziel und der Rest als einzige grosse Zahl, dann die Naehrwert-Tabelle
Ist/Ziel/Offen. Fuss mit Schnittkante.

FORM: Kassenbon / Tagesbon, Kandidat 1 der eigenen Liste (IMPECCABLE'S PICK, vom
Nutzer gegen die gewuerfelte Richtung 5 "Tonband" gewaehlt); Seed-Key 7e3ccb77,
Scope direction, Mode operate. Erhebungen aus den geschlagenen Richtungen:
ein Schriftgrad-Regime statt Groessenleiter (Kursbuch-Rack), Farbe nur an der Kante
statt in Flaechen (Wolkensaum), Zeilen als lebende Objekte in festen Spalten
(Fallblattanzeige), der Tag als einzige Achse (Abreisskalender).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Offene Entscheidungen

- Wortmarke: im Bonkopf steht der Name derzeit in Big Shoulders gesetzt, nicht als
  SVG aus `app/static/brand/`. Vor dem Launch klaeren, ob die Wortmarke umgezeichnet
  wird oder das SVG in den Kopf wandert.
- DESIGN.md wird erst nach dem Finish-Review aus dem gebauten Ergebnis geschrieben.
