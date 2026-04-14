"""add needs_attention to conversations

Revision ID: 002
Revises: 001
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversations",
        sa.Column("needs_attention", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("conversations", "needs_attention")
