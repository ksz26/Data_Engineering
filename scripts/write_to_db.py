import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
TABLE_NAME = "bulatovaks"
ENV_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]


def read_env() -> dict[str, str]:
    load_dotenv(ENV_FILE)
    creds = {key: os.getenv(key) for key in ENV_KEYS}
    missing = [key for key, value in creds.items() if not value]
    if missing:
        raise SystemExit(
            f"В {ENV_FILE} не хватает переменных: {', '.join(missing)}. "
            "Сначала запустите python scripts/creds_to_env.py /путь/к/creds.db"
        )
    return creds


def main():
    creds = read_env()

    data = pd.read_csv(BASE_DIR / "data" / "Oil_Pipeline_Accidents.csv", nrows=100, low_memory=False)
    if len(data) != 100:
        raise ValueError("В датасете меньше 100 строк")

    engine = create_engine(URL.create(
        "postgresql+psycopg2", username=creds["DB_USER"], password=creds["DB_PASSWORD"],
        host=creds["DB_HOST"], port=int(creds["DB_PORT"]), database=creds["DB_NAME"],
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
