"""Production hardening: Numeric percentile, covering indexes, constraint alignment, timestamps.

Revision ID: 0004_production_hardening
Revises: 0003_password_hash_and_fk
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_production_hardening"
down_revision: str | Sequence[str] | None = "0003_password_hash_and_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply production schema hardening."""
    # 1. Exact decimal precision for MHT-CET 7-decimal percentiles
    op.alter_column(
        "admission_cutoffs",
        "percentile",
        existing_type=sa.Float(),
        type_=sa.Numeric(precision=10, scale=7),
        existing_nullable=False,
    )

    # 2. Align users.username unique constraint name with ORM model (uq_users_username)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.drop_constraint("username", "users", type_="unique")

    # 3. Add covering and lookup indexes
    op.create_index("ix_colleges_division", "colleges", ["division"])
    op.create_index(
        "ix_branches_branch_name_college_code",
        "branches",
        ["branch_name", "college_code"],
    )
    op.drop_index("ix_admission_cutoffs_recommender", table_name="admission_cutoffs")
    op.create_index(
        "ix_admission_cutoffs_recommender",
        "admission_cutoffs",
        ["admission_stage", "category", "admission_year", "branch_code", "percentile"],
    )
    op.create_index(
        "ix_admission_cutoffs_stage_year_branch",
        "admission_cutoffs",
        ["admission_stage", "admission_year", "branch_code", "percentile"],
    )

    # 4. Audit timestamps
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "saved_list_items",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "saved_list_items",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "admission_cutoffs",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Revert production schema hardening."""
    op.drop_column("admission_cutoffs", "created_at")
    op.drop_column("saved_list_items", "updated_at")
    op.drop_column("saved_list_items", "created_at")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "created_at")

    op.drop_index("ix_admission_cutoffs_stage_year_branch", table_name="admission_cutoffs")
    op.drop_index("ix_admission_cutoffs_recommender", table_name="admission_cutoffs")
    op.create_index(
        "ix_admission_cutoffs_recommender",
        "admission_cutoffs",
        ["admission_year", "admission_stage", "category", "branch_code"],
    )
    op.drop_index("ix_branches_branch_name_college_code", table_name="branches")
    op.drop_index("ix_colleges_division", table_name="colleges")

    op.create_unique_constraint("username", "users", ["username"])
    op.drop_constraint("uq_users_username", "users", type_="unique")

    op.alter_column(
        "admission_cutoffs",
        "percentile",
        existing_type=sa.Numeric(precision=10, scale=7),
        type_=sa.Float(),
        existing_nullable=False,
    )
