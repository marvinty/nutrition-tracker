from pydantic import BaseModel


class UsageRead(BaseModel):
    """Today's AI credit budget, for the dashboard's remaining-credits line."""

    used: int
    limit: int
    remaining: int
    tier: str
    # False once the app-wide ceiling is spent. Distinct from remaining == 0: the user
    # may still have personal credits and would otherwise see a full budget and an
    # unexplained 429.
    system_available: bool

    model_config = {"from_attributes": True}
