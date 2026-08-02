"""Rendering euro amounts for the admin panel.

Lives in ``core`` rather than next to the admin router for two reasons: the router
is supposed to hold no logic, and the rules below are the ones that decide whether
a cost figure tells the truth — which makes them worth testing without importing
FastAPI (the local Python has no python-multipart, so the router is unimportable
there; see CLAUDE.md on the two httpx-only test modules).
"""

from typing import Optional

_DEFAULT_DIGITS = 4


def eur(value: Optional[float], digits: int = _DEFAULT_DIGITS) -> str:
    """German-formatted euro amount, or an em dash when there is nothing to show.

    Four decimals by default because a single meal log costs a fraction of a cent —
    rounding to two would print "0,00 €" down an entire column.
    """
    if value is None:
        return "—"
    return f"{value:.{digits}f} €".replace(".", ",")


def eur_auto(value: Optional[float]) -> str:
    """Two decimals once the amount reads as money, four while it is still fractions
    of a cent. A young install would otherwise show "0,00 €" for spend that is real."""
    if value is None:
        return "—"
    return eur(value, 2 if abs(value) >= 1 else _DEFAULT_DIGITS)


def eur_bucket(bucket, digits: Optional[int] = _DEFAULT_DIGITS) -> str:
    """A cost bucket's euro figure, honest about what it does and does not cover.

    Three cases, because collapsing them is how a cost report starts lying:

    - nothing in the bucket could be priced — say "unbekannt"; 0,0000 € would read
      as free, which is the one mistake the whole costing feature exists to avoid
    - some of it could — "mind." marks the figure as a lower bound
    - all of it could — plain amount

    ``digits=None`` scales the precision to the amount, for the headline tiles.
    """
    if bucket.calls and bucket.unpriced_calls == bucket.calls:
        return "unbekannt"
    formatted = eur_auto(bucket.eur) if digits is None else eur(bucket.eur, digits)
    return f"mind. {formatted}" if bucket.unpriced_calls else formatted
