import os
import re
from pathlib import Path

# Путь к папке с миграциями
MIGRATIONS_DIR = "alembic/versions"

# Регулярные выражения для поиска Revision ID и Revises
REVISION_PATTERN = re.compile(r"Revision ID: (\w+)")
REVISES_PATTERN = re.compile(r"Revises: (\w+|None)")

def extract_revision_data(file_path):
    """Извлекает данные о миграции: Revision ID и Revises."""
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
        revision = REVISION_PATTERN.search(content)
        revises = REVISES_PATTERN.search(content)
        return {
            "file": file_path,
            "revision": revision.group(1) if revision else None,
            "revises": revises.group(1) if revises else None
        }

def build_chain(revision_data):
    """Строит цепочку миграций на основе Revision ID и Revises."""
    lookup = {item["revision"]: item for item in revision_data if item["revision"]}
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

def rename_files(ordered_migrations):
    """Переименовывает файлы в соответствии с порядком."""
    for index, migration in enumerate(ordered_migrations, start=1):
        new_name = f"{index:03d}_{Path(migration['file']).name}"
        new_path = Path(MIGRATIONS_DIR) / new_name
        os.rename(migration["file"], new_path)
        print(f"Renamed {migration['file']} to {new_path}")

def main():
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
