"""alter project.cmc_rank to int

Revision ID: 21
Revises: 20
Create Date: 2025-03-02 20:40:39.385878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21'
down_revision: Union[str, None] = '20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'project',
        'cmc_rank',
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="cmc_rank::integer"
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    op.alter_column(
        'project',
        'cmc_rank',
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(length=30),
        existing_nullable=True
    )
    # ### end Alembic commands ###
