"""Вспомогательные функции, общие для transform и validate."""

from __future__ import annotations

import re

import pandas as pd


def to_snake_case(name: str) -> str:
    """``"Unintentional Release (Barrels)"`` -> ``"unintentional_release_barrels"``."""
    return re.sub(r"[^0-9a-z]+", "_", name.lower()).strip("_")


def in_usa(lat: pd.Series, lon: pd.Series) -> pd.Series:
    """Грубая проверка, что точка лежит в США: материк, Аляска, Гавайи, Пуэрто-Рико.

    Границы те же, что в EDA (раздел 4). Для пропусков возвращает False.
    """
    return (
        (lat.between(24, 49.5) & lon.between(-125, -66))
        | (lat.between(51, 72) & lon.between(-180, -129))
        | (lat.between(18, 23) & lon.between(-161, -154))
        | (lat.between(17.5, 18.6) & lon.between(-68, -65))
    )
