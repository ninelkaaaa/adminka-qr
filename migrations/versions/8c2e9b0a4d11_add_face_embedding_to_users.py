"""Add face embedding to users

Revision ID: 8c2e9b0a4d11
Revises: 3878dbb87855
Create Date: 2026-04-18 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c2e9b0a4d11'
down_revision = '3878dbb87855'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('face_embedding', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('users', 'face_embedding')
