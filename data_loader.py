"""data_loader.py - reads and writes the CSV data files (the app's storage layer)."""
from pathlib import Path
import pandas as pd

DATA = Path(__file__).parent / "data"


def load_all():
    """Load every CSV into a dictionary of DataFrames, converting date columns."""
    return {
        "equipment": pd.read_csv(DATA / "Equipment_database.csv",
                                 parse_dates=["Last_Maintenance_Date", "Next_Maintenance_Date"]),
        "readings": pd.read_csv(DATA / "equipment_readings.csv", parse_dates=["Date"]),
        "workers": pd.read_csv(DATA / "workers.csv", parse_dates=["Safety_Training_Expiry_Date"]),
        "incidents": pd.read_csv(DATA / "safety_incidents.csv", parse_dates=["Date"]),
        "risks": pd.read_csv(DATA / "risk_register.csv", parse_dates=["Next_Review_Date"]),
        "users": pd.read_csv(DATA / "users.csv"),
        "perms": pd.read_csv(DATA / "role_permissions.csv"),
    }


def save_csv(df, filename):
    """Write a DataFrame back to its CSV (used when adding incidents or users)."""
    df.to_csv(DATA / filename, index=False)
