"""Initial CoRe MySQL schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial application tables."""
    op.create_table(
        "colleges",
        sa.Column("college_code", sa.String(length=10), nullable=False),
        sa.Column("college_name", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=300), nullable=True),
        sa.Column("division", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("college_code"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "branches",
        sa.Column("branch_code", sa.String(length=15), nullable=False),
        sa.Column("branch_name", sa.String(length=300), nullable=False),
        sa.Column("college_code", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["college_code"], ["colleges.college_code"]),
        sa.PrimaryKeyConstraint("branch_code"),
    )

    op.create_table(
        "cutoffs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("branch_code", sa.String(length=15), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("round", mysql.TINYINT(), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("stage", sa.String(length=5), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["branch_code"], ["branches.branch_code"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_code",
            "year",
            "round",
            "level",
            "stage",
            "category",
            name="unique_cutoff",
        ),
    )

    op.create_table(
        "saved_list",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("college_code", sa.String(length=10), nullable=False),
        sa.Column("branch_code", sa.String(length=15), nullable=False),
        sa.Column("college_name", sa.String(length=300), nullable=False),
        sa.Column("branch_name", sa.String(length=300), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "branch_code", name="uq_saved_list_user_branch"),
    )


def downgrade() -> None:
    """Drop initial application tables."""
    op.drop_table("saved_list")
    op.drop_table("cutoffs")
    op.drop_table("branches")
    op.drop_table("users")
    op.drop_table("colleges")
