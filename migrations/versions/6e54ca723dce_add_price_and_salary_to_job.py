"""Add price and salary to job

Revision ID: 6e54ca723dce
Revises: 1e413035c0fd
Create Date: 2025-10-13 20:37:10.602937

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e54ca723dce'
down_revision = '1e413035c0fd'
branch_labels = None
depends_on = None



def upgrade():
    # --- PROJECT: price_* ---
    op.add_column('project', sa.Column('price_min', sa.Numeric(10, 2), nullable=True))
    op.add_column('project', sa.Column('price_max', sa.Numeric(10, 2), nullable=True))
    op.add_column('project', sa.Column('price_currency', sa.String(length=10), nullable=True))

    # Índices (opcionales pero recomendados)
    op.create_index('ix_project_price_min', 'project', ['price_min'], unique=False)
    op.create_index('ix_project_price_max', 'project', ['price_max'], unique=False)
    op.create_index('ix_project_price_currency', 'project', ['price_currency'], unique=False)

    # --- JOB: salary_* ---
    op.add_column('job', sa.Column('salary_min', sa.Numeric(10, 2), nullable=True))
    op.add_column('job', sa.Column('salary_max', sa.Numeric(10, 2), nullable=True))
    op.add_column('job', sa.Column('salary_currency', sa.String(length=10), nullable=True))
    op.add_column('job', sa.Column('salary_period', sa.String(length=10), nullable=True))  # hour/day/month/year

    # Índices
    op.create_index('ix_job_salary_min', 'job', ['salary_min'], unique=False)
    op.create_index('ix_job_salary_max', 'job', ['salary_max'], unique=False)
    op.create_index('ix_job_salary_currency', 'job', ['salary_currency'], unique=False)
    op.create_index('ix_job_salary_period', 'job', ['salary_period'], unique=False)


def downgrade():
    # JOB
    op.drop_index('ix_job_salary_period', table_name='job')
    op.drop_index('ix_job_salary_currency', table_name='job')
    op.drop_index('ix_job_salary_max', table_name='job')
    op.drop_index('ix_job_salary_min', table_name='job')

    op.drop_column('job', 'salary_period')
    op.drop_column('job', 'salary_currency')
    op.drop_column('job', 'salary_max')
    op.drop_column('job', 'salary_min')

    # PROJECT
    op.drop_index('ix_project_price_currency', table_name='project')
    op.drop_index('ix_project_price_max', table_name='project')
    op.drop_index('ix_project_price_min', table_name='project')

    op.drop_column('project', 'price_currency')
    op.drop_column('project', 'price_max')
    op.drop_column('project', 'price_min')