"""таблица ответа агента

Revision ID: f04c4a90bab1
Revises: 4356f39ba63e
Create Date: 2024-11-20 13:12:52.100617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f04c4a90bab1'
down_revision: Union[str, None] = '4356f39ba63e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Используем batch mode для добавления внешнего ключа
    with op.batch_alter_table('agentanswer', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_agentanswer_project', 'project', ['project_id'], ['id'])

    # Добавляем новый столбец к таблице calculation
    op.add_column('calculation', sa.Column('agent_answer', sa.Text(), nullable=True))


def downgrade() -> None:
    # Откатываем изменения с использованием batch mode
    with op.batch_alter_table('agentanswer', schema=None) as batch_op:
        batch_op.drop_constraint('fk_agentanswer_project', type_='foreignkey')
        batch_op.drop_column('project_id')

    # Удаляем столбец из таблицы calculation
    op.drop_column('calculation', 'agent_answer')
