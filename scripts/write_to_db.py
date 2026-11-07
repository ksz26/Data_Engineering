import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


BASE_DIR = Path(__file__).resolve().parent.parent
TABLE_NAME = "bulatovaks"


def main():
    load_dotenv(BASE_DIR / ".env")
    creds_path = os.getenv("CREDS_DB")
    if not creds_path:
        raise SystemExit("Не найдена переменная CREDS_DB — создайте файл .env с путем к creds.db")
    creds_file = Path(creds_path).expanduser().resolve()
    with closing(sqlite3.connect(f"{creds_file.as_uri()}?mode=ro", uri=True)) as connection:
        url, port, user, password, db_name = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            ("homeworks",),
        ).fetchone()

    data = pd.read_csv(BASE_DIR / "data" / "Oil_Pipeline_Accidents.csv", nrows=100, low_memory=False)
    if len(data) != 100:
        raise ValueError("В датасете меньше 100 строк")

    engine = create_engine(URL.create(
        "postgresql+psycopg2", username=user, password=password,
        host=url, port=int(port), database=db_name,
    ))
    with engine.begin() as connection:
        data.to_sql(TABLE_NAME, connection, index=False, if_exists="fail")
        count = connection.execute(text(f'SELECT COUNT(*) FROM "{TABLE_NAME}"')).scalar_one()
        if count != 100:
            raise ValueError(f"В таблицу записано {count} строк вместо 100")
    engine.dispose()
    print(f"В таблицу {TABLE_NAME} записано {count} строк")


if __name__ == "__main__":
    main()
