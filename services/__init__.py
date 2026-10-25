
from pathlib import Path

import pandas as pd
import plotly.express as px


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "energy_data.csv"

# Illustrative factor for demonstration only.
# Replace with a documented, region-appropriate factor
# before making real-world emissions claims.
DEMO_EMISSION_FACTOR = 0.40


def load_data():
    df = pd.read_csv(DATA_FILE)

    required = {"month", "facility", "electricity_kwh"}
    if not required.issubset(df.columns):
        raise ValueError("Dataset is missing required columns.")

    df["month"] = pd.to_datetime(
        df["month"], format="%Y-%m", errors="raise"
    )
    df["electricity_kwh"] = pd.to_numeric(
        df["electricity_kwh"], errors="raise"
    )

    if df[list(required)].isnull().any().any():
        raise ValueError("Dataset contains missing values.")

    if (df["electricity_kwh"] < 0).any():
        raise ValueError("Energy consumption cannot be negative.")

    if df["facility"].astype(str).str.strip().eq("").any():
        raise ValueError("Facility names cannot be empty.")

    df["emissions_kg"] = (
        df["electricity_kwh"] * DEMO_EMISSION_FACTOR
    )

    return df


def get_dashboard_data():
    df = load_data()

    total_energy = df["electricity_kwh"].sum()
    total_emissions = df["emissions_kg"].sum()
    facility_count = df["facility"].nunique()

    monthly = (
        df.groupby("month", as_index=False)
        .agg(
            electricity_kwh=("electricity_kwh", "sum"),
            emissions_kg=("emissions_kg", "sum"),
        )
        .sort_values("month")
    )

    facilities = (
        df.groupby("facility", as_index=False)
        .agg(
            electricity_kwh=("electricity_kwh", "sum"),
            emissions_kg=("emissions_kg", "sum"),
        )
        .sort_values("electricity_kwh", ascending=False)
    )

    monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")

    trend_fig = px.line(
        monthly,
        x="month_label",
        y="electricity_kwh",
        markers=True,
        title="Monthly Electricity Consumption",
        labels={
            "month_label": "Month",
            "electricity_kwh": "Electricity (kWh)",
        },
    )

    trend_fig.update_layout(template="plotly_dark")

    facility_fig = px.bar(
        facilities,
        x="facility",
        y="electricity_kwh",
        title="Energy Consumption by Facility",
        labels={
            "facility": "Facility",
            "electricity_kwh": "Electricity (kWh)",
        },
    )

    facility_fig.update_layout(template="plotly_dark")

    return {
        "total_energy": round(total_energy),
        "total_emissions": round(total_emissions),
        "facility_count": facility_count,
        "monthly_chart": trend_fig.to_html(
            full_html=False, include_plotlyjs="cdn"
        ),
        "facility_chart": facility_fig.to_html(
            full_html=False, include_plotlyjs=False
        ),
        "facilities": facilities.to_dict(orient="records"),
    }
