"""Validate: проверки сырых данных на входе и результата перед загрузкой.

Проверки взяты из EDA (ноутбук, разделы 2 и 4) и описаны схемами Pandera.
Нарушение схемы останавливает ETL. Известные проблемы источника, которые
не мешают загрузке (остановка раньше аварии, координаты вне США и т.п.),
не считаются ошибкой: transform помечает их флагами, а здесь они только
выводятся в лог.
"""

from __future__ import annotations

import logging

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from etl.config import (
    COST_COLUMNS,
    COST_PART_COLUMNS,
    COUNT_COLUMNS,
    DATETIME_FORMATS,
    FLAG_COLUMNS,
    KEY_COLUMN,
    REQUIRED_COLUMNS,
    VICTIM_COLUMNS,
    VOLUME_COLUMNS,
)
from etl.errors import ValidationError
from etl.utils import to_snake_case

logger = logging.getLogger(__name__)

COST_TOLERANCE = 1  # доллар: суммы затрат в источнике целые
VOLUME_TOLERANCE = 0.01  # баррель: объемы указаны с точностью до сотых


def _parses(fmt: str) -> pa.Check:
    return pa.Check(
        lambda s: pd.to_datetime(s, format=fmt, errors="coerce").notna(),
        name=f"формат даты {fmt}",
    )


RAW_SCHEMA = pa.DataFrameSchema(
    columns={
        KEY_COLUMN: pa.Column(
            int, pa.Check(lambda s: s.astype(str).str.fullmatch(r"\d{8}"), name="8 цифр"), unique=True
        ),
        "Accident Year": pa.Column(int),
        "Accident State": pa.Column(str, pa.Check.str_matches(r"^[A-Z]{2}$"), nullable=True),
        **{col: pa.Column(str, _parses(fmt), nullable=(col != "Accident Date/Time"))
           for col, fmt in DATETIME_FORMATS.items()},
        **{col: pa.Column(str, pa.Check.isin(["YES", "NO"]), nullable=True) for col in FLAG_COLUMNS},
    },
    checks=pa.Check(lambda df: len(df) > 0, name="датасет не пустой"),
    name="сырой датасет",
)


def _snake(cols: list[str]) -> list[str]:
    return [to_snake_case(col) for col in cols]


def _non_negative(dtype, nullable: bool = True) -> pa.Column:
    return pa.Column(dtype, pa.Check.ge(0), nullable=nullable)


def _restart_after_shutdown(df: pd.DataFrame) -> pd.Series:
    # перезапуск не может быть раньше остановки
    rest, shut = df["restart_date_time"], df["shutdown_date_time"]
    return rest.isna() | shut.isna() | (rest >= shut)


PROCESSED_SCHEMA = pa.DataFrameSchema(
    columns={
        "report_number": pa.Column(int, unique=True),
        "accident_year": pa.Column(int),
        "accident_date_time": pa.Column("datetime64[ns]"),
        "shutdown_date_time": pa.Column("datetime64[ns]", nullable=True),
        "restart_date_time": pa.Column("datetime64[ns]", nullable=True),
        "accident_latitude": pa.Column(float, pa.Check.in_range(-90, 90), nullable=True),
        "accident_longitude": pa.Column(float, pa.Check.in_range(-180, 180), nullable=True),
        **{col: pa.Column("boolean", nullable=True) for col in _snake(FLAG_COLUMNS)},
        **{col: _non_negative("Int64") for col in _snake(COUNT_COLUMNS)},
        **{col: _non_negative("Int64", nullable=False) for col in _snake(VICTIM_COLUMNS)},
        **{col: _non_negative(float) for col in _snake(VOLUME_COLUMNS)},
        **{col: _non_negative(float) for col in _snake(COST_COLUMNS) if col != "all_costs"},
        "all_costs": _non_negative(int, nullable=False),
        "downtime_hours": pa.Column(float, nullable=True),
    },
    checks=[
        pa.Check(lambda df: df["accident_year"] == df["accident_date_time"].dt.year,
                 name="год совпадает с датой аварии"),
        pa.Check(lambda df: (df[_snake(COST_PART_COLUMNS)].sum(axis=1) - df["all_costs"]).abs() <= COST_TOLERANCE,
                 name="all_costs = сумма затрат"),
        pa.Check(lambda df: ((df["unintentional_release_barrels"] - df["liquid_recovery_barrels"]
                              - df["net_loss_barrels"]).abs() <= VOLUME_TOLERANCE)
                 | df[["unintentional_release_barrels", "liquid_recovery_barrels", "net_loss_barrels"]]
                 .isna().any(axis=1),
                 name="net_loss = утечка - собрано"),
        pa.Check(lambda df: ~(df["liquid_explosion"].fillna(False) & ~df["liquid_ignition"].fillna(True)),
                 name="нет взрыва без возгорания"),
        pa.Check(_restart_after_shutdown, name="перезапуск не раньше остановки"),
    ],
    name="результат transform",
)


def _run(schema: pa.DataFrameSchema, df: pd.DataFrame) -> None:
    try:
        schema.validate(df, lazy=True)
    except SchemaErrors as e:
        cases = e.failure_cases
        summary = (
            cases.fillna({"column": "<таблица>"})
            .groupby(["column", "check"], dropna=False).size()
            .rename("нарушений").reset_index().to_string(index=False)
        )
        raise ValidationError(f"Проверка «{schema.name}» не пройдена:\n{summary}") from e
    logger.info("Проверка «%s» пройдена", schema.name)


def validate_raw(raw: pd.DataFrame) -> None:
    """Проверяет, что источник имеет ожидаемую структуру и форматы."""
    missing = [col for col in REQUIRED_COLUMNS if col not in raw.columns]
    if missing:
        raise ValidationError(f"В сыром датасете нет столбцов: {', '.join(missing)}")
    _run(RAW_SCHEMA, raw)


def report_quality(df: pd.DataFrame) -> dict[str, int]:
    """Выводит в лог известные проблемы источника, помеченные флагами в transform."""
    shut_without_date = int((df["pipeline_shutdown"].fillna(False) & df["shutdown_date_time"].isna()).sum())
    counts = {
        "остановка раньше аварии": int(df["is_shutdown_before_accident"].sum()),
        "остановка в ту же минуту": int(df["is_shutdown_same_minute"].sum()),
        "остановка YES без даты": shut_without_date,
        "координаты вне США": int(df["is_outside_usa"].sum()),
        "нулевые затраты": int(df["is_zero_costs"].sum()),
        "неполный год": int(df["is_incomplete_year"].sum()),
    }
    for name, count in counts.items():
        if count:
            logger.warning("Качество данных: %s — %d записей (помечены, не удалены)", name, count)
    return counts


def validate_processed(df: pd.DataFrame) -> dict[str, int]:
    """Проверяет результат transform и возвращает число записей с известными проблемами."""
    _run(PROCESSED_SCHEMA, df)
    return report_quality(df)
