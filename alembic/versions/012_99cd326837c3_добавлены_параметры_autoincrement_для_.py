"""добавлены параметры autoincrement для всех таблиц к полям id

Revision ID: 99cd326837c3
Revises: f6ef51cd0375
Create Date: 2024-12-10 17:55:24.156995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99cd326837c3'
down_revision: Union[str, None] = 'f6ef51cd0375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
