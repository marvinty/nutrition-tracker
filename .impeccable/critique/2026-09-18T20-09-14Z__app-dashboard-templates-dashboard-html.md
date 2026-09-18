---
target: app/dashboard/templates/dashboard.html
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 4
target_identity: "file:/Users/marvin/nutrition-tracker/app/dashboard/templates/dashboard.html"
target_fingerprint: "sha256:5e0eb9f76368681a8cb89563893b6b241f3ec92c495af24913f4047dbc2fdd7d"
target_path: /Users/marvin/nutrition-tracker/app/dashboard/templates/dashboard.html
timestamp: 2026-09-18T20-09-14Z
slug: app-dashboard-templates-dashboard-html
---
# Design Critique — app/dashboard/templates/dashboard.html

Method: dual-agent (A: a8686afce641617e3 · B: a52349572120f951d)
Surface mode: Operate — judged against PRODUCT.md's binding scene: mobile, one-handed, 375px, right after eating.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | 5–15s Whisper+LLM wait signalled by one 14px muted line; completed log gets no confirmation |
| 2 | Match System / Real World | 3 | German brand voice in the card, but API `detail` strings leak English into the status line |
| 3 | User Control and Freedom | 1 | No undo on delete/edit, no cancel on clarification, no retry after failed upload — blob discarded, credit spent |
| 4 | Consistency and Standards | 3 | Faithful component reuse; but native `confirm()` amid custom UI, and `#f6d3c6` outside DESIGN.md's closed tint list |
| 5 | Error Prevention | 2 | Text-submit and record not mutually disabled — two concurrent AI calls, two credits |
| 6 | Recognition Rather Than Recall | 3 | Good placeholder and editor labels, but the transcript is never shown |
| 7 | Flexibility and Efficiency | 2 | Enter submits; no record shortcut, no enterkeyhint, no re-log of a frequent meal |
| 8 | Aesthetic and Minimalist Design | 3 | Restrained and warm with a POV; 36px serif date eats the fold |
| 9 | Error Recovery | 1 | English technical strings with raw exception reprs, no recovery action anywhere |
| 10 | Help and Documentation | 2 | /ai-log link is thoughtful; nothing explains a Credit or the 2-question cap |
| **Total** | | **22/40** | **Acceptable, low end — significant work needed** |

## Design Specificity Verdict

Authored at rest, generic in motion — roughly 60/40, and the 40 is the half that matters.

The static composition is this product's: the hero is a log card whose headline is the brand claim (dashboard.html:54), and the clarification box (dashboard.html:78) is bespoke — accent-soft plane, 3px accent rule, 20px Newsreader question. It reads as speech, not as a validation error.

The scaffolding around it is interchangeable, and the decisive failure is dynamic: the estimate arriving after you speak is `window.location.reload()` (dashboard.html:231). The response carries `transcript` and the full `meal`; the template throws both away. A voice-first product whose voice moment is a white flash has not finished being designed.

### Deterministic scan

4 findings, all in base.html, all severity warning, no line numbers emitted.

- `low-contrast` — #7a7164 on #eeece4, 4.1:1 (needs 4.5:1) — GENUINE. DESIGN.md fixes both tokens but never claims the pair is accessible. The detector caught only the mildest case; the design review found `--text-subtle #a39a8d` on `--surface` at ≈2.48:1 carrying the macro labels, and #f6d3c6 on `--accent` at ≈2.79:1.
- `overused-font` — Primary font: Inter — FALSE POSITIVE. DESIGN.md:16 mandates Inter for Fließtext und UI; the file is binding.
- `cream-palette` — bg rgb(238,236,228) — FALSE POSITIVE. DESIGN.md:40 fixes --bg:#eeece4 exactly, "keine neuen Grundfarben".
- `pulsing-dot` — .rec-indicator::before — FALSE POSITIVE. The indicator un-hides only while recording is live; that is the state a pulse is reserved for.

One genuine finding out of four. The detector added nothing the design review missed.

### Visual overlays

None. No reliable user-visible overlay available: port 8000 held by an unrelated project's container (jobs-api-1), /dashboard behind login + invite-only auth, MacroMic not running. No containers started/stopped, no auth bypass attempted. All layout numbers computed from inlined CSS at 375px (335px content width), not observed.

## Overall Impression

The right page, stopped one screen short of the product PRODUCT.md describes. Input before numbers, microphone before ring, question styled as speech — non-obvious, correct calls. Then the primary text input collapses to ~5 characters on the only device that matters, and the estimate's arrival is a page refresh. Biggest opportunity: the 800ms after the estimate lands, currently the emptiest moment in the app.

## What's Working

1. The clarification component reads as a conversational turn, not an error state (dashboard.html:78) — accent-soft, 3px accent rule, 20px Newsreader question, i.e. heading register. A deliberate claim that the question is a feature; matches PRODUCT.md positioning exactly.
2. The credit badge linked to /ai-log (dashboard.html:57-66) turns an adversarial constraint into an argument for trust, in the brand's dry voice. The inline comment about sibling-not-child placement prevents regression.
3. Input before numbers in DOM order: log card → Tagesbilanz → Mahlzeiten. Every competitor leads with the calorie ring; leading with the microphone is correct for this job.

## Priority Issues

### [P0] The meal input collapses to ~46px at 375px
- What: `.log-form` (dashboard.html:69; base.html:119) is one wrapping flex row. At 335px content width, inflexible children measure ≈94px ("Loggen") + ≈175px ("Sprachaufnahme") + 20px gaps ≈ 289px, leaving the field ≈46px — about five characters. `min-width:0` guarantees crushing over wrapping. Recording un-hides #record-indicator and grows the label to "Aufnahme stoppen", forcing a mid-interaction reflow.
- Why: primary control, on the viewport PRODUCT.md records as binding and user-confirmed. Half of the two input paths unusable on the only device that matters.
- Fix: in the 640px block (dashboard.html:18): `.log-form input[type=text]{flex-basis:100%}` and `.log-form .btn{flex:1}`. Move #record-indicator out of .log-form. Rename the button "Sprechen".
- Command: /impeccable adapt

### [P1] A completed log produces no confirmation, and the transcript is never shown
- What: handleLogResponse (dashboard.html:229) discards data.meal and data.transcript — both on the wire — and calls window.location.reload().
- Why: the peak moment renders as a page refresh, and a Whisper mis-transcription commits silently — undercutting the promise that MacroMic says when it is guessing.
- Fix: render an inline confirmation in .log-card from the response (transcript as heard, four macros, "Korrigieren" wired to the existing .row-edit flow) before reloading; pass ?logged=<id> and highlight the matching row in --accent-soft.
- Command: /impeccable animate, then /impeccable delight

### [P1] Personal credit exhaustion is invisible until a submit fails
- What: dashboard.html:57 applies credit-line--blocked only on `not credits.system_available`. At remaining == 0 the badge is pixel-identical to a healthy state and both buttons stay enabled. refreshCredits() repeats the one-sided check.
- Why: the user records, waits, and is rejected with a 429. A deliberate constraint communicated only by failure.
- Fix: branch on credits.remaining <= 0 too — blocked style, disable both buttons, swap the placeholder for the German message in usage_service._USER_LIMIT_DETAIL. Mirror in refreshCredits().
- Command: /impeccable harden

### [P1] English exception text shown to a German user, after the credit is spent and the recording is gone
- What: dashboard.html:255, 260, 351, 355, 401, 434 put err.detail verbatim into .status. Details include "Empty audio file", "Whisper transcription failed: {exc}", "LLM extraction failed: {exc}", "Meal not found" — English, several interpolating a raw exception repr. Credit-limit strings next to them are German.
- Why: violates the German-only rule binding in CLAUDE.md and PRODUCT.md. Credits are charged before the provider call with no refund path, so a 502 costs a credit while uploadRecording discards the blob.
- Fix: German detail strings without exception interpolation (the AI log captures it server-side). Retain the blob in uploadRecording and offer "Nochmal senden".
- Command: /impeccable clarify, then /impeccable harden

### [P1] The reading layer fails at 375px: rows stack, data sits at 2.5:1
- What (A): base.html's 640px row rules (base.html:287) target .row-day/.row-macros/.row-count — history.html's classes, none used by dashboard.html. The dashboard's row leaves .row-main ≈48px inside a 297px card, and .row-title has no text-overflow, so a normal description stacks into ~9 lines.
- What (B): --text-subtle #a39a8d on --surface ≈2.48:1 carries macro labels, .row-sub, .goal-meta, .row-time, .hint, .empty and every label. #f6d3c6 on --accent ≈2.79:1 and is not in DESIGN.md's closed tint list, which supplies --on-accent-muted:#f6d9cc. base.html's :root omits the whole --on-* block.
- Why: the user cannot read their own log on the device they log from. Detector and design review agree here; the detector caught only the mildest instance.
- Fix: add `.row-main{flex-basis:100%;order:3}` to the dashboard's 640px block; move data-carrying text from --text-subtle to --text-muted (≈4.3:1); replace #f6d3c6 with --on-accent-muted and add the DESIGN.md --on-* tokens to :root.
- Command: /impeccable audit, then /impeccable adapt

## Persona Red Flags

**Casey (Distracted Mobile User)** — primary persona, described almost verbatim in PRODUCT.md. Input ≈46px wide. Every control in the top third of an 812px viewport; nothing in the thumb zone, on a product whose principle 4 is "Der Daumen entscheidet". Tap targets under 44×44 throughout (.nav-btn 38×38, .nav-link ~35px, .row-btn ~33px, .row-edit__delete 36×36, .btn.sm 36px). Interrupted mid-flow she loses everything: blob not retained, convo array client-side only, pending clarification silently destroyed by typing a new meal. ~150px of sticky nav (7 links on two rows) takes ~20% of her viewport.

**Sam (Accessibility-Dependent User)** — no aria-live on any .status element, so waits, errors and outcomes are announced never. #clarify-box toggles .hidden with no announcement, then focus moves to #clarify-input, which has no label — Sam lands in an edit field and never hears the question. #meal-text-input unlabeled; four editor labels have no `for`. .goal-bar__fill--over signals overshoot by colour alone.

**Riley (Deliberate Stress Tester)** — can fire "Loggen" during a voice upload (two calls, two credits, two racing reloads). Delete is confirm() then gone, no undo. Refresh during a clarification loses the question and the charged credit. Two tabs on the same meal: last write wins silently. Empty state is one italic line at 2.48:1 with no guidance.

**"Die Skeptikerin"** (project-specific) — no transcript, no confidence signal, no indication of which numbers were asked about versus inferred, bare `—` for null macros. /ai-log is a 12px --text-subtle line at 2.48:1, below the fold on mobile. The differentiator lives in the backend and one hidden component, absent where the estimate lands.

**"Der Invite-Nutzer auf Kreditbudget"** (project-specific) — nothing explains what a Credit buys, that a clarification costs 0 but a voice log costs more, or that the cap resets at local midnight. A Whisper 502 eats a credit unacknowledged. The 2-question cap is invisible mid-clarification.

## Minor Observations

- "Carbs" (dashboard.html:107) is the only English word in the UI copy, next to "Eiweiß"/"Fett".
- Three "Heute"s in one viewport; active_page keeps "Heute" highlighted at /dashboard?d=…, where the page says "Rückblick".
- The H1 is a 30-character date at 36px Newsreader — 2–3 lines, 76–113px of the first screen, for the datum the user already knows.
- confirm() is the only OS-native dialog in a fully custom German interface.
- No enterkeyhint="send", no autocapitalize on the text input.
- .row-edit__delete is icon-only; no label on touch.
- No pointer to /goals from an unset-goal state.
- .log-card's gap:4px is inert.

## Questions to Consider

1. The clarify box is the only component that looks like the product PRODUCT.md describes. Why does it appear only when the model fails, rather than as the shape of a successful log?
2. window.location.reload() sits on the line where this product earns or loses trust. What would the page look like if those 800ms were the most important 800ms in the app?
3. You built a credit system and never said what a Credit is. Why make people manage a budget the interface never taught them to value?
4. PRODUCT.md says the thumb decides, and calls it binding. If that were true, where would the microphone be?
