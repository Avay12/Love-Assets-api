"""use jsonb for photos and details on postgres

Revision ID: 9f1fe1e23121
Revises: ac9a0f2248b6
Create Date: 2026-08-02 09:24:16.378274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f1fe1e23121'
down_revision: Union[str, Sequence[str], None] = 'ac9a0f2248b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # JSONB exists only on Postgres, and SQLite has no ALTER COLUMN TYPE at
    # all -- unguarded, this raised "near ALTER: syntax error" and stopped the
    # whole chain, so a dev database could not be built from migrations.
    # SQLite stores both as TEXT regardless, so skipping changes nothing.
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column('letters', 'photos',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
               existing_nullable=True)
    op.alter_column('letters', 'details',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column('letters', 'details',
               existing_type=sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True)
    op.alter_column('letters', 'photos',
               existing_type=sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True)
    # ### end Alembic commands ###
