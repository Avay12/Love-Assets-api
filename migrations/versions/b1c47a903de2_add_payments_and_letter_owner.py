"""Add the payments table and letters.user_id

Both were added to the models without a migration, so `alembic upgrade head`
produced a schema the app could not run against: every typed-letter POST
writes `letters.user_id` and inserts a `payments` row.

Revision ID: b1c47a903de2
Revises: 70e4c68333c6
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b1c47a903de2"
down_revision: Union[str, Sequence[str], None] = "70e4c68333c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite cannot ALTER a table to add a foreign key; batch mode rebuilds it.
    with op.batch_alter_table("letters") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_letters_user_id_users", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )
    op.create_index(op.f("ix_letters_user_id"), "letters", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("payment_code", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("letter_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["letter_id"], ["letters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_payment_code"), "payments", ["payment_code"], unique=True)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_payments_letter_id"), "payments", ["letter_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_letter_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_payment_code"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_letters_user_id"), table_name="letters")
    with op.batch_alter_table("letters") as batch:
        batch.drop_constraint("fk_letters_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
