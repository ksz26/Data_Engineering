"""Общие настройки ETL: пути, источник данных, описание столбцов."""

from __future__ import annotations

from pathlib import Path

# src/etl/config.py -> корень репозитория на два уровня выше пакета
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_FILE_NAME = "Oil_Pipeline_Accidents.csv"
PROCESSED_FILE_NAME = "oil_pipeline_accidents.parquet"
ENV_FILE = PROJECT_ROOT / ".env"

# файл датасета на Google Drive
DATASET_ID = "1ngApLH7YljcLcSuWmQSlw8jnU22NfcJx"

# база и таблица для загрузки
DB_NAME = "homeworks"
DEFAULT_TABLE = "bulatovaks"
MAX_DB_ROWS = 100
ENV_KEYS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")

# столбцы сырого датасета
KEY_COLUMN = "Report Number"

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

# форматы разные: у аварии AM/PM, у остановки и перезапуска 24 часа
DATETIME_FORMATS = {
    "Accident Date/Time": "%m/%d/%Y %I:%M %p",
    "Shutdown Date/Time": "%m/%d/%Y %H:%M",
    "Restart Date/Time": "%m/%d/%Y %H:%M",
}

# блок о пострадавших заполняют, только если они есть, поэтому пропуск = 0
VICTIM_COLUMNS = [
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

# эвакуации — тоже счетчик, но пропуск здесь значит «не указано» (поле появилось не сразу)
COUNT_COLUMNS = ["Public Evacuations", *VICTIM_COLUMNS]

COST_PART_COLUMNS = [
    "Property Damage Costs",
    "Lost Commodity Costs",
    "Public/Private Property Damage Costs",
    "Emergency Response Costs",
    "Environmental Remediation Costs",
    "Other Costs",
]
COST_COLUMNS = [*COST_PART_COLUMNS, "All Costs"]

VOLUME_COLUMNS = [
    "Unintentional Release (Barrels)",
    "Intentional Release (Barrels)",
    "Liquid Recovery (Barrels)",
    "Net Loss (Barrels)",
]

REQUIRED_COLUMNS = [
    KEY_COLUMN,
    "Supplemental Number",
    "Accident Year",
    "Operator ID",
    "Operator Name",
    "Pipeline/Facility Name",
    "Accident City",
    "Accident County",
    "Accident State",
    "Accident Latitude",
    "Accident Longitude",
    *DATETIME_FORMATS,
    *FLAG_COLUMNS,
    *CATEGORY_COLUMNS,
    *VOLUME_COLUMNS,
    *COUNT_COLUMNS,
    *COST_COLUMNS,
]
