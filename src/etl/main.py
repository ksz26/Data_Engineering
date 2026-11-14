"""Точка входа ETL: extract -> validate -> transform -> validate -> load.

Примеры (из корня репозитория, после ``pip install -e .``)::

    python -m etl.main --creds-db ~/creds.db        # первый запуск: доступы -> .env, весь цикл
    python -m etl.main --if-exists replace          # перезаписать таблицу
    python -m etl.main --rows 20 --skip-db          # без базы: только проверки и Parquet
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from etl.config import DATA_DIR, DEFAULT_TABLE, ENV_FILE, MAX_DB_ROWS, PROCESSED_FILE_NAME, RAW_FILE_NAME
from etl.creds import creds_from_env, creds_from_sqlite, save_to_env
from etl.errors import EtlError
from etl.extract import extract
from etl.load import IF_EXISTS_CHOICES, load_to_db, save_parquet, select_rows
from etl.transform import transform
from etl.validate import validate_processed, validate_raw

logger = logging.getLogger("etl")

TABLE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def rows_arg(value: str) -> int:
    rows = int(value)
    if not 1 <= rows <= MAX_DB_ROWS:
        raise argparse.ArgumentTypeError(f"от 1 до {MAX_DB_ROWS}")
    return rows


def table_arg(value: str) -> str:
    if not TABLE_NAME_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("латинские строчные буквы, цифры и _, не длиннее 63 символов")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="etl",
        description="ETL датасета Oil Pipeline Accidents: Google Drive -> проверки -> Parquet и PostgreSQL",
    )
    parser.add_argument("--rows", type=rows_arg, default=MAX_DB_ROWS,
                        help=f"сколько строк записать в базу, от 1 до {MAX_DB_ROWS} (по умолчанию {MAX_DB_ROWS})")
    parser.add_argument("--table", type=table_arg, default=DEFAULT_TABLE,
                        help=f"таблица в базе (по умолчанию {DEFAULT_TABLE})")
    parser.add_argument("--if-exists", choices=IF_EXISTS_CHOICES, default="fail",
                        help="что делать, если таблица уже есть: fail — остановиться (по умолчанию), "
                             "replace — перезаписать")
    parser.add_argument("--creds-db", type=Path,
                        help="SQLite-файл с доступами: перед запуском они будут записаны в .env")
    parser.add_argument("--source", type=Path,
                        help="локальный CSV вместо скачивания с Google Drive")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR,
                        help="папка для сырого и обработанного датасета (по умолчанию data/)")
    parser.add_argument("--skip-db", action="store_true",
                        help="не писать в базу: только extract, transform, проверки и Parquet")
    parser.add_argument("-v", "--verbose", action="store_true", help="подробный лог")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    if args.creds_db is not None:
        save_to_env(creds_from_sqlite(args.creds_db.expanduser()), ENV_FILE)
    # доступы проверяем до тяжелых шагов, чтобы не ждать скачивания впустую
    creds = None if args.skip_db else creds_from_env(ENV_FILE)

    raw = extract(args.data_dir / "raw" / RAW_FILE_NAME, source=args.source)
    validate_raw(raw)

    processed = transform(raw)
    validate_processed(processed)
    save_parquet(processed, args.data_dir / "processed" / PROCESSED_FILE_NAME)

    sample = select_rows(processed, args.rows)
    if args.skip_db:
        logger.info("Запись в базу пропущена (--skip-db), подготовлено %d строк", len(sample))
        return
    load_to_db(sample, args.table, creds, if_exists=args.if_exists)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        run(args)
    except EtlError as e:  # все ожидаемые ошибки пайплайна; остальное — баг, его покажет traceback
        if args.verbose:
            logger.exception("ETL остановлен")
        else:
            logger.error("ETL остановлен: %s", e)
        return 1
    logger.info("ETL завершен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
