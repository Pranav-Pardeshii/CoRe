from pydantic import BaseModel


class TrendsQuery(BaseModel):
    """Query parameters for historical cutoff trends."""

    branch_code: str
    category: str


class TrendPointOut(BaseModel):
    """Single historical CAP round cutoff point."""

    year: int
    round: int
    percentile: float


class TrendsResponse(BaseModel):
    """Historical cutoff trend response."""

    branch_code: str
    count: int
    trends: list[TrendPointOut]
