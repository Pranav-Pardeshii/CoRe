"""Rename users.password to password_hash and add saved_list_items.branch_code FK.

Revision ID: 0003_password_hash_and_fk
Revises: 0002_standardize_schema
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_password_hash_and_fk"
down_revision: str | Sequence[str] | None = "0002_standardize_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename users.password to password_hash and enforce branch_code FK on saved_list_items."""
    op.alter_column(
        "users",
        "password",
        new_column_name="password_hash",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_saved_list_items_branch_code_branches",
        "saved_list_items",
        "branches",
        ["branch_code"],
        ["branch_code"],
    )


def downgrade() -> None:
    """Revert branch_code FK and password_hash column rename."""
    op.drop_constraint(
        "fk_saved_list_items_branch_code_branches",
        "saved_list_items",
        type_="foreignkey",
    )
    op.alter_column(
        "users",
        "password_hash",
        new_column_name="password",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
