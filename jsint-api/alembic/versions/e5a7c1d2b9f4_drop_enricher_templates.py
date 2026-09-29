"""drop enricher_templates

The enricher-templates feature is gone: YAML-defined enrichers, their API,
the ``run_template_enricher`` task and the template editor UI were all
removed, so the table that backed them has no remaining readers.

The historical create/alter revisions stay in place so an existing database
still walks the same chain; this revision is what takes the table back out.

Revision ID: e5a7c1d2b9f4
Revises: 9a1f8b2c4d3e
Create Date: 2026-09-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5a7c1d2b9f4"
down_revision: Union[str, None] = "9a1f8b2c4d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the table; its indexes and foreign key go with it."""
    op.drop_table("enricher_templates")


def downgrade() -> None:
    """Recreate the table exactly as the feature left it."""
    op.create_table(
        "enricher_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("version", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["profiles.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_enricher_templates_owner_id",
        "enricher_templates",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "idx_enricher_templates_name", "enricher_templates", ["name"], unique=False
    )
    op.create_index(
        "idx_enricher_templates_category",
        "enricher_templates",
        ["category"],
        unique=False,
    )
    op.create_index(
        "idx_enricher_templates_is_public",
        "enricher_templates",
        ["is_public"],
        unique=False,
    )
