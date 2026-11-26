from pydantic import BaseModel


class TrendsQuery(BaseModel):
    """Query parameters for historical cutoff trends."""

    branch_code: str
    category: str
    level: str | None = None


class TrendPointOut(BaseModel):
    """Single historical CAP round cutoff point."""

    year: int
    round: int
    level: str
    percentile: float


class TrendsResponse(BaseModel):
    """Historical cutoff trend response."""

    branch_code: str
    count: int
    trends: list[TrendPointOut]
