import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import set_key


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
DB_NAME = "homeworks"


def read_creds(creds_file: Path) -> dict[str, str]:
    if not creds_file.is_file():
        raise SystemExit(f"Файл с доступами не найден: {creds_file}")
    with closing(sqlite3.connect(f"{creds_file.as_uri()}?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            (DB_NAME,),
        ).fetchone()
    if row is None:
        raise SystemExit(f"В таблице access нет записи для базы {DB_NAME}")
    url, port, user, password, db_name = row
    return {
        "DB_HOST": str(url),
        "DB_PORT": str(port),
        "DB_USER": str(user),
        "DB_PASSWORD": str(password),
        "DB_NAME": str(db_name),
    }


def main():
    parser = argparse.ArgumentParser(description="Переносит доступы к базе из creds.db в файл .env")
    parser.add_argument("creds_db", type=Path, help="путь к SQLite-файлу с доступами (creds.db)")
    args = parser.parse_args()

    creds = read_creds(args.creds_db.expanduser().resolve())
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    for key, value in creds.items():
        set_key(ENV_FILE, key, value, quote_mode="always")
    print(f"Доступы к базе {creds['DB_NAME']} записаны в {ENV_FILE}")


if __name__ == "__main__":
    main()
