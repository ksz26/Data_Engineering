from __future__ import annotations

import sqlite3
from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy.exc import StatementError

from etl.config import COST_COLUMNS, VOLUME_COLUMNS
from etl.creds import creds_from_env, creds_from_sqlite, save_to_env
from etl.errors import CredsError, EtlError, ExtractError, LoadError
from etl.load import load_to_db, select_rows
from etl.main import parse_args, run
from etl.transform import transform
from etl.utils import to_snake_case
from etl.validate import ValidationError, validate_processed, validate_raw


def test_to_snake_case():
    assert to_snake_case("Unintentional Release (Barrels)") == "unintentional_release_barrels"
    assert to_snake_case("Public/Private Property Damage Costs") == "public_private_property_damage_costs"


def test_transform_types_and_cleaning(raw_df):
    df = transform(raw_df)

    assert str(df["accident_date_time"].dtype) == "datetime64[ns]"
    assert str(df["pipeline_shutdown"].dtype) == "boolean"
    assert df["pipeline_shutdown"].isna().sum() == 1  # пропуск не превратился в False
    assert str(df["all_injuries"].dtype) == "Int64"
    assert df["all_injuries"].tolist() == [0, 2, 0]  # пропуск о пострадавших = 0
    assert df["public_evacuations"].isna().all()  # а эвакуации остаются пропуском
    assert df.loc[1, "operator_name"] == "MOBIL PIPE LINE COMPANY"
    assert df["accident_county"].tolist() == ["MCPHERSON", "HARRIS", "KERN"]


def test_transform_quality_flags(raw_df):
    df = transform(raw_df)

    # с минусом точка все равно не в США (как Линден с долготой -14) — не исправляем, а помечаем
    assert df.loc[1, "accident_longitude"] == 14.2
    assert df.loc[1, "is_outside_usa"]
    assert df.loc[1, "is_shutdown_same_minute"]
    assert df.loc[1, "downtime_hours"] == 36
    assert df.loc[2, "is_zero_costs"]
    assert df["is_incomplete_year"].tolist() == [False, False, True]
    assert pd.isna(df.loc[2, "is_outside_usa"])


def test_incomplete_year_does_not_depend_on_months_with_accidents(raw_df):
    # В 2017 году есть запись для каждого месяца, но год по-прежнему неполный.
    rows = pd.concat([raw_df.iloc[[2]]] * 12, ignore_index=True)
    rows["Accident Date/Time"] = [f"{month}/2/2017 11:38 PM" for month in range(1, 13)]
    assert transform(rows)["is_incomplete_year"].all()


def test_longitude_sign_fixed(raw_df):
    raw_df.loc[1, "Accident Longitude"] = 74.21  # Линден, Нью-Джерси, без минуса
    df = transform(raw_df)
    assert df.loc[1, "accident_longitude"] == -74.21
    assert not df.loc[1, "is_outside_usa"]


def test_validation_passes(raw_df):
    validate_raw(raw_df)
    counts = validate_processed(transform(raw_df))
    assert counts["остановка в ту же минуту"] == 1
    assert counts["нулевые затраты"] == 1


def test_raw_validation_catches_errors(raw_df):
    raw_df.loc[0, "Liquid Ignition"] = "MAYBE"
    raw_df.loc[1, "Report Number"] = raw_df.loc[0, "Report Number"]
    with pytest.raises(ValidationError, match="Liquid Ignition"):
        validate_raw(raw_df)


def test_raw_validation_missing_columns(raw_df):
    with pytest.raises(ValidationError, match="All Costs"):
        validate_raw(raw_df.drop(columns="All Costs"))


@pytest.mark.parametrize("column", [*VOLUME_COLUMNS, *COST_COLUMNS])
def test_raw_validation_rejects_negative_volume_and_cost(raw_df, column):
    raw_df.loc[0, column] = -1
    with pytest.raises(ValidationError, match=column.replace("(", r"\(").replace(")", r"\)")):
        validate_raw(raw_df)


def test_raw_validation_accepts_missing_volume_and_cost(raw_df):
    raw_df[[*VOLUME_COLUMNS, *COST_COLUMNS]] = float("nan")
    validate_raw(raw_df)


def test_processed_validation_catches_cost_mismatch(raw_df):
    raw_df.loc[0, "All Costs"] = 999_999
    with pytest.raises(ValidationError, match="all_costs = сумма затрат"):
        validate_processed(transform(raw_df))


def test_select_rows_limit(raw_df):
    assert len(select_rows(raw_df, 2)) == 2
    many_rows = pd.concat([raw_df] * 40, ignore_index=True)
    pd.testing.assert_frame_equal(select_rows(many_rows, 100), many_rows.iloc[:100])
    with pytest.raises(LoadError):
        select_rows(raw_df, 101)


def test_all_etl_errors_share_base_class():
    for error_class in (ExtractError, CredsError, ValidationError, LoadError):
        assert issubclass(error_class, EtlError)


def test_missing_credentials_raise_creds_error(tmp_path):
    with pytest.raises(CredsError):
        creds_from_sqlite(tmp_path / "missing.db")


def test_database_error_mentions_table_and_preserves_cause(raw_df, monkeypatch):
    original = ValueError("ошибка драйвера")
    error = StatementError("ошибка SQLAlchemy", None, None, original)
    engine = Mock()
    engine.begin.side_effect = error
    monkeypatch.setattr("etl.load.make_engine", lambda creds: engine)

    with pytest.raises(LoadError, match="таблицей accidents: ошибка драйвера") as exc:
        load_to_db(raw_df, "accidents", {})
    assert exc.value.__cause__ is error
    engine.dispose.assert_called_once()


def test_cli_rejects_more_than_100_rows():
    with pytest.raises(SystemExit):
        parse_args(["--rows", "101"])


def test_creds_roundtrip(tmp_path, monkeypatch):
    creds_db = tmp_path / "creds.db"
    with sqlite3.connect(creds_db) as connection:
        connection.execute("CREATE TABLE access (url, port, user, pass, db_name)")
        connection.execute("INSERT INTO access VALUES ('db.host', 5432, 'student', 'p@ss', 'homeworks')")
    env_file = tmp_path / ".env"
    for key in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)

    save_to_env(creds_from_sqlite(creds_db), env_file)
    creds = creds_from_env(env_file)
    assert creds["DB_HOST"] == "db.host"
    assert creds["DB_PORT"] == "5432"
    assert creds["DB_PASSWORD"] == "p@ss"


def test_pipeline_without_db(raw_df, tmp_path):
    source = tmp_path / "source.csv"
    raw_df.to_csv(source, index=False)
    args = parse_args(["--source", str(source), "--data-dir", str(tmp_path), "--skip-db", "--rows", "2"])
    run(args)
    result = pd.read_parquet(tmp_path / "processed" / "oil_pipeline_accidents.parquet")
    assert len(result) == 3
