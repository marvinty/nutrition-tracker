from sqlalchemy import Column, DateTime, Integer, String, func
from app.models.base import Base


class RateLimitHit(Base):
    """One recorded attempt against a throttled endpoint.

    Rows rather than a counter: a sliding window needs to know *when* each attempt
    happened, and a fixed-window counter would let an attacker fire a full budget at
    the end of one window and another at the start of the next.

    Deliberately in the database and not in process memory — production runs uvicorn
    with two workers, so an in-memory limiter would hand out its budget once per
    worker and drift apart under load. Volume is tiny: only failures are recorded, and
    ``prune_expired`` clears anything older than the window.
    """

    id = Column(Integer, primary_key=True, index=True)
    # "login", "signup", "forgot_password", "admin_login"
    scope = Column(String, nullable=False, index=True)
    # Either an IP or an account identifier — see rate_limit_service.ip_key/account_key,
    # which prefix them so the two namespaces cannot collide.
    key = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
