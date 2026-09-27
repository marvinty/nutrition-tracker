---
version: 1
slug: "app-landing-templates-landing-html"
primary_target: "app/landing/templates/landing.html"
related_targets: []
---

## Scope

Landing Page `/` — oeffentlich, ohne Anmeldung. Modus: Persuade.
Die visuelle Welt ist bereits entschieden (Bon, siehe DESIGN.md); dies ist keine neue
Weltwahl, sondern das Nachziehen einer bestehenden Seite. Inhalt, Copy, Reihenfolge und
CTA-Regeln bleiben; nur die Form wechselt.

## Direction contract

THESIS: Wenn der Tag eine laufende Rechnung ist, dann ist die Landing Page der Tisch,
auf dem die Belege liegen. Verweigert wird die Kategorie-Anordnung (Hero mit Bento-Grid
aus gleich grossen Icon-Karten, Fortschrittsbalken als Beweis) und der alte Auftritt
(Creme, Newsreader-Kursive, Terracotta).

OWN-WORLD: Dieselben Tokens wie das Dashboard. Neu ist nur die Anordnung: mehrere
Papiere auf der Tischflaeche statt einer durchgehenden Rolle. Was Papier ist, traegt
Korn, Abrisskante und Schnittkante; was auf dem Tisch steht (Wortmarke, Ueberschriften,
Fusszeile), steht in `--on-table` direkt auf dem Gruen. Rot bleibt Offenem, Fehlern und
Ueberschreitung vorbehalten — der Primaerknopf ist ein Papier-Stempel, kein roter.
Betonung im Fliesstext kommt als Punktfuehrung unter dem Wort, nie als Kursive und nie
als Farbe.

STORY: Die Besucherin versteht in einem Blick, dass sie einen Satz sagt und eine
gebuchte Zeile bekommt; sie sieht am Beleg, dass nachgefragt statt geraten wird; sie
registriert sich.

FIRST VIEWPORT: Schmale Leiste auf dem Tisch mit Wortmarke links, FAQ/Anmelden/
Registrieren rechts. Darunter zweispaltig: links die Ueberschrift direkt auf dem Tisch,
das Wort "gegessen" mit Punktfuehrung unterstrichen, darunter der Untertitel, der
Stempel "Jetzt registrieren" in Papierfarbe und die Invite-Zeile; rechts ein Beleg aus
Papier, auf den sich der Satz tippt und in den danach die Werte als Position mit
Punktfuehrung einlaufen. Auf Handy stapeln sie in dieser Reihenfolge.

FORM: Bon-Welt, Flaechenwechsel von einer Rolle zu mehreren Belegen auf dem Tisch.
Kein eigener Seed — die Welt stand bereits fest (Seed-Key 7e3ccb77, Runde vom
2026-09-19), und der Auftrag lautete ausdruecklich "nachziehen".

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Uebernommene Regeln

- Ein Primaer-CTA auf `/register` ("Jetzt registrieren"), in der Leiste nur "Registrieren".
- `/login` ausschliesslich als dezenter Textlink, nie als zweiter grosser Knopf.
- Die Invite-Zeile nur hier, unter dem CTA.
- Feature-Wording ausschliesslich aus DESIGN.md, nichts dazuerfinden.
- Ein einziger gestalteter Moment: der Beleg, der sich im ersten Viewport druckt.
  Kein Reveal-on-Scroll — die alte Seite hatte es, der Bon hat die Ein-Moment-Regel.

## Bewusste Abweichungen vom alten Aufbau

- Die Eyebrow-Zeilen ("Voice-first Ernaehrungslog", "Der ganze Ablauf", "Der
  Unterschied", "Funktionen") entfallen: DESIGN.md verbietet die gesperrte
  Versalienzeile ueber einer Ueberschrift. Die Ueberschriften tragen sich selbst.
- Die Mini-Balken der Ziel-Karte entfallen: der Bon rechnet, er visualisiert nicht.
  An ihre Stelle tritt eine gedruckte Wochentabelle.
- Das Bento-Grid aus gleich grossen Icon-Karten entfaellt zugunsten gedruckter
  Positionslisten.
