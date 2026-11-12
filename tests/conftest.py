from __future__ import annotations

import pandas as pd
import pytest

from etl.config import COST_PART_COLUMNS, REQUIRED_COLUMNS, VICTIM_COLUMNS


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """Три записи в формате сырого CSV (по образцу первых строк датасета)."""
    rows = [
        {
            "Report Number": 20100016, "Accident Year": 2010, "Accident Date/Time": "1/1/2010 7:15 AM",
            "Operator Name": "ONEOK NGL PIPELINE LP", "Accident County": "MCPHERSON COUNTY ",
            "Accident State": "KS", "Accident Latitude": 38.6707, "Accident Longitude": -97.78123,
            "Liquid Ignition": "NO", "Liquid Explosion": "NO", "Pipeline Shutdown": "NO",
            "Unintentional Release (Barrels)": 21.0, "Liquid Recovery (Barrels)": 0.0, "Net Loss (Barrels)": 21.0,
            "Property Damage Costs": 110.0, "Lost Commodity Costs": 1517.0, "All Costs": 1627,
        },
        {
            "Report Number": 20100254, "Accident Year": 2010, "Accident Date/Time": "1/4/2010 8:30 AM",
            "Operator Name": "MOBIL  PIPE  LINE COMPANY", "Accident County": "Harris",
            "Accident State": "TX", "Accident Latitude": 40.63, "Accident Longitude": 14.2,  # потерян минус
            "Liquid Ignition": "YES", "Liquid Explosion": "YES", "Pipeline Shutdown": "YES",
            "Shutdown Date/Time": "1/4/2010 8:30", "Restart Date/Time": "1/5/2010 20:30",
            "Unintentional Release (Barrels)": 0.12, "Liquid Recovery (Barrels)": 0.12, "Net Loss (Barrels)": 0.0,
            "Property Damage Costs": 4000.0, "Lost Commodity Costs": 8.0, "All Costs": 4008,
            "All Injuries": 2.0, "Other Injuries": 2.0,
        },
        {
            "Report Number": 20170001, "Accident Year": 2017, "Accident Date/Time": "1/2/2017 11:38 PM",
            "Operator Name": "PLAINS PIPELINE, L.P.", "Accident County": "KERN",
            "Accident State": "CA", "Accident Latitude": float("nan"), "Accident Longitude": float("nan"),
            "Liquid Ignition": "NO", "Liquid Explosion": "NO", "Pipeline Shutdown": float("nan"),
            "Unintentional Release (Barrels)": 2.0, "Liquid Recovery (Barrels)": 0.0, "Net Loss (Barrels)": 2.0,
            "All Costs": 0,
        },
    ]
    df = pd.DataFrame(rows).reindex(columns=REQUIRED_COLUMNS)
    df[COST_PART_COLUMNS] = df[COST_PART_COLUMNS].fillna(0.0)
    df["Supplemental Number"] = [17305, 17331, 30000]
    df["Operator ID"] = [32109, 15786, 300]
    df["Intentional Release (Barrels)"] = 0.0
    df[VICTIM_COLUMNS] = df[VICTIM_COLUMNS].astype(float)
    return df
