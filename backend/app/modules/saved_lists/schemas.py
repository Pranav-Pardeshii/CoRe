from pydantic import BaseModel, field_validator


class SavedListCreateRequest(BaseModel):
    """Request payload for saving a branch to the user's list."""

    branch_code: str


class SavedListReorderRequest(BaseModel):
    """Request payload for reordering the user's saved list."""

    ordered_list: list[int]

    @field_validator("ordered_list")
    @classmethod
    def validate_unique_ids(cls, value: list[int]) -> list[int]:
        """Reject duplicate item IDs before hitting the database."""
        if len(value) != len(set(value)):
            raise ValueError("ordered_list must not contain duplicate IDs.")
        return value


class SavedListItemOut(BaseModel):
    """Saved list item returned to the client."""

    id: int
    college_name: str
    branch_name: str


class SavedListResponse(BaseModel):
    """Ordered list of saved items for the authenticated user."""

    saved_list: list[SavedListItemOut]


class SavedListMessageResponse(BaseModel):
    """Generic message response for saved-list mutations."""

    message: str
