"""Transform: приведение типов, чистка и флаги качества по выводам EDA (ноутбук, раздел 9)."""

from __future__ import annotations

import logging

import pandas as pd

from etl.config import (
    CATEGORY_COLUMNS,
    COUNT_COLUMNS,
    DATETIME_FORMATS,
    FLAG_COLUMNS,
    INCOMPLETE_YEARS,
    VICTIM_COLUMNS,
)
from etl.utils import in_usa, to_snake_case

logger = logging.getLogger(__name__)

TEXT_COLUMNS = ["Operator Name", "Pipeline/Facility Name", "Accident City", "Accident County", "Accident State"]
FLAG_VALUES = {"YES": True, "NO": False}


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Даты — каждая со своим форматом, флаги YES/NO — в nullable boolean, счетчики людей — в Int64."""
    df = df.copy()

    for col, fmt in DATETIME_FORMATS.items():
        df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")

    # map вместо eq("YES"): пропуск должен остаться пропуском, а не стать False
    for col in FLAG_COLUMNS:
        df[col] = df[col].map(FLAG_VALUES).astype("boolean")

    # блок о пострадавших заполняют только при наличии пострадавших
    df[VICTIM_COLUMNS] = df[VICTIM_COLUMNS].fillna(0)
    for col in COUNT_COLUMNS:
        df[col] = df[col].astype("Int64")

    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")

    return df


def clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """Убирает лишние пробелы и суффиксы COUNTY/PARISH у округов."""
    df = df.copy()
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

    df["Accident County"] = (
        df["Accident County"].str.upper().str.replace(r"\s+(COUNTY|PARISH)$", "", regex=True).str.strip()
    )
    return df


def fix_longitude_sign(df: pd.DataFrame) -> pd.DataFrame:
    """Возвращает потерянный минус у долготы, если с ним точка попадает в США."""
    df = df.copy()
    lat, lon = df["Accident Latitude"], df["Accident Longitude"]
    lost_minus = (lon > 0) & in_usa(lat, -lon)
    df.loc[lost_minus, "Accident Longitude"] = -lon[lost_minus]
    if lost_minus.any():
        logger.info("Исправлен знак долготы у %d записей", lost_minus.sum())
    return df


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет длительность простоя и флаги, по которым запись можно исключить из расчетов.

    Записи не удаляются: флаг говорит, для каких расчетов запись не годится.
    """
    df = df.copy()
    accident, shutdown, restart = df["Accident Date/Time"], df["Shutdown Date/Time"], df["Restart Date/Time"]
    lat, lon = df["Accident Latitude"], df["Accident Longitude"]

    df["Downtime Hours"] = (restart - shutdown).dt.total_seconds() / 3600

    # время реакции по таким записям считать нельзя
    df["Is Shutdown Before Accident"] = (shutdown < accident).astype("boolean")
    df["Is Shutdown Same Minute"] = (shutdown == accident).astype("boolean")
    df.loc[shutdown.isna() | accident.isna(), ["Is Shutdown Before Accident", "Is Shutdown Same Minute"]] = pd.NA

    # нулевые затраты — скорее всего, затраты просто не внесли
    df["Is Zero Costs"] = df["All Costs"].eq(0)

    has_geo = lat.notna() & lon.notna()
    df["Is Outside USA"] = (has_geo & ~in_usa(lat, lon)).astype("boolean")
    df.loc[~has_geo, "Is Outside USA"] = pd.NA

    # Полнота года известна из описания источника, а не из числа месяцев с авариями.
    df["Is Incomplete Year"] = df["Accident Year"].isin(INCOMPLETE_YEARS)

    return df


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    """Полный цикл преобразования: типы, чистка, флаги, имена столбцов в snake_case."""
    df = convert_types(raw)
    df = clean_text(df)
    df = fix_longitude_sign(df)
    df = add_quality_flags(df)

    df = df.sort_values(["Accident Date/Time", "Report Number"], kind="stable").reset_index(drop=True)
    df.columns = [to_snake_case(col) for col in df.columns]
    logger.info("После преобразования: %d строк и %d столбцов", *df.shape)
    return df
