"""Extract: скачивание сырого датасета с Google Drive и чтение CSV."""

from __future__ import annotations

import logging
from pathlib import Path

import gdown
import pandas as pd

from etl.config import DATASET_ID, KEY_COLUMN

logger = logging.getLogger(__name__)


def is_dataset_file(file: Path) -> bool:
    """Проверяет, что файл похож на CSV с датасетом, а не на HTML-страницу Google Drive."""
    if not file.is_file() or file.stat().st_size < 1024:
        return False
    with file.open(encoding="utf-8", errors="replace") as f:
        header = f.readline()
    return KEY_COLUMN in header and header.count(",") > 10


def download_dataset(target: Path, dataset_id: str = DATASET_ID) -> Path:
    """Скачивает датасет в ``target``, если там еще нет корректной копии."""
    if is_dataset_file(target):
        logger.info("Датасет уже скачан: %s", target)
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    logger.info("Скачиваю датасет с Google Drive в %s", target)
    try:
        gdown.download(id=dataset_id, output=str(tmp), quiet=True)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Скачивание не удалось ({e}). Проверьте интернет и запустите еще раз") from e

    if not is_dataset_file(tmp):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "Скачанный файл не похож на CSV с датасетом — скорее всего, Google Drive "
            "исчерпал лимит скачиваний. Попробуйте позже или передайте файл через --source"
        )

    tmp.replace(target)
    return target


def extract(raw_file: Path, source: Path | None = None) -> pd.DataFrame:
    """Возвращает сырой датасет.

    Если передан ``source``, читает локальный CSV, иначе скачивает файл в ``raw_file``.
    """
    if source is not None:
        if not is_dataset_file(source):
            raise RuntimeError(f"Файл {source} не найден или не похож на CSV с датасетом")
        path = source
    else:
        path = download_dataset(raw_file)

    raw = pd.read_csv(path, low_memory=False)
    logger.info("Прочитано %d строк и %d столбцов из %s", *raw.shape, path)
    return raw
