"""Add the payments table and letters.user_id

Both were added to the models without a migration, so `alembic upgrade head`
produced a schema the app could not run against: every typed-letter POST
writes `letters.user_id` and inserts a `payments` row.

Because the models ran ahead of the chain, an environment that was ever booted
against `Base.metadata.create_all` already has some or all of this -- the
production database had `letters.user_id` but was still stamped at the previous
revision. So every step here is applied only if it is actually missing. That
makes this migration safe to run against a fresh database, a drifted one, or a
partially drifted one.

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

LETTERS_USER_FK = "fk_letters_user_id_users"
LETTERS_USER_IX = "ix_letters_user_id"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(insp: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(insp: sa.Inspector, table: str, name: str) -> bool:
    return any(i["name"] == name for i in insp.get_indexes(table))


def _has_fk_on(insp: sa.Inspector, table: str, column: str) -> bool:
    return any(column in fk["constrained_columns"] for fk in insp.get_foreign_keys(table))


def upgrade() -> None:
    insp = _inspector()
    is_sqlite = op.get_bind().dialect.name == "sqlite"

    # ---------------------------------------------------------- letters.user_id
    if not _has_column(insp, "letters", "user_id"):
        # SQLite cannot ALTER a table to add a foreign key; batch mode rebuilds
        # it. Postgres can, and batch mode there is needless table churn.
        if is_sqlite:
            with op.batch_alter_table("letters") as batch:
                batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(
                    LETTERS_USER_FK, "users", ["user_id"], ["id"], ondelete="SET NULL"
                )
        else:
            op.add_column("letters", sa.Column("user_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                LETTERS_USER_FK, "letters", "users", ["user_id"], ["id"], ondelete="SET NULL"
            )
        insp = _inspector()
    elif not _has_fk_on(insp, "letters", "user_id") and not is_sqlite:
        # Column present but unconstrained -- create_all leaves the FK behind on
        # some paths. Adding it separately is cheap and makes the two agree.
        op.create_foreign_key(
            LETTERS_USER_FK, "letters", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )

    if not _has_index(insp, "letters", LETTERS_USER_IX):
        op.create_index(LETTERS_USER_IX, "letters", ["user_id"], unique=False)

    # ---------------------------------------------------------------- payments
    if "payments" not in insp.get_table_names():
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
    else:
        insp = _inspector()
        for name, cols, unique in (
            ("ix_payments_id", ["id"], False),
            ("ix_payments_payment_code", ["payment_code"], True),
            ("ix_payments_user_id", ["user_id"], False),
            ("ix_payments_letter_id", ["letter_id"], False),
        ):
            if not _has_index(insp, "payments", name):
                op.create_index(name, "payments", cols, unique=unique)


def downgrade() -> None:
    insp = _inspector()
    is_sqlite = op.get_bind().dialect.name == "sqlite"

    if "payments" in insp.get_table_names():
        op.drop_table("payments")

    if _has_index(insp, "letters", LETTERS_USER_IX):
        op.drop_index(LETTERS_USER_IX, table_name="letters")

    if _has_column(insp, "letters", "user_id"):
        if is_sqlite:
            with op.batch_alter_table("letters") as batch:
                batch.drop_column("user_id")
        else:
            op.drop_column("letters", "user_id")
