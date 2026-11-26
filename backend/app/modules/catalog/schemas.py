from pydantic import BaseModel


class CatalogFiltersResponse(BaseModel):
    """Distinct filter values available across the admission catalog."""

    categories: list[str]
    branches: list[str]
    divisions: list[str]
    years: list[int]
    levels: list[str]
