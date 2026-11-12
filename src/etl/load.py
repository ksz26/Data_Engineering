"""Load: сохранение результата в Parquet и запись не больше 100 строк в PostgreSQL."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import URL, create_engine, inspect, text

from etl.config import MAX_DB_ROWS

logger = logging.getLogger(__name__)

IF_EXISTS_CHOICES = ("fail", "replace")


def save_parquet(df: pd.DataFrame, path: Path) -> Path:
    """Сохраняет весь обработанный датасет в Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("Обработанный датасет сохранен в %s", path)
    return path


def select_rows(df: pd.DataFrame, rows: int) -> pd.DataFrame:
    """Берет первые ``rows`` строк (не больше 100) для записи в базу."""
    if not 1 <= rows <= MAX_DB_ROWS:
        raise ValueError(f"В базу можно записать от 1 до {MAX_DB_ROWS} строк, передано {rows}")
    return df.head(rows)


def make_engine(creds: dict[str, str]):
    return create_engine(URL.create(
        "postgresql+psycopg2",
        username=creds["DB_USER"],
        password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"],
        port=int(creds["DB_PORT"]),
        database=creds["DB_NAME"],
    ))


def load_to_db(df: pd.DataFrame, table: str, creds: dict[str, str], if_exists: str = "fail") -> int:
    """Записывает ``df`` в таблицу ``table`` и проверяет число строк в той же транзакции.

    ``if_exists``: ``fail`` — остановиться, если таблица уже есть; ``replace`` — пересоздать.
    Дописывания нет специально: в таблице не должно оказаться больше 100 строк.
    Если проверка не прошла, транзакция откатывается. Возвращает число строк в таблице.
    """
    if len(df) > MAX_DB_ROWS:
        raise ValueError(f"В базу можно записать не больше {MAX_DB_ROWS} строк, передано {len(df)}")
    if if_exists not in IF_EXISTS_CHOICES:
        raise ValueError(f"if_exists должен быть одним из {IF_EXISTS_CHOICES}")

    engine = make_engine(creds)
    try:
        with engine.begin() as connection:
            if if_exists == "fail" and inspect(connection).has_table(table):
                raise RuntimeError(
                    f"Таблица {table} уже существует. Чтобы перезаписать ее, запустите с --if-exists replace"
                )
            df.to_sql(table, connection, index=False, if_exists=if_exists, method="multi")

            count = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
            if count != len(df):
                raise RuntimeError(f"В таблице {table} {count} строк, ожидалось {len(df)}")
    finally:
        engine.dispose()

    logger.info("В таблицу %s записано %d строк", table, count)
    return count
