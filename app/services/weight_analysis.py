"""Weight trend maths and the adaptive calorie suggestion.

Deliberately pure: no ``AsyncSession``, no clock, no settings. Every date the
functions need is passed in. That is what lets ``tests/test_weight_analysis.py``
run without a fixture, and it keeps the one part of the feature that can quietly
produce a *wrong number* separate from the part that can merely fail loudly.
``weight_service`` does the I/O and calls in here.

Like ``goal_service.build_progress``, the entry point returns display-ready values
— rounded, clamped, with the German message already chosen. Templates render, they
do not compute.
"""

from datetime import date, timedelta
from typing import Optional, Sequence

from app.core.dates_de import format_day_month, format_short_weekday

# Energy per kg of body-mass change. The textbook figure for fat; real change is a
# fat/lean/glycogen/water mix, which is why the estimate is only meaningful over
# weeks and why the guards below refuse short windows.
KCAL_PER_KG = 7700.0

SMOOTH_WINDOW_DAYS = 7   # trailing calendar window for the moving average
CHART_DAYS = 90          # how far back the page plots
TREND_DAYS = 28          # how far back the estimate looks

MIN_SPAN_DAYS = 14       # shortest span that can carry a trend
MIN_ENTRIES = 6          # weigh-ins required in the trend window
MIN_END_ENTRIES = 2      # weigh-ins backing the first and last smoothed point
MIN_INTAKE_COVERAGE = 0.8  # share of days that must have meals logged

MAX_PLAUSIBLE_RATE = 1.5   # kg/week; beyond this it is a data error, not a person
TDEE_HARD_MIN, TDEE_HARD_MAX = 1200.0, 5000.0   # outside → refuse
TDEE_SOFT_MIN, TDEE_SOFT_MAX = 1500.0, 4000.0   # outside → show with a caveat

FLAT_RATE_KG = 0.1       # |rate| below this reads as "Gewicht gehalten"
TDEE_ROUND = 10
SUGGESTION_ROUND = 50


def _round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


def moving_average(
    entries: Sequence[tuple],
    *,
    window_days: int = SMOOTH_WINDOW_DAYS,
) -> list[dict]:
    """Trailing mean over the ``window_days`` calendar days ending on each weigh-in.

    Returns one dict per weigh-in day, ascending:
    ``{"date", "raw", "avg", "n", "centre"}`` where ``n`` is how many weigh-ins
    backed the average and ``centre`` is the mean of their dates as a float
    ordinal. ``centre`` is what ``weekly_change`` divides by — see there.

    Two choices worth defending:

    * The window is a **calendar interval** ``[d - (window_days-1), d]``, not "the
      last N weigh-ins". Someone who only weighs on Mondays would otherwise get a
      window spanning seven weeks, lagging the truth by a month.
    * It averages **only the weigh-ins actually present** in that window. The
      obvious alternative — carry the last value forward and take a plain SMA —
      injects copies of a single measurement across a gap, so one water-inflated
      reading dominates the window and the line goes dead flat and then steps.
      Averaging what is there degrades gracefully, and is *identical* to a classic
      7-day SMA when someone weighs in daily.

    ``n`` is reported, not enforced. The chart draws every point (a line from day
    one is what people expect); the trend requires ``n >= MIN_END_ENTRIES`` at both
    ends, because a point with ``n == 1`` is just a raw value carrying the full
    water noise and must never anchor an estimate.
    """
    ordered = sorted(entries, key=lambda e: e[0])
    out: list[dict] = []
    start = 0
    for i, (day, kg) in enumerate(ordered):
        cutoff = day - timedelta(days=window_days - 1)
        while ordered[start][0] < cutoff:
            start += 1
        window = ordered[start:i + 1]
        out.append(
            {
                "date": day,
                "raw": kg,
                "avg": sum(w[1] for w in window) / len(window),
                "n": len(window),
                "centre": sum(w[0].toordinal() for w in window) / len(window),
            }
        )
    return out


def weekly_change(
    smoothed: Sequence[dict],
    *,
    min_n: int = MIN_END_ENTRIES,
) -> Optional[dict]:
    """Rate of change in kg/week between the first and last well-backed points.

    Computed on the *smoothed* series only — raw day-to-day values are mostly water.

    The rate divides the change by the distance between the two windows' **centres**,
    not between their end dates. This is not a refinement, it is the difference
    between right and wrong: a trailing average estimates the weight at the mean date
    of the measurements it covers, and at the start of a series that window is
    truncated (often ``n == 2``) while the one at the end is full. The lags therefore
    do *not* cancel. On a clean +0.5 kg/week ramp, dividing by the calendar span
    reports 0.45 — a 9% under-count that would flow straight into the expenditure
    estimate. Dividing by the centres recovers 0.5 exactly.

    ``span_days`` is still the plain calendar distance, because that is what the UI
    means by "seit X Wochen".

    Endpoint-to-endpoint on a smoothed series is roughly "mean of the first week vs.
    mean of the last week", the standard recomposition method. A least-squares slope
    would be marginally less noisy and much harder to explain in one German sentence.

    Returns ``None`` when fewer than two points qualify or they fall on one day.
    """
    usable = [p for p in smoothed if p["n"] >= min_n]
    if len(usable) < 2:
        return None
    first, last = usable[0], usable[-1]
    span_days = (last["date"] - first["date"]).days
    centre_span = last["centre"] - first["centre"]
    if span_days <= 0 or centre_span <= 0:
        return None
    delta_kg = last["avg"] - first["avg"]
    per_week_kg = delta_kg / centre_span * 7
    if per_week_kg > FLAT_RATE_KG:
        direction = "up"
    elif per_week_kg < -FLAT_RATE_KG:
        direction = "down"
    else:
        direction = "flat"
    return {
        "start_date": first["date"],
        "end_date": last["date"],
        "span_days": span_days,
        "start_kg": first["avg"],
        "end_kg": last["avg"],
        "delta_kg": delta_kg,
        "per_week_kg": per_week_kg,
        "per_week_g": round(per_week_kg * 1000),
        "direction": direction,
    }


def intake_stats(series: Sequence[dict], start: date, end: date) -> dict:
    """Average logged intake over ``[start, end]``, plus how complete the log is.

    ``series`` is ``meal_service.get_daily_series`` output, unchanged — no new query.

    The average divides by the number of **logged** days, not by the number of days
    in the window. This is the single most dangerous line in the feature:
    ``get_period_summary`` divides by all days, and reusing it here would score every
    unlogged day as a 0 kcal day, invent a deficit of roughly a full day's intake,
    and inflate the estimated expenditure by the same amount — the app would start
    telling people they burn 4500 kcal a day.

    Averaging over logged days assumes the missing days looked like the logged ones.
    That assumption is exactly why the caller gates on ``MIN_INTAKE_COVERAGE``.
    """
    window = [e for e in series if start <= e["date"] <= end]
    days_total = (end - start).days + 1
    logged = [e for e in window if e["meal_count"] > 0]
    days_logged = len(logged)
    return {
        "days_total": days_total,
        "days_logged": days_logged,
        "days_missing": days_total - days_logged,
        "avg_calories": (
            sum(e["calories"] for e in logged) / days_logged if days_logged else None
        ),
        "coverage": days_logged / days_total if days_total else 0.0,
    }


def estimate_tdee(avg_intake: float, per_week_kg: float) -> float:
    """Daily expenditure implied by intake and the rate of weight change.

    Energy balance over the window::

        Δmass · KCAL_PER_KG = (avg_intake − TDEE) · days
        ⇒ TDEE = avg_intake − per_week_kg · KCAL_PER_KG / 7

    Sign check, both ways: gaining weight (``per_week_kg > 0``) subtracts a positive
    number, so the estimate lands *below* intake — you gained because you ate more
    than you burned. Losing weight puts it above intake.

    Assumptions: 7700 kcal per kg of body mass; logged intake equals real intake
    (under-reporting pulls the estimate down); unlogged days resembled logged ones;
    expenditure was constant across the window.
    """
    return avg_intake - per_week_kg * KCAL_PER_KG / 7


def suggest_target(tdee: float, desired_rate_kg_week: float) -> float:
    """Daily calories that would produce ``desired_rate_kg_week``. Display only."""
    return tdee + desired_rate_kg_week * KCAL_PER_KG / 7


def build_chart(
    points: Sequence[dict],
    *,
    width: float = 640.0,
    height: float = 200.0,
    pad_x: float = 8.0,
    pad_y: float = 12.0,
    min_span_kg: float = 1.0,
) -> Optional[dict]:
    """Screen geometry for the weight chart, computed server-side.

    Mirrors the ``build_progress`` precedent, where ``bar_pct`` is clamped in Python
    and the template only substitutes it into a style attribute.

    Returns ``None`` for an empty series so the template can render its empty state.
    """
    if not points:
        return None

    values = [p["raw"] for p in points] + [p["avg"] for p in points]
    lo, hi = min(values), max(values)
    # No zero baseline, on purpose. Body weight varies by about 1%, so a 0-based
    # axis renders every history ever recorded as a flat horizontal line. This is
    # the one chart where the "axes start at zero" rule is actively wrong — please
    # do not "fix" it.
    span = hi - lo
    pad = max(span * 0.15, min_span_kg / 2)
    y_min, y_max = lo - pad, hi + pad
    if y_max <= y_min:  # defensive; pad already guarantees a positive span
        y_min, y_max = lo - 0.5, hi + 0.5

    first_day, last_day = points[0]["date"], points[-1]["date"]
    day_span = (last_day - first_day).days
    plot_w, plot_h = width - 2 * pad_x, height - 2 * pad_y
    single = len(points) == 1

    def _x(d: date) -> float:
        # Positioned by date, not by index: three weigh-ins on Mon/Tue/Wed and a
        # fourth a month later must not be evenly spaced.
        if single or day_span == 0:
            return width / 2
        return round(pad_x + (d - first_day).days / day_span * plot_w, 1)

    def _y(kg: float) -> float:
        return round(pad_y + (y_max - kg) / (y_max - y_min) * plot_h, 1)

    dots = [
        {
            "x": _x(p["date"]),
            "y": _y(p["raw"]),
            "kg": round(p["raw"], 1),
            "label": format_short_weekday(p["date"]),
        }
        for p in points
    ]
    line = (
        None
        if single
        else " ".join(f"{_x(p['date'])},{_y(p['avg'])}" for p in points)
    )
    return {
        "view_w": int(width),
        "view_h": int(height),
        "line": line,
        "dots": dots,
        "y_min": round(y_min, 1),
        "y_max": round(y_max, 1),
        "x_first_label": format_day_month(first_day),
        "x_last_label": format_day_month(last_day),
        "single": single,
    }


def _blocked(key: str, message: str, **extra) -> dict:
    return {"blocked": key, "blocked_message": message, **extra}


def build_weight_view(
    entries: Sequence[tuple],
    intake_series: Sequence[dict],
    *,
    trend_start: date,
    trend_end: date,
    intake_end: date,
    desired_rate_kg_week: Optional[float],
    goal_calories: Optional[float],
) -> dict:
    """Everything the /weight page renders, as display-ready values.

    ``entries`` are ``(day, kg)`` pairs over the chart window; ``intake_series`` is
    ``get_daily_series`` output covering at least ``[trend_start, intake_end]``.

    The two windows end one day apart, and that asymmetry is deliberate.
    ``intake_end`` is yesterday: today's meals are only half logged, and counting
    them would drag the intake average down and inflate the estimate. A weigh-in,
    by contrast, is complete the moment it is taken, so ``trend_end`` is today —
    otherwise the weigh-in someone just entered would not be counted, and the page
    would tell them they have "0 von mindestens 6" while listing one right below.
    The cost is a one-day offset between the two windows, which is under 4% of the
    shortest window this function will estimate from.

    When the data cannot carry an estimate, ``estimate`` is ``None`` and ``blocked``
    names why, with ``blocked_message`` already written in German. The reasons are
    kept apart on purpose — the user needs to know *which* log to fill.
    """
    smoothed = moving_average(entries)
    chart = build_chart(smoothed)
    latest = None
    if smoothed:
        last = smoothed[-1]
        latest = {
            "date": last["date"],
            "raw_kg": round(last["raw"], 1),
            "avg_kg": round(last["avg"], 1),
            "n": last["n"],
        }

    view: dict = {
        "has_data": bool(smoothed),
        "latest": latest,
        "points": smoothed,
        "chart": chart,
        "trend": None,
        "intake": None,
        "estimate": None,
        "blocked": None,
        "blocked_message": None,
    }

    if not smoothed:
        view.update(
            _blocked(
                "no_entries",
                "Noch keine Wiegungen. Trag dein Gewicht ein — nach zwei Wochen "
                "kann ich deinen Verbrauch schätzen.",
            )
        )
        return view

    trend_entries = sorted(
        (e for e in entries if trend_start <= e[0] <= trend_end),
        key=lambda e: e[0],
    )
    if len(trend_entries) < MIN_ENTRIES:
        view.update(
            _blocked(
                "too_few_entries",
                f"Zu wenige Wiegungen: {len(trend_entries)} von mindestens "
                f"{MIN_ENTRIES}. Wieg dich am besten mehrmals pro Woche, immer "
                "morgens nach dem Aufstehen.",
            )
        )
        return view

    trend_smoothed = moving_average(trend_entries)
    raw_span = (trend_entries[-1][0] - trend_entries[0][0]).days
    if raw_span < MIN_SPAN_DAYS:
        view.update(
            _blocked(
                "span_too_short",
                f"Der Zeitraum ist zu kurz: {raw_span} von mindestens "
                f"{MIN_SPAN_DAYS} Tagen. Wasserschwankungen würden die Schätzung "
                "sonst überdecken.",
            )
        )
        return view

    trend = weekly_change(trend_smoothed)
    if trend is None or trend["span_days"] < MIN_SPAN_DAYS:
        view.update(
            _blocked(
                "thin_ends",
                "Am Anfang oder Ende des Zeitraums fehlen Wiegungen. Für einen "
                "belastbaren Trend brauche ich je zwei Wiegungen in der ersten und "
                "in der letzten Woche.",
            )
        )
        return view
    view["trend"] = {
        **trend,
        "delta_kg": round(trend["delta_kg"], 1),
        "start_kg": round(trend["start_kg"], 1),
        "end_kg": round(trend["end_kg"], 1),
        "per_week_kg": round(trend["per_week_kg"], 2),
    }

    # The intake window is the *trend* window, not the fetched window: averaging 28
    # days of meals against a 20-day weight trend compares two different periods.
    # Capped at intake_end so today, whose meals are still being logged, stays out.
    intake = intake_stats(
        intake_series, trend["start_date"], min(trend["end_date"], intake_end)
    )
    view["intake"] = {
        **intake,
        "avg_calories": (
            round(intake["avg_calories"]) if intake["avg_calories"] is not None else None
        ),
        "coverage_pct": round(intake["coverage"] * 100),
    }

    if intake["days_logged"] == 0:
        view.update(
            _blocked(
                "no_intake",
                "Für diesen Zeitraum sind keine Mahlzeiten erfasst. Ohne Kalorien "
                "kann ich den Verbrauch nicht schätzen.",
            )
        )
        return view
    if intake["coverage"] < MIN_INTAKE_COVERAGE:
        view.update(
            _blocked(
                "intake_gaps",
                f"An {intake['days_missing']} von {intake['days_total']} Tagen "
                "fehlen Mahlzeiten. Ich schätze erst ab "
                f"{round(MIN_INTAKE_COVERAGE * 100)} % erfassten Tagen — sonst sähe "
                "es nach einem Defizit aus, das es nie gab.",
            )
        )
        return view

    if abs(trend["per_week_kg"]) > MAX_PLAUSIBLE_RATE:
        view.update(
            _blocked(
                "implausible_rate",
                f"{trend['per_week_g']} g pro Woche — das ist keine Körpermasse, "
                "sondern fast sicher eine Fehleingabe. Prüf deine Wiegungen.",
            )
        )
        return view

    tdee = estimate_tdee(intake["avg_calories"], trend["per_week_kg"])
    if not TDEE_HARD_MIN <= tdee <= TDEE_HARD_MAX:
        view.update(
            _blocked(
                "implausible_tdee",
                f"Die Zahlen ergeben keinen sinnvollen Verbrauch "
                f"({_round_to(tdee, TDEE_ROUND)} kcal). Prüf deine Wiegungen und "
                "Mahlzeiten.",
            )
        )
        return view

    suggested = (
        _round_to(suggest_target(tdee, desired_rate_kg_week), SUGGESTION_ROUND)
        # 0.0 is a real rate ("halten"); only None means "no target stated".
        if desired_rate_kg_week is not None
        else None
    )
    view["estimate"] = {
        "tdee": _round_to(tdee, TDEE_ROUND),
        "uncertain": not TDEE_SOFT_MIN <= tdee <= TDEE_SOFT_MAX,
        "suggested": suggested,
        "desired_rate_kg_week": desired_rate_kg_week,
        "desired_rate_g_week": (
            round(desired_rate_kg_week * 1000)
            if desired_rate_kg_week is not None
            else None
        ),
        "goal_calories": round(goal_calories) if goal_calories is not None else None,
        "delta_to_goal": (
            suggested - round(goal_calories)
            if suggested is not None and goal_calories is not None
            else None
        ),
        "weeks": max(1, round(trend["span_days"] / 7)),
    }
    return view
