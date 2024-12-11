"""таблица ответа агента

Revision ID: 4356f39ba63e
Revises: 5ff23721cb44
Create Date: 2024-11-17 17:41:23.178227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '4356f39ba63e'
down_revision: Union[str, None] = '5ff23721cb44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name, column_name):
    """Проверяет существование колонки в таблице."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # Создаем временную таблицу с новой схемой
    op.create_table(
        'agentanswer_temp',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('answer', sa.Text(), nullable=True),  # Меняем nullable на True
        sa.Column('language', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Переносим данные из старой таблицы в новую
    op.execute("""
        INSERT INTO agentanswer_temp (id, answer, language, updated_at)
        SELECT id, answer, language, updated_at FROM agentanswer
    """)

    # Удаляем старую таблицу
    op.drop_table('agentanswer')

    # Переименовываем новую таблицу в старое имя
    op.rename_table('agentanswer_temp', 'agentanswer')


def downgrade():
    # Создаем временную таблицу с исходной схемой
    op.create_table(
        'agentanswer_temp',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('answer', sa.Text(), nullable=False),  # Возвращаем nullable на False
        sa.Column('language', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Переносим данные обратно в старую таблицу
    op.execute("""
        INSERT INTO agentanswer_temp (id, answer, language, updated_at)
        SELECT id, answer, language, updated_at FROM agentanswer
    """)

    # Удаляем измененную таблицу
    op.drop_table('agentanswer')

    # Переименовываем временную таблицу обратно
    op.rename_table('agentanswer_temp', 'agentanswer')