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


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)

    df = load_dataset()

    print(df.head(10))
    rows, cols = df.shape
    print(f"\nРазмер датасета: {rows} строк, {cols} столбцов")
