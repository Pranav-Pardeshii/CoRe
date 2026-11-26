from pydantic import BaseModel, Field


class RecommenderQuery(BaseModel):
    """Query parameters for college recommendations."""

    percentile: float = Field(ge=0, le=100)
    category: str
    branch: str
    division: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=5, le=30)


class EligibleCollegeOut(BaseModel):
    """Aggregated eligible college/branch recommendation item."""

    college: str
    branch: str
    branch_code: str
    min_cutoff: float
    max_cutoff: float


class RecommenderResponse(BaseModel):
    """Paginated recommendation response."""

    eligible_colleges: list[EligibleCollegeOut]
    count: int
