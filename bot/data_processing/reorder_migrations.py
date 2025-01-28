import os
from pathlib import Path
from typing import List, Dict, Optional

from bot.utils.common.consts import REVISION_PATTERN, REVISES_PATTERN, MIGRATIONS_DIR


def extract_revision_data(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Извлекает данные о миграции: Revision ID и Revises.

    :param file_path: Путь к файлу миграции
    :return: Словарь с данными о ревизии и связанных миграциях
    """

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
        revision = REVISION_PATTERN.search(content)
        revises = REVISES_PATTERN.search(content)
        return {
            "file": str(file_path),
            "revision": revision.group(1) if revision else None,
            "revises": revises.group(1) if revises else None
        }


def build_chain(revision_data: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    """
    Строит цепочку миграций на основе Revision ID и Revises.

    :param revision_data: Список словарей с данными о ревизиях
    :return: Упорядоченный список миграций
    """

    chain = []

    # Найти первый элемент цепочки (где Revises == None)
    current = next((item for item in revision_data if item["revises"] in (None, "None")), None)

    while current:
        chain.append(current)
        next_revision = current["revision"]
        current = next((item for item in revision_data if item["revises"] == next_revision), None)

    if len(chain) != len(revision_data):
        print("Warning: Not all migrations are connected. Some files might be skipped.")

    return chain


def rename_files(ordered_migrations: List[Dict[str, Optional[str]]]) -> None:
    """
    Переименовывает файлы в соответствии с порядком.

    :param ordered_migrations: Упорядоченный список миграций
    """

    for index, migration in enumerate(ordered_migrations, start=1):
        new_name = f"{index:03d}_{Path(migration['file']).name}"
        new_path = Path(MIGRATIONS_DIR) / new_name
        os.rename(migration["file"], new_path)
        print(f"Renamed {migration['file']} to {new_path}")


def main() -> None:
    """
    Запускает процесс переименования файлов миграций в соответствии с порядком.
    """

    # Получить все файлы миграций
    migration_files = sorted(Path(MIGRATIONS_DIR).glob("*.py"))
    if not migration_files:
        print("No migration files found!")
        return

    # Извлечь данные о ревизиях
    revision_data = [extract_revision_data(file) for file in migration_files]

    # Проверить на отсутствие данных
    for data in revision_data:
        if not data["revision"]:
            print(f"Warning: Revision ID not found in {data['file']}")
        if not data["revises"]:
            print(f"Warning: Revises not found in {data['file']}")

    # Построить цепочку миграций
    ordered_migrations = build_chain(revision_data)
    if not ordered_migrations:
        print("Could not determine migration order.")
        return

    # Переименовать файлы
    rename_files(ordered_migrations)


if __name__ == "__main__":
    main()
