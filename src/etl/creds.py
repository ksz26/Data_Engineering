"""Доступы к базе: перенос из SQLite-файла в .env и чтение из .env.

Логика из ДЗ №7 (scripts/creds_to_env.py и scripts/write_to_db.py), встроенная в пакет.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv, set_key

from etl.config import DB_NAME, ENV_FILE, ENV_KEYS

logger = logging.getLogger(__name__)


def creds_from_sqlite(creds_file: Path, db_name: str = DB_NAME) -> dict[str, str]:
    """Читает доступы к базе ``db_name`` из таблицы ``access`` SQLite-файла (только чтение)."""
    if not creds_file.is_file():
        raise FileNotFoundError(f"Файл с доступами не найден: {creds_file}")
    with closing(sqlite3.connect(f"{creds_file.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            (db_name,),
        ).fetchone()
    if row is None:
        raise LookupError(f"В таблице access нет записи для базы {db_name}")
    return dict(zip(ENV_KEYS, map(str, row)))


def save_to_env(creds: dict[str, str], env_file: Path = ENV_FILE) -> None:
    """Записывает доступы в .env, не трогая остальные строки файла."""
    env_file.touch(mode=0o600, exist_ok=True)
    for key, value in creds.items():
        set_key(env_file, key, value, quote_mode="always")
    logger.info("Доступы к базе %s записаны в %s", creds["DB_NAME"], env_file)


def creds_from_env(env_file: Path = ENV_FILE) -> dict[str, str]:
    """Читает доступы к базе из .env (или из переменных окружения)."""
    load_dotenv(env_file)
    creds = {key: os.getenv(key, "") for key in ENV_KEYS}
    missing = [key for key, value in creds.items() if not value]
    if missing:
        raise RuntimeError(
            f"В {env_file} не хватает переменных: {', '.join(missing)}. "
            "Запустите ETL с аргументом --creds-db /путь/к/creds.db"
        )
    return creds
