---
target: die landingpage
total_score: 26
max_score: 36
na_heuristics: 7
p0_count: 2
p1_count: 3
target_identity: "file:/Users/marvin/nutrition-tracker/app/landing/templates/landing.html"
target_fingerprint: "sha256:97fcdaa746df64a6b28e190fe80a9ab89ff38a942c449c1f449744a94b55af70"
target_path: /Users/marvin/nutrition-tracker/app/landing/templates/landing.html
timestamp: 2026-09-18T21-13-58Z
slug: app-landing-templates-landing-html
---
# Design Critique — app/landing/templates/landing.html

Method: dual-agent (A: a059856d326d8f07a · B: a05806931c71d00c0)
Surface mode: Persuade. Geprüft an der echten Seite im Browser (lokal gerendert, echte selbstgehostete Fonts und Brand-Assets, needs_code=True).

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Nav-Rahmen und Reveal funktionieren; kein Fortschrittsmarker auf 5.298px Seitenlänge |
| 2 | Match System / Real World | 4 | Spricht, wie ein deutscher Nutzer über Essen redet; kein unübersetzter Jargon |
| 3 | User Control and Freedom | 3 | reduced-motion vollständig respektiert; unter 560px verschwinden beide Nav-Links |
| 4 | Consistency and Standards | 3 | Palette exakt nach DESIGN.md; .bento dreifach konfiguriert, Inline-Stil schlägt beide Media Queries |
| 5 | Error Prevention | 2 | needs_code serverseitig, gut; Code-Beschaffung, Preis und Tageslimit werden nirgends erwähnt |
| 6 | Recognition Rather Than Recall | 3 | Demo und Transkript ersparen jedes Vorstellen; Credit-Modell unsichtbar |
| 7 | Flexibility and Efficiency | n/a | Einzelentscheidung auf Persuade-Fläche; kein Expertenpfad zu beschleunigen |
| 8 | Aesthetic and Minimalist Design | 3 | Zurückgenommen; kostet Punkte für mini-bars und einen Hero, der den CTA unter die Falz schiebt |
| 9 | Error Recovery | 2 | Ohne JS bleiben alle 17 .rv-Elemente unsichtbar; kein noscript, kein Fehler |
| 10 | Help and Documentation | 3 | /faq ist gut und ungeschützt — auf Mobil aus der Navigation entfernt |
| **Total** | | **26/36** | **Good, unterer Rand** (H7 n/a) |

## Design Specificity Verdict

Autorenseite mit Schablonen-Mittelteil. Das Hero-Demo-Panel tippt den Satz und staffelt vier Makro-Kacheln zu je 120ms ein — der Produktablauf als Objekt. Der Rückfrage-Abschnitt bekommt den einzigen invertierten Accent-Block und argumentiert über ein Transkript statt über eine Behauptung. Schablonenhaft: "Was du sonst noch brauchst." und der 1-2-3-Erklärer. Der Befund ist nicht Generik, sondern Erreichbarkeit — die autorierten Teile kommen auf dem primären Gerät nicht an.

### Deterministischer Scan

18 CLI-Befunde plus einer, den nur das Overlay fand.

- low-contrast (15) — ECHT mit Einschränkung: DESIGN.md:115-118 legt fest, dass --text-subtle auf der Landing Page bleibt. Damit ist 2,34:1 dokumentiert, aber nicht gelöst.
- icon-tile-stack (7) — FALSCH POSITIV. DESIGN.md:97 spezifiziert das Icon-Badge als verbindliche Komponente.
- overused-font (Inter) — FALSCH POSITIV. DESIGN.md:16.
- cream-palette — FALSCH POSITIV. DESIGN.md:40.
- pulsing-dot (.eyebrow .pulse) — ECHT, einziger Befund mit Severity error. Hängt an keinem Live-Zustand, anders als der Aufnahme-Punkt im Dashboard.
- blinking-cursor (span.caret) — ECHT, nur im Overlay. An eine echte Animation gekoppelt, vertretbar.
- cramped-padding — ECHT.
- em-dash-overuse — advisory, 10 Gedankenstriche.

Verworfen: die von B gemessenen Buttons unter 44px sind die Bedienelemente des injizierten Overlays; landing.html enthält null <button>.

### Browser-Evidenz

Overlay lief, meldete 14 Anti-Patterns, Helfer auf Port 8400 gestoppt und nachgeprüft. Keine Verbindung zu einem Drittanbieter — performance.getEntriesByType('resource') zeigt ausschließlich 127.0.0.1. Fonts bestätigt selbst gehostet.

## Overall Impression

Die beste Arbeit im Repository: ein Standpunkt, eine Stimme, und mit dem Rückfrage-Transkript ein Beweismittel, das ohne Testimonials auskommt. Null Überclaim. Dann schiebt ein Inline-Attribut ein Drittel des Erklärstücks aus dem Handy-Viewport, lautlos, weil overflow-x:hidden die Scrollbar unterdrückt.

## What's Working

1. Der Rückfrage-Abschnitt argumentiert über ein Transkript statt über Adjektive — das stärkste verfügbare Beweismittel unter dem Verbot von Testimonials und Zahlen.
2. Das Demo-Panel macht das Tempo lesbar, bevor Copy gelesen ist; aria-hidden ist korrekt, weil der Chat-Block den Inhalt zugänglich wiederholt.
3. needs_code kommt aus dem Router: die Seite kann keine Registrierung versprechen, die der Server ablehnt.

## Priority Issues

### [P0] Inline-Stil schiebt ein Drittel von "Der ganze Ablauf" aus dem Viewport
- landing.html:278 trägt style="grid-template-columns:repeat(3,1fr)". Inline schlägt beide Media Queries (900px → 2 Spalten, 560px → 1 Spalte).
- Gemessen bei 375px, Container 335px: Karte 1 bei 20–209, Karte 2 bei 227–410 (abgeschnitten), Karte 3 bei 428–613 (vollständig außerhalb). scrollWidth 613 gegen clientWidth 375.
- Die zweite .bento auf derselben Seite, ohne Inline-Stil, rechnet korrekt auf 335px.
- PRODUCT.md hält 375px ohne horizontales Scrollen als bindend fest. Der Fehler ist lautlos.
- Fix: Attribut löschen, .bento.steps-Klasse in den Basisblock. Danach die drei weiteren Inline-Overrides prüfen.
- Command: /impeccable adapt

### [P0] Primär-CTA unter der Falz auf Standard-Laptops
- Bei 1440x900 rechnet .hero-ctas .btn auf top 888,6px; bei 1366x768 liegt er 120px darunter. Makro-Kacheln bei top 857px.
- Ursache: h1.hero-h erreicht die Clamp-Obergrenze 116px in 609,5px Spalte → vier Zeilen, 473px Höhe. Der <br> in Zeile 238 ist überflüssig. .hero-grid{align-items:end} schiebt die Demo-Spalte zusätzlich nach unten.
- Über der Falz: keine Aktion, keine Ausgabe, kein Beweis.
- Fix: Clamp auf clamp(44px,6.5vw,84px), <br> streichen, align-items:center ab 901px. Ziel: CTA-top unter 620px bei 768px Höhe.
- Command: /impeccable layout

### [P1] Die Seite nennt den Invite-Code und nie den Weg dahin
- Zeile 245 und 400 rendern korrekt aus Server-Zustand. Die FAQ wiederholt die Sperre, statt sie zu öffnen. Kein Kontaktweg außer dem Impressum.
- Konversionsdecke: bei einem Invite-Produkt ist der Anfrageweg das Konversionsereignis.
- Fix: Hinweis handlungsfähig machen — mailto auf die Adresse aus den Settings, die im Impressum längst veröffentlicht ist. Erfindet nichts. In der FAQ spiegeln.
- Command: /impeccable clarify

### [P1] Der gesamte Seiteninhalt hängt an JavaScript, ohne Fallback
- .rv{opacity:0}, siebzehn Elemente, jeder Pixel zwischen nav und footer. Kein noscript — base.html hat genau dafür eines.
- Ausfall total statt graduell, und lautlos. Der Registrieren-Knopf überlebt: gebrandete leere Seite mit einem rätselhaften Knopf.
- Fix: noscript-Block plus additive Enthüllung (html.js .rv{opacity:0}).
- Command: /impeccable harden

### [P1] Null Fokus-Stile
- grep -c focus landing.html → 0. landing.html erweitert base.html nicht und erbt dessen :focus-visible nicht.
- Tastaturfokus auf dem Primärbutton fällt auf den Browser-Standardring über Terrakotta.
- Die Seite hat sonst sorgfältig an a11y gedacht (reduced-motion, aria-hidden, Überschriftenordnung) und hört einen Schritt zu früh auf.
- Fix: Regel aus base.html übernehmen, plus abgesetzter Ring auf --accent-Flächen.
- Command: /impeccable audit

## Persona Red Flags

**Casey (Handy, primär)** — Schritt 3 existiert auf ihrem Bildschirm nicht, Schritt 2 ist mitten im Wort abgeschnitten. Kein Weg zur FAQ in der Navigation. 6,5 Handybildschirme hoch, zweiter CTA ganz unten.

**Jordan (Erstbesucher)** — eine Frage, die die gesamte Website verweigert. Keine Ahnung, ob es Geld kostet; die FAQ beantwortet das in sechs Wörtern und wird nie hervorgeholt. Auf das Tageslimit bereitet ihn nichts vor.

**Sam (a11y)** — kein einziger Fokus-Stil; Invite-Hinweis bei 2,34:1. Korrekt gelöst: reduced-motion schaltet ab und macht sichtbar, Typewriter kürzt sich ab, Überschriftenordnung stimmt.

**Riley (Stresstest)** — JS aus: leere Seite mit Nav und Fuß. Fenster von 900 auf 375: #ablauf weigert sich umzubrechen, #features zwei Sektionen tiefer bricht korrekt um.

## Minor Observations

Wortmarke in der Nav ist kein Link · og:image fehlt (blockiert durch den offenen BRAND.md-Punkt) — für ein Invite-Produkt mit Mundpropaganda als einzigem Verbreitungsweg der höchste Hebel auf der Liste · mini-bars dekorieren statt zu demonstrieren · .demo-quote nutzt --surface statt --on-dark · .hero-ctas antizipiert einen zweiten Button, den DESIGN.md verbietet · die Anker #ablauf/#rueckfrage/#features sind unverlinkt · .card:hover hebt sieben nicht klickbare Karten · unter 560px versteckt eine CSS-Zeile beide Nav-Links, weil FAQ und Anmelden sich die Klasse nav-login teilen.

## Questions to Consider

1. Das stolzeste Versprechen ist "fragt nach, statt eine Zahl zu erfinden" — warum versteckt die Seite dann das Invite-Gate in der blassesten Farbe und beantwortet die Frage nie, die sie auslöst?
2. Wenn Testimonials, Zahlen, Logos und Presse verboten sind — reicht ein einziges durchgespieltes Beispiel als Ersatz, oder wären drei Transkripte ehrlicher?
3. Für wen ist die Seite? Die Worte sind breit, die Demo zeigt eine Kraftsport-Mahlzeit und führt mit Eiweiß.
4. Wie viele Beschränkungen sind Unfälle eines geteilten Klassennamens statt Entscheidungen?
