"""Standardize table/column naming, constraints, and query indexes.

Revision ID: 0002_standardize_schema
Revises: 0001_initial_schema
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0002_standardize_schema"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename legacy tables/columns and add constraints and query indexes."""
    # 1. Standardize cutoffs -> admission_cutoffs
    op.rename_table("cutoffs", "admission_cutoffs")
    op.alter_column(
        "admission_cutoffs",
        "year",
        new_column_name="admission_year",
        existing_type=sa.SmallInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "round",
        new_column_name="cap_round",
        existing_type=mysql.TINYINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "stage",
        new_column_name="admission_stage",
        existing_type=sa.String(length=5),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "rank",
        new_column_name="merit_rank",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.create_unique_constraint(
        "uq_admission_cutoffs_composite",
        "admission_cutoffs",
        [
            "branch_code",
            "admission_year",
            "cap_round",
            "level",
            "admission_stage",
            "category",
        ],
    )
    op.drop_constraint("unique_cutoff", "admission_cutoffs", type_="unique")
    op.create_check_constraint(
        "ck_admission_cutoffs_percentile_range",
        "admission_cutoffs",
        "percentile >= 0 AND percentile <= 100",
    )
    op.create_index(
        "ix_admission_cutoffs_recommender",
        "admission_cutoffs",
        ["admission_year", "admission_stage", "category", "branch_code"],
    )
    op.create_index(
        "ix_admission_cutoffs_trends",
        "admission_cutoffs",
        ["branch_code", "category", "admission_stage", "admission_year", "cap_round"],
    )

    # 2. Index branches.college_code for college-branch joins
    op.create_index("ix_branches_college_code", "branches", ["college_code"])

    # 3. Standardize saved_list -> saved_list_items
    op.rename_table("saved_list", "saved_list_items")
    op.alter_column(
        "saved_list_items",
        "rank",
        new_column_name="sort_order",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.create_unique_constraint(
        "uq_saved_list_items_user_branch",
        "saved_list_items",
        ["user_id", "branch_code"],
    )
    op.drop_constraint("uq_saved_list_user_branch", "saved_list_items", type_="unique")
    op.create_check_constraint(
        "ck_saved_list_items_sort_order_positive",
        "saved_list_items",
        "sort_order >= 1",
    )
    op.create_index(
        "ix_saved_list_items_user_sort_order",
        "saved_list_items",
        ["user_id", "sort_order"],
    )


def downgrade() -> None:
    """Revert standardized table/column names, constraints, and indexes."""
    op.drop_index("ix_saved_list_items_user_sort_order", table_name="saved_list_items")
    op.drop_constraint(
        "ck_saved_list_items_sort_order_positive",
        "saved_list_items",
        type_="check",
    )
    op.create_unique_constraint(
        "uq_saved_list_user_branch",
        "saved_list_items",
        ["user_id", "branch_code"],
    )
    op.drop_constraint("uq_saved_list_items_user_branch", "saved_list_items", type_="unique")
    op.alter_column(
        "saved_list_items",
        "sort_order",
        new_column_name="rank",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.rename_table("saved_list_items", "saved_list")

    op.drop_index("ix_branches_college_code", table_name="branches")

    op.drop_index("ix_admission_cutoffs_trends", table_name="admission_cutoffs")
    op.drop_index("ix_admission_cutoffs_recommender", table_name="admission_cutoffs")
    op.drop_constraint(
        "ck_admission_cutoffs_percentile_range",
        "admission_cutoffs",
        type_="check",
    )
    op.create_unique_constraint(
        "unique_cutoff",
        "admission_cutoffs",
        ["branch_code", "admission_year", "cap_round", "level", "admission_stage", "category"],
    )
    op.drop_constraint("uq_admission_cutoffs_composite", "admission_cutoffs", type_="unique")
    op.alter_column(
        "admission_cutoffs",
        "merit_rank",
        new_column_name="rank",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "admission_stage",
        new_column_name="stage",
        existing_type=sa.String(length=5),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "cap_round",
        new_column_name="round",
        existing_type=mysql.TINYINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "admission_cutoffs",
        "admission_year",
        new_column_name="year",
        existing_type=sa.SmallInteger(),
        existing_nullable=False,
    )
    op.rename_table("admission_cutoffs", "cutoffs")
