"""Rendering plain numbers for the German UI.

The counterpart to ``money.eur``: the admin panel has formatted its euro figures
German-style from the start, while the macro values on the user-facing pages went
out as raw ``float`` repr — "600.0 kcal", "18.0g P", "1.5g F". Two faults in one
string: a trailing ``.0`` on a whole number, and a decimal point in a locale that
writes a comma.

Lives in ``core`` for the same reason as ``money``: it is testable without
importing FastAPI.
"""

from typing import Optional

_DEFAULT_DIGITS = 1


def de_num(value: Optional[float], digits: int = _DEFAULT_DIGITS) -> str:
    """A macro value as a German reader expects it, or an em dash when unset.

    Whole numbers lose the decimal part entirely ("600", not "600,0"); a real
    fraction keeps it with a comma ("1,5"). One digit by default because that is
    the precision an estimated macro can honestly claim.

    The em dash matches what the templates already print for a missing value, so
    the filter can replace those inline conditionals rather than sit beside them.
    """
    if value is None:
        return "—"
    rounded = round(float(value), digits)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{digits}f}".replace(".", ",")


def de_fixed(value: Optional[float], digits: int = _DEFAULT_DIGITS) -> str:
    """Wie ``de_num``, aber die Nachkommastelle bleibt auch bei einer runden Zahl.

    Der Unterschied ist inhaltlich, nicht kosmetisch: ein Makrowert ist eine
    Schaetzung, da ist die nachgestellte Null Rauschen und faellt weg. Eine
    Wiegung ist ein Messwert — "71,0 kg" sagt aus, dass auf 100 g genau gewogen
    wurde, "71 kg" waere eine Angabe geringerer Genauigkeit.
    """
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}".replace(".", ",")
