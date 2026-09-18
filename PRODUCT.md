# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primär: Menschen, die ihre Ernährung tracken wollen — Abnehmen, Gesundheit, Muskelaufbau,
Neugier. Bewusst breit gefasst; Kraftsport ist ein Segment davon, nicht die Definition
der Zielgruppe.

Situation: überwiegend am Handy, häufig direkt nach dem Essen, einhändig, oft unterwegs
oder am Tisch. Der Job ist „diese Mahlzeit ins Log bekommen, bevor ich sie vergesse" —
in Sekunden, nicht in einem Formular.

Zweite Rolle: der Betreiber (Admin) mit eigenem Login und getrennten Ansichten für Nutzer,
Invites, Kosten, Feedback und KI-Log.

## Product Purpose

MacroMic ist ein Voice-first Ernährungslog. Die Nutzerin sagt oder tippt in natürlicher
Sprache, was sie gegessen hat; die Aufnahme wird transkribiert, ein LLM schätzt Kalorien,
Eiweiß, Kohlenhydrate und Fett, die Mahlzeit landet im Tagesprotokoll.

Erfolg heißt: Loggen kostet so wenig Aufwand, dass es nicht abbricht — kein Suchen in
Datenbanken, kein Scrollen durch Treffer, kein Abwiegen.

## Positioning

Das Unterscheidungsmerkmal ist die **Rückfrage**: Fehlt eine Angabe, die das Ergebnis
deutlich verändert, stellt die App eine kurze, gezielte Frage, statt die Lücke mit einer
erfundenen Zahl zu füllen. Höchstens zwei Rückfragen, danach schätzt das Modell.
Konkurrenzprodukte raten still; MacroMic sagt, wann es rät.

Zweiter Punkt: Sprache läuft im Browser, ohne App-Installation und ohne zusätzliches Gerät.

## Operating Context

- Sprechen oder Tippen im Browser am Handy, direkt nach der Mahlzeit.
- Nachträgliches Korrigieren am Desktop oder später am Handy (Verlauf, Woche/Monat).
- Rezepte einmal anlegen, danach portionsweise loggen.
- Gewicht regelmäßig eintragen; daraus 7-Tage-Schnitt, Wochenveränderung und ein
  **Vorschlag** fürs kcal-Ziel — der nie automatisch übernommen wird.
- Betrieb: Docker Compose auf einem Proxmox-Host zuhause hinter Caddy, Domain macromic.de,
  Mailversand via Resend.

## Capabilities and Constraints

Bestätigte Funktionen:

- Sprachaufnahme im Browser → Transkription (Whisper) → Makros.
- Freitext in natürlicher Sprache; keine Dropdowns, keine Gramm-Pflichtfelder.
- Rückfrage-Dialog (max. 2 Assistenten-Turns) vor der endgültigen Schätzung.
- Makroziele mit Tagesfortschritt plus Auswertung Woche/Monat.
- Rezepte mit Makros pro Portion, Zutaten auch per Sprache.
- Verlauf mit Wochen-/Monatsansicht, Mahlzeiten nachträglich bearbeitbar.
- Gewichts-Log mit 7-Tage-Schnitt, Wochenveränderung, geschätztem Tagesverbrauch.
- Nutzer-Feedback direkt aus der App; vollständiges KI-Log pro Nutzer einsehbar.
- Admin-Bereich mit eigenen Zugangsdaten: Nutzer, Invites, Kosten, Feedback.

Constraints:

- **Mobil zuerst, einhändig.** Der Hauptgebrauch findet am Handy statt, oft direkt nach
  dem Essen. 375px ohne horizontales Scrollen und Daumenreichweite sind bindend
  (vom Nutzer ausdrücklich bestätigt).
- **Alles auf Deutsch** — UI-Copy, Fehlermeldungen, `detail`-Strings auf `HTTPException`.
  Mehrsprachigkeit ist kein Ziel.
- **Keine Drittanbieter-Assets im Frontend.** Fonts sind selbst gehostet; die
  Datenschutzerklärung sagt zu, dass kein Dritter eine IP-Adresse sieht. Kein
  `fonts.googleapis.com`, kein CDN.
- Zugang aktuell nur mit Invite-Code; E-Mail-Bestätigung mit Karenzzeit.
- Credit-System pro Nutzer und ein app-weites Tageslimit begrenzen die KI-Kosten;
  jeder KI-Endpunkt ist daran gebunden.
- Zeitrechnung in Europe/Berlin; Speicherung tz-aware UTC.
- Technisch: FastAPI, async SQLAlchemy, SQLite (ein uvicorn-Worker, bewusst),
  server-gerendertes Jinja2, CSS pro Template inline. SQLite ist ausdrücklich provisorisch.
- Legacy: `/meals` und `/audio` liegen ohne `/api`-Präfix an der Wurzel — Pfade eines
  ESP32-Clients, die nicht vereinheitlicht werden.

Explizit offen: BYO-API-Key als nächstes geplantes Feature; Tarifmodell und Preise sind
nicht entschieden.

## Brand Commitments

- Name **MacroMic**, Claim „Sag einfach, was du gegessen hast."
- Du-Ansprache. Ton direkt, selbstbewusst, leicht trocken. Kein Marketing-Sprech,
  keine Superlative, keine Emojis.
- Wortmarke und Monogramm liegen als SVG vor (siehe BRAND.md); Space Grotesk ausschließlich
  für die Wortmarke. Offener Punkt: Text in der Wortmarke in Pfade umwandeln, dann ist die
  Marke font-unabhängig.
- Farbwelt und Komponenten sind in DESIGN.md verbindlich festgehalten („nichts dazuerfinden").
  Kein Dark Mode.

## Evidence on Hand

- Live-Installation unter macromic.de (Proxmox zuhause, Caddy, Docker Compose).
- Landing Page, FAQ, Impressum und Datenschutzerklärung mit bestehender, verbindlicher Copy.
- Brand-Assets unter `app/static/brand/`, Fonts unter `app/static/fonts/`.
- DESIGN.md und BRAND.md als bestehende Design-Autorität.

Nicht vorhanden — und nicht zu erfinden: Testimonials, Nutzerzahlen, Kundenlogos, Presse,
Benchmarks, Preise, Zertifizierungen. Es gibt keine bezahlten Nutzer und keine
veröffentlichten Tarife.

## Product Principles

1. **Der Satz ist die Eingabe.** Jede Interaktion, die den Nutzer zurück ins Formular
   zwingt, ist ein Rückschritt.
2. **Lieber nachfragen als raten.** Eine erfundene Zahl im Protokoll beschädigt das
   Vertrauen stärker als eine zusätzliche Frage — aber höchstens zwei.
3. **Vorschlagen, nicht übernehmen.** Abgeleitete Werte (kcal-Ziel aus dem Gewichtsverlauf)
   bleiben Vorschläge, die der Nutzer bestätigt.
4. **Der Daumen entscheidet.** Was am Handy nicht einhändig funktioniert, funktioniert nicht.
5. **Keine Daten an Dritte, auch nicht beiläufig.** Was das Frontend lädt, kommt vom
   eigenen Server.

## Accessibility & Inclusion

Kein formaler Standard (WCAG o.ä.) wurde als Anforderung festgelegt. Bindend sind die
bestehenden Regeln aus DESIGN.md: responsiv bis 375px ohne horizontales Scrollen,
`prefers-reduced-motion` wird immer respektiert.
