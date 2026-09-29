"""admin accounts: is_admin, status and created_at on profiles

Replaces the unused ``profiles.is_active`` boolean with an explicit account
lifecycle so registrations can wait for administrator approval.

Existing accounts are grandfathered in as ``active``; the column default then
becomes ``pending`` so every new registration needs approval.

Revision ID: 9a1f8b2c4d3e
Revises: c7d1f0a92b3e
Create Date: 2026-09-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1f8b2c4d3e"
down_revision: Union[str, None] = "c7d1f0a92b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "status", sa.String(length=16), server_default="active", nullable=False
        ),
    )

    # Accounts that exist today keep working: map the old flag onto the new
    # lifecycle, then switch the default for new rows to "pending".
    op.execute(
        "UPDATE profiles SET status = CASE WHEN is_active THEN 'active' "
        "ELSE 'suspended' END"
    )
    op.alter_column("profiles", "status", server_default="pending")

    op.drop_column("profiles", "is_active")


def downgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.execute("UPDATE profiles SET is_active = (status = 'active')")
    op.drop_column("profiles", "status")
    op.drop_column("profiles", "is_admin")
    op.drop_column("profiles", "created_at")
