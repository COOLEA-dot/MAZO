"""Add google_id to users

Revision ID: 1e413035c0fd
Revises: 
Create Date: 2025-10-03 18:43:39.888124

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e413035c0fd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # añade la columna (nullable para no romper existentes)
    op.add_column('users', sa.Column('google_id', sa.String(length=200), nullable=True))
    # crea índice único con NOMBRE explícito (mejor que UniqueConstraint en SQLite)
    op.create_index('uq_users_google_id', 'users', ['google_id'], unique=True)

def downgrade():
    op.drop_index('uq_users_google_id', table_name='users')
    op.drop_column('users', 'google_id')

    # ### end Alembic commands ###
