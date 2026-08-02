"""Tests for the pure weight maths behind /weight.

No fixture, no database, no event loop — ``weight_analysis`` takes dates as
arguments and touches nothing. That is the point of the module split: this is the
part of the feature that can produce a plausible-looking *wrong number*, so it is
the part that has to be cheap to test exhaustively.

Config requires an API key at import time, so the dummy env vars are set before
importing app modules, as everywhere else in this suite.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import date, timedelta

import pytest

from app.services.weight_analysis import (
    MIN_ENTRIES,
    build_chart,
    build_weight_view,
    estimate_tdee,
    intake_stats,
    moving_average,
    suggest_target,
    weekly_change,
)

DAY0 = date(2026, 6, 1)


def _d(offset: int) -> date:
    return DAY0 + timedelta(days=offset)


def _daily(weights: list[float], *, start: int = 0) -> list[tuple]:
    return [(_d(start + i), kg) for i, kg in enumerate(weights)]


def _meals(days: list[int], *, calories: float = 2500.0) -> list[dict]:
    """A get_daily_series-shaped list: every day in 0..27, only ``days`` logged."""
    return [
        {
            "date": _d(i),
            "calories": calories if i in days else 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "meal_count": 1 if i in days else 0,
        }
        for i in range(28)
    ]


# --------------------------------------------------------------------- smoothing

def test_moving_average_matches_plain_sma_when_daily():
    weights = [80.0, 80.4, 79.8, 80.2, 80.6, 80.0, 79.6, 80.8]
    points = moving_average(_daily(weights))
    assert [p["n"] for p in points] == [1, 2, 3, 4, 5, 6, 7, 7]
    # 8th point: the window is days 1..7, i.e. the last seven values.
    assert points[7]["avg"] == sum(weights[1:8]) / 7
    assert points[3]["avg"] == sum(weights[0:4]) / 4


def test_moving_average_window_is_calendar_not_last_n_entries():
    # Two weigh-ins ten days apart: the second one's window contains only itself,
    # even though there is a previous entry. "Last 7 weigh-ins" would have averaged
    # them together across a ten-day gap.
    points = moving_average([(_d(0), 80.0), (_d(10), 82.0)])
    assert points[1]["n"] == 1
    assert points[1]["avg"] == 82.0


def test_moving_average_start_of_series_is_the_raw_value():
    points = moving_average([(_d(0), 80.0)])
    assert points[0]["n"] == 1 and points[0]["avg"] == points[0]["raw"] == 80.0


def test_moving_average_sorts_defensively():
    points = moving_average([(_d(2), 81.0), (_d(0), 80.0), (_d(1), 80.5)])
    assert [p["date"] for p in points] == [_d(0), _d(1), _d(2)]


# ------------------------------------------------------------------ weekly change

def test_weekly_change_recovers_a_linear_ramp():
    # +0.5 kg per week over four weeks, weighed daily.
    weights = [80.0 + 0.5 / 7 * i for i in range(29)]
    trend = weekly_change(moving_average(_daily(weights)))
    assert trend["per_week_kg"] == pytest.approx(0.5)
    assert trend["direction"] == "up"


def test_weekly_change_direction_flat_and_down():
    flat = weekly_change(moving_average(_daily([80.0] * 29)))
    assert flat["direction"] == "flat" and abs(flat["per_week_kg"]) < 1e-9

    losing = weekly_change(moving_average(_daily([85.0 - 0.5 / 7 * i for i in range(29)])))
    assert losing["direction"] == "down"
    assert losing["per_week_kg"] == pytest.approx(-0.5)
    assert losing["per_week_g"] == -500


def test_weekly_change_none_without_two_well_backed_points():
    # A single point, and a series where no point ever reaches n >= 2.
    assert weekly_change(moving_average([(_d(0), 80.0)])) is None
    sparse = moving_average([(_d(0), 80.0), (_d(20), 81.0), (_d(40), 82.0)])
    assert all(p["n"] == 1 for p in sparse)
    assert weekly_change(sparse) is None


def test_weekly_change_none_for_zero_span():
    smoothed = moving_average([(_d(0), 80.0), (_d(1), 80.4)])
    # Both points qualify (n>=2 only for the second), so force the degenerate case.
    assert weekly_change([smoothed[1], smoothed[1]]) is None


# ------------------------------------------------------------------------ intake

def test_intake_stats_averages_over_logged_days_only():
    # 21 of 28 days logged at 2500 kcal. The mean must be 2500, NOT 2500*21/28.
    series = _meals(list(range(21)))
    stats = intake_stats(series, _d(0), _d(27))
    assert stats["days_total"] == 28
    assert stats["days_logged"] == 21
    assert stats["days_missing"] == 7
    assert stats["avg_calories"] == 2500.0
    assert stats["coverage"] == pytest.approx(0.75)


def test_intake_stats_no_logged_days():
    stats = intake_stats(_meals([]), _d(0), _d(27))
    assert stats["days_logged"] == 0 and stats["avg_calories"] is None


def test_intake_stats_clips_to_the_window():
    stats = intake_stats(_meals(list(range(28))), _d(5), _d(9))
    assert stats["days_total"] == 5 and stats["days_logged"] == 5


def test_intake_stats_counts_a_zero_kcal_logged_day():
    series = _meals([0, 1])
    series[2]["meal_count"] = 1  # logged, but totalling 0 kcal — still the user's data
    stats = intake_stats(series, _d(0), _d(2))
    assert stats["days_logged"] == 3
    assert stats["avg_calories"] == pytest.approx(5000.0 / 3)


# -------------------------------------------------------------------------- TDEE

def test_estimate_tdee_sign_gaining_means_below_intake():
    # Eating 3000 and gaining 0.5 kg in 14 days = 0.25 kg/week.
    # 0.25 * 7700 / 7 = 275 kcal/day of surplus, so expenditure is 2725.
    assert estimate_tdee(3000.0, 0.25) == pytest.approx(2725.0)


def test_estimate_tdee_sign_losing_means_above_intake():
    assert estimate_tdee(2000.0, -0.25) == pytest.approx(2275.0)


def test_estimate_tdee_flat_weight_equals_intake():
    assert estimate_tdee(2400.0, 0.0) == 2400.0


def test_suggest_target():
    assert suggest_target(2400.0, 0.3) == pytest.approx(2730.0)
    assert suggest_target(2400.0, 0.0) == 2400.0
    assert suggest_target(2400.0, -0.5) == pytest.approx(1850.0)


# ------------------------------------------------------------------------- chart

def test_build_chart_empty_is_none():
    assert build_chart([]) is None


def test_build_chart_single_point_is_centred_without_a_line():
    chart = build_chart(moving_average([(_d(0), 80.0)]))
    assert chart["single"] is True
    assert chart["line"] is None
    assert chart["dots"][0]["x"] == 320.0


def test_build_chart_never_uses_a_zero_baseline():
    chart = build_chart(moving_average(_daily([80.0, 80.1, 79.9, 80.05])))
    assert chart["y_min"] > 0
    # A near-flat series still gets at least a 1 kg window, so 200 g of wobble is
    # not amplified into a sawtooth.
    assert chart["y_max"] - chart["y_min"] >= 1.0


def test_build_chart_spaces_dots_by_date_not_by_index():
    chart = build_chart(moving_average([(_d(0), 80.0), (_d(1), 80.2), (_d(30), 81.0)]))
    xs = [d["x"] for d in chart["dots"]]
    assert xs[0] < xs[1] < xs[2]
    midpoint = (xs[0] + xs[2]) / 2
    assert xs[1] < midpoint  # index spacing would have put it exactly there


def test_build_chart_y_is_inverted():
    chart = build_chart(moving_average([(_d(0), 78.0), (_d(1), 82.0)]))
    heavier = chart["dots"][1]
    lighter = chart["dots"][0]
    assert heavier["y"] < lighter["y"]  # more kg = higher up = smaller SVG y


# -------------------------------------------------------- build_weight_view: blocks

def _view(entries, series, *, rate=0.3, goal=None):
    """Day 27 is "today": the trend window runs to it, the intake window stops a
    day earlier. The seeded series covers days 0..27."""
    return build_weight_view(
        entries,
        series,
        trend_start=_d(0),
        trend_end=_d(27),
        intake_end=_d(26),
        desired_rate_kg_week=rate,
        goal_calories=goal,
    )


def _good_entries() -> list[tuple]:
    """Daily weigh-ins over the whole window, holding weight exactly.

    Perfectly constant on purpose, so "flat weight ⇒ expenditure equals intake" can
    be asserted as an equality. The noisy case is covered separately below.
    """
    return _daily([80.0] * 28)


def test_view_no_entries():
    view = _view([], _meals(list(range(28))))
    assert view["blocked"] == "no_entries"
    assert view["estimate"] is None
    assert view["has_data"] is False
    assert view["chart"] is None
    assert "Noch keine Wiegungen" in view["blocked_message"]


def test_view_too_few_entries():
    entries = _daily([80.0, 80.2, 80.1])
    view = _view(entries, _meals(list(range(28))))
    assert view["blocked"] == "too_few_entries"
    assert view["estimate"] is None
    assert f"3 von mindestens {MIN_ENTRIES}" in view["blocked_message"]
    # The chart still renders — only the estimate is withheld.
    assert view["chart"] is not None


def test_view_span_too_short():
    entries = _daily([80.0, 80.2, 80.1, 80.3, 80.0, 80.2, 80.1])  # 7 days, 7 weigh-ins
    view = _view(entries, _meals(list(range(28))))
    assert view["blocked"] == "span_too_short"
    assert view["estimate"] is None


def test_view_thin_ends():
    # Plenty of weigh-ins spanning 20 days, but clustered so no point at the far end
    # is backed by two weigh-ins within its week.
    entries = _daily([80.0, 80.2, 80.1, 80.3, 80.0]) + [(_d(20), 80.4)]
    view = _view(entries, _meals(list(range(28))))
    assert view["blocked"] == "thin_ends"
    assert view["estimate"] is None


def test_view_no_intake():
    view = _view(_good_entries(), _meals([]))
    assert view["blocked"] == "no_intake"
    assert view["estimate"] is None


def test_view_intake_gaps_blocks_below_coverage():
    # 21 of 28 days logged = 75% < 80%.
    view = _view(_good_entries(), _meals(list(range(21))))
    assert view["blocked"] == "intake_gaps"
    assert view["estimate"] is None
    assert "fehlen Mahlzeiten" in view["blocked_message"]


def test_view_intake_coverage_just_above_threshold_passes():
    # 24 of 28 days = 85.7% >= 80%.
    view = _view(_good_entries(), _meals(list(range(24))))
    assert view["blocked"] is None
    assert view["estimate"] is not None


def test_view_implausible_rate():
    # 2 kg per week gained — a data error, not a person.
    entries = _daily([80.0 + 2.0 / 7 * i for i in range(28)])
    view = _view(entries, _meals(list(range(28))))
    assert view["blocked"] == "implausible_rate"
    assert view["estimate"] is None


def test_view_implausible_tdee():
    # Holding weight on 800 kcal/day would imply an 800 kcal expenditure.
    view = _view(_good_entries(), _meals(list(range(28)), calories=800.0))
    assert view["blocked"] == "implausible_tdee"
    assert view["estimate"] is None


# ------------------------------------------------------ build_weight_view: success

def test_view_estimate_holding_weight():
    view = _view(_good_entries(), _meals(list(range(28)), calories=2400.0), rate=0.3)
    assert view["blocked"] is None
    est = view["estimate"]
    # Weight is flat, so expenditure equals intake.
    assert est["tdee"] == 2400
    assert est["uncertain"] is False
    # 0.3 kg/week = +330 kcal/day → 2730, rounded to the nearest 50.
    assert est["suggested"] == 2750
    assert est["desired_rate_g_week"] == 300
    assert view["trend"]["direction"] == "flat"
    assert view["intake"]["avg_calories"] == 2400


def test_view_zero_rate_still_yields_a_suggestion():
    view = _view(_good_entries(), _meals(list(range(28)), calories=2400.0), rate=0.0)
    # 0 means "halten" and is a real answer; only None means "not stated".
    assert view["estimate"]["suggested"] == 2400
    assert view["estimate"]["desired_rate_g_week"] == 0


def test_view_no_rate_gives_tdee_but_no_suggestion():
    view = _view(_good_entries(), _meals(list(range(28)), calories=2400.0), rate=None)
    est = view["estimate"]
    assert est["tdee"] == 2400
    assert est["suggested"] is None
    assert est["desired_rate_kg_week"] is None
    assert est["delta_to_goal"] is None


def test_view_delta_to_goal():
    view = _view(
        _good_entries(), _meals(list(range(28)), calories=2400.0), rate=0.3, goal=2400
    )
    assert view["estimate"]["goal_calories"] == 2400
    assert view["estimate"]["delta_to_goal"] == 350


def test_view_uncertain_flag_outside_the_soft_band():
    # Holding weight on 4200 kcal: plausible enough to show, odd enough to caveat.
    view = _view(_good_entries(), _meals(list(range(28)), calories=4200.0))
    assert view["estimate"] is not None
    assert view["estimate"]["uncertain"] is True


def test_view_latest_reports_both_raw_and_smoothed():
    # Noisy series, so the two genuinely differ: the last raw reading is 1.5 kg above
    # the trend and the Ø tile must not inherit that spike.
    entries = _daily([80.0] * 27 + [81.5])
    view = _view(entries, _meals(list(range(28))))
    assert view["latest"]["date"] == entries[-1][0]
    assert view["latest"]["raw_kg"] == 81.5
    assert view["latest"]["n"] == 7
    assert view["latest"]["avg_kg"] == pytest.approx(80.21, abs=0.01)


def test_view_gaining_estimate_lands_below_intake():
    # The end-to-end version of the sign test: +0.2 kg/week on 3000 kcal.
    entries = _daily([80.0 + 0.2 / 7 * i for i in range(28)])
    view = _view(entries, _meals(list(range(28)), calories=3000.0), rate=0.2)
    assert view["trend"]["direction"] == "up"
    assert view["trend"]["per_week_kg"] == pytest.approx(0.2, abs=1e-3)
    assert view["estimate"]["tdee"] < 3000
    assert view["estimate"]["tdee"] == 2780  # 3000 − 0.2*7700/7 = 3000 − 220


def test_view_losing_estimate_lands_above_intake():
    entries = _daily([80.0 - 0.2 / 7 * i for i in range(28)])
    view = _view(entries, _meals(list(range(28)), calories=2000.0), rate=-0.2)
    assert view["trend"]["direction"] == "down"
    assert view["estimate"]["tdee"] == 2220  # 2000 + 220


def test_view_noisy_but_flat_weight_lands_close_to_intake():
    # Realistic ±200 g water wobble around a constant 80 kg. The smoothing has to
    # absorb it: a naive raw-endpoint slope would read a trend that isn't there.
    entries = _daily([80.0 + (0.2 if i % 2 else -0.2) for i in range(28)])
    view = _view(entries, _meals(list(range(28)), calories=2400.0))
    assert abs(view["estimate"]["tdee"] - 2400) <= 30


def test_view_todays_weigh_in_counts_immediately():
    """A weigh-in is complete when taken, so it must count the moment it is saved.

    Regression test for a message that read "0 von mindestens 6" while the page
    listed the weigh-in the user had just entered underneath it.
    """
    view = build_weight_view(
        [(_d(27), 77.6)], [], trend_start=_d(0), trend_end=_d(27),
        intake_end=_d(26), desired_rate_kg_week=None, goal_calories=None,
    )
    assert view["blocked"] == "too_few_entries"
    assert "1 von mindestens" in view["blocked_message"]


def test_view_todays_meals_are_excluded_from_the_intake_average():
    """Today is only half logged, so its calories must not drag the average down."""
    series = _meals(list(range(28)), calories=2400.0)
    series[27]["calories"] = 200.0  # today, barely logged so far
    view = _view(_good_entries(), series)
    assert view["intake"]["avg_calories"] == 2400
    assert view["estimate"]["tdee"] == 2400
