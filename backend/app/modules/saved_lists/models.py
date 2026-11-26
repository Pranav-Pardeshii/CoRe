from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.database.base import Base


class SavedListItem(Base):
    """User's saved college/branch preference item with ordering position."""

    __tablename__ = "saved_list_items"
    __table_args__ = (
        UniqueConstraint("user_id", "branch_code", name="uq_saved_list_items_user_branch"),
        CheckConstraint("sort_order >= 1", name="sort_order_positive"),
        Index("ix_saved_list_items_user_sort_order", "user_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    college_code: Mapped[str] = mapped_column(String(10), nullable=False)
    branch_code: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("branches.branch_code"),
        nullable=False,
    )
    college_name: Mapped[str] = mapped_column(String(300), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(300), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
