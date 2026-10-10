from pathlib import Path

import gdown
import pandas as pd

DATASET_ID = "1ngApLH7YljcLcSuWmQSlw8jnU22NfcJx"

BASE_DIR = Path(__file__).resolve().parent
DATASET_FILE = BASE_DIR / "data" / "Oil_Pipeline_Accidents.csv"


def is_dataset_file(file: Path) -> bool:
    if not file.is_file() or file.stat().st_size < 1024:
        return False
    with file.open(encoding="utf-8", errors="replace") as f:
        header = f.readline()
    return "Report Number" in header and header.count(",") > 10


def download_dataset() -> Path:
    if is_dataset_file(DATASET_FILE):
        print(f"Файл {DATASET_FILE} уже скачан, загрузка не требуется")
        return DATASET_FILE

    DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATASET_FILE.parent / (DATASET_FILE.name + ".tmp")
    print("Скачиваю датасет с Google Drive...")
    try:
        gdown.download(id=DATASET_ID, output=str(tmp))
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Скачивание не удалось ({e}). Проверьте интернет и запустите скрипт еще раз")

    if not is_dataset_file(tmp):
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            "Скачанный файл не похож на CSV с датасетом — скорее всего, Google Drive "
            "исчерпал лимит скачиваний. Попробуйте запустить скрипт позже"
        )

    tmp.replace(DATASET_FILE)
    print("Датасет сохранен в папку data/")
    return DATASET_FILE


def load_dataset() -> pd.DataFrame:
    return pd.read_csv(download_dataset(), low_memory=False)


FLAG_COLUMNS = ["Liquid Ignition", "Liquid Explosion", "Pipeline Shutdown"]

CATEGORY_COLUMNS = [
    "Pipeline Location",
    "Pipeline Type",
    "Liquid Type",
    "Liquid Subtype",
    "Liquid Name",
    "Cause Category",
    "Cause Subcategory",
]

DATETIME_COLUMNS = ["Accident Date/Time", "Shutdown Date/Time", "Restart Date/Time"]

DATETIME_FORMATS = {
    "Accident Date/Time": "%m/%d/%Y %I:%M %p",
    "Shutdown Date/Time": "%m/%d/%Y %H:%M",
    "Restart Date/Time": "%m/%d/%Y %H:%M",
}

COUNT_COLUMNS = [
    "Public Evacuations",
    "Operator Employee Injuries",
    "Operator Contractor Injuries",
    "Emergency Responder Injuries",
    "Other Injuries",
    "Public Injuries",
    "All Injuries",
    "Operator Employee Fatalities",
    "Operator Contractor Fatalities",
    "Emergency Responder Fatalities",
    "Other Fatalities",
    "Public Fatalities",
    "All Fatalities",
]


def convert_column_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in FLAG_COLUMNS:
        df[col] = df[col].eq("YES")

    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")

    for col, fmt in DATETIME_FORMATS.items():
        df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")

    for col in COUNT_COLUMNS:
        df[col] = df[col].astype("Int64")

    return df


def save_parquet(df: pd.DataFrame, path: Path = BASE_DIR / "data" / "Oil_Pipeline_Accidents.parquet") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"DataFrame сохранен в {path}")
    return path


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)

    df = load_dataset()

    print(df.head(10))
    rows, cols = df.shape
    print(f"\nРазмер датасета: {rows} строк, {cols} столбцов")

    df = convert_column_types(df)
    print("\nТипы колонок после приведения:")
    print(df.dtypes.to_string())

    print("\nНезаполненных значений в колонках с датами:")
    print(df[DATETIME_COLUMNS].isna().sum().to_string())

    save_parquet(df)
