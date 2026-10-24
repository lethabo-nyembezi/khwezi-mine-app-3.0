"""data_loader.py - reads and writes the CSV data files (the app's storage layer)."""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
DATA = BASE / "data"
if not DATA.is_dir():
    DATA = BASE


def _normalize_lowercase_columns(df):
    abbreviations = {"id": "ID", "c": "C", "mm": "mm", "s": "s", "l": "L", "h": "h"}
    return df.rename(columns={
        column: "_".join(abbreviations.get(part, part.capitalize()) for part in column.split("_"))
        for column in df.columns if column == column.lower()
    })


def load_all():
    """Load every CSV into a dictionary of DataFrames, converting date columns."""
    equipment = _normalize_lowercase_columns(pd.read_csv(DATA / "Equipment_database.csv"))
    equipment["Last_Maintenance_Date"] = pd.to_datetime(equipment["Last_Maintenance_Date"])
    equipment["Next_Maintenance_Date"] = pd.to_datetime(equipment["Next_Maintenance_Date"])
    readings = _normalize_lowercase_columns(pd.read_csv(DATA / "equipment_readings.csv"))
    readings["Date"] = pd.to_datetime(readings["Date"])
    return {
        "equipment": equipment,
        "readings": readings,
        "workers": pd.read_csv(DATA / "workers.csv", parse_dates=["Safety_Training_Expiry_Date"]),
        "incidents": pd.read_csv(DATA / "safety_incidents.csv", parse_dates=["Date"]),
        "risks": pd.read_csv(DATA / "risk_register.csv", parse_dates=["Next_Review_Date"]),
        "users": pd.read_csv(DATA / "users.csv"),
        "perms": pd.read_csv(DATA / "role_permissions.csv"),
    }


def save_csv(df, filename):
    """Write a DataFrame back to its CSV (used when adding incidents or users)."""
    df.to_csv(DATA / filename, index=False)
