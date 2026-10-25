
from pathlib import Path

import pandas as pd
import plotly.express as px


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "energy_data.csv"

# Illustrative demo factor, not a verified regional factor.
DEMO_EMISSION_FACTOR = 0.40


# --------------------------------------------------
# Load and validate data
# --------------------------------------------------

def load_energy_data():
    """Load, validate, and prepare the energy dataset."""

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = [
        "month",
        "facility",
        "electricity_kwh",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required CSV columns: {missing}"
        )

    
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Track data-quality issues before cleaning.
    original_rows = len(df)
    duplicate_rows = int(df.duplicated().sum())

    df["month"] = pd.to_datetime(
        df["month"], errors="coerce"
    )

    df["electricity_kwh"] = pd.to_numeric(
        df["electricity_kwh"], errors="coerce"
    )

    df["facility"] = (
        df["facility"].astype("string").str.strip()
    )

    # Count invalid records before removing them.
    invalid_months = int(df["month"].isna().sum())
    invalid_energy = int(
        df["electricity_kwh"].isna().sum()
    )
    missing_facilities = int(
        (df["facility"].isna() | (df["facility"] == "")).sum()
    )
    negative_energy = int(
        (df["electricity_kwh"] < 0).sum()
    )

    # Remove unusable records.
    df = df.dropna(
        subset=["month", "facility", "electricity_kwh"]
    )

    df = df[
        (df["facility"] != "")
        & (df["electricity_kwh"] >= 0)
    ].copy()

    # Remove exact duplicate records.
    df = df.drop_duplicates().copy()

    if df.empty:
        raise ValueError(
            "No valid energy records found in energy_data.csv."
        )

    # Normalize dates to the first day of each month.
    df["month"] = (
        df["month"].dt.to_period("M").dt.to_timestamp()
    )

    # Calculate illustrative emissions.
    df["emissions_kg"] = (
        df["electricity_kwh"] * DEMO_EMISSION_FACTOR
    )

    # Save a summary for diagnostics and future reporting.
    df.attrs["data_quality"] = {
        "original_rows": original_rows,
        "valid_rows": len(df),
        "removed_rows": original_rows - len(df),
        "duplicate_rows": duplicate_rows,
        "invalid_months": invalid_months,
        "invalid_energy": invalid_energy,
        "missing_facilities": missing_facilities,
        "negative_energy": negative_energy,
    }


    # Normalize all dates to the first day of each month.
    df["month"] = (
        df["month"].dt.to_period("M").dt.to_timestamp()
    )

    df["emissions_kg"] = (
        df["electricity_kwh"] * DEMO_EMISSION_FACTOR
    )

    return df


# --------------------------------------------------
# Dashboard analytics and filters
# --------------------------------------------------

def get_dashboard_data(
    selected_facility="All",
    start_date="",
    end_date="",
):
    """Calculate dashboard metrics using selected filters."""

    
    # Load the complete dataset first.
    all_data = load_energy_data()

    # Preserve data-quality information before filtering.
    data_quality = all_data.attrs.get(
        "data_quality",
        {
            "original_rows": len(all_data),
            "valid_rows": len(all_data),
            "removed_rows": 0,
            "duplicate_rows": 0,
            "invalid_months": 0,
            "invalid_energy": 0,
            "missing_facilities": 0,
            "negative_energy": 0,
        },
    ).copy()

    # Keep the full facility list available in the filter.
    facility_options = sorted(
        all_data["facility"].unique().tolist()
    )


    min_date = all_data["month"].min().strftime("%Y-%m-%d")
    max_date = all_data["month"].max().strftime("%Y-%m-%d")

    # Validate selected facility.
    if selected_facility not in ["All"] + facility_options:
        selected_facility = "All"

    # Validate date inputs.
    parsed_start = pd.to_datetime(
        start_date, errors="coerce"
    ) if start_date else pd.NaT

    parsed_end = pd.to_datetime(
        end_date, errors="coerce"
    ) if end_date else pd.NaT

    if pd.isna(parsed_start):
        start_date = ""
        parsed_start = pd.NaT

    if pd.isna(parsed_end):
        end_date = ""
        parsed_end = pd.NaT

    # If dates are reversed, swap them.
    if (
        pd.notna(parsed_start)
        and pd.notna(parsed_end)
        and parsed_start > parsed_end
    ):
        parsed_start, parsed_end = parsed_end, parsed_start
        start_date = parsed_start.strftime("%Y-%m-%d")
        end_date = parsed_end.strftime("%Y-%m-%d")

    # Apply filters to a copy of the dataset.
    df = all_data.copy()

    if selected_facility != "All":
        df = df[
            df["facility"] == selected_facility
        ]

    if pd.notna(parsed_start):
        df = df[df["month"] >= parsed_start]

    if pd.notna(parsed_end):
        df = df[df["month"] <= parsed_end]

    # --------------------------------------------------
    # Key performance indicators
    # --------------------------------------------------


    # Key performance indicators
    total_energy = float(df["electricity_kwh"].sum())
    total_emissions = float(df["emissions_kg"].sum())
    facility_count = int(df["facility"].nunique())

    # Average monthly consumption across months with records
    monthly_totals = (
        df.groupby("month")["electricity_kwh"].sum()
    )

    average_monthly_consumption = (
        float(monthly_totals.mean())
        if not monthly_totals.empty
        else 0.0
    )

    # Estimated emissions per kWh
    emissions_intensity = (
        total_emissions / total_energy
        if total_energy > 0
        else 0.0
    )
    
    # Automated sustainability insights
    insights = []

    if not df.empty:
        # Find the facility with the highest total energy consumption
        facility_totals = (
            df.groupby("facility")["electricity_kwh"]
            .sum()
            .sort_values(ascending=False)
        )

        if not facility_totals.empty:
            top_facility = facility_totals.index[0]
            top_energy = float(facility_totals.iloc[0])

            insights.append({
                "title": "Highest Energy Consumer",
                "message": (
                    f"{top_facility} consumed "
                    f"{top_energy:,.0f} kWh in the selected period."
                ),
                "type": "warning",
            })

        # Compare consumption across recorded months
        monthly_totals = (
            df.groupby("month")["electricity_kwh"].sum().sort_index()
        )

        if len(monthly_totals) >= 2:
            previous_month = float(monthly_totals.iloc[-2])
            latest_month = float(monthly_totals.iloc[-1])

            if previous_month > 0:
                change_pct = (
                    (latest_month - previous_month)
                    / previous_month
                ) * 100

                if change_pct > 10:
                    insights.append({
                        "title": "Consumption Increased",
                        "message": (
                            f"Energy use increased by {change_pct:.1f}% "
                            "between the last two recorded months."
                        ),
                        "type": "warning",
                    })
                elif change_pct < -10:
                    insights.append({
                        "title": "Consumption Decreased",
                        "message": (
                            f"Energy use decreased by {abs(change_pct):.1f}% "
                            "between the last two recorded months."
                        ),
                        "type": "success",
                    })

    if not insights:
        insights.append({
            "title": "More Data Needed",
            "message": (
                "Add more monthly records to generate useful "
                "sustainability insights."
            ),
            "type": "info",
        })
    
    # Facility performance ranking
    facility_ranking = (
        df.groupby("facility")
        .agg(
            electricity_kwh=("electricity_kwh", "sum"),
            emissions_kg=("emissions_kg", "sum"),
        )
        .reset_index()
        .sort_values(
            by="electricity_kwh",
            ascending=False,
        )
        .to_dict(orient="records")
    )
    
    # Compare each facility's consumption with the facility average.
    if facility_ranking:
        average_facility_energy = sum(
            item["electricity_kwh"]
            for item in facility_ranking
        ) / len(facility_ranking)

        for item in facility_ranking:
            energy = item["electricity_kwh"]

            if energy < average_facility_energy * 0.90:
                item["performance_status"] = "Below average"
                item["performance_level"] = "low"
            elif energy > average_facility_energy * 1.10:
                item["performance_status"] = "Above average"
                item["performance_level"] = "high"
            else:
                item["performance_status"] = "Near average"
                item["performance_level"] = "average"
    else:
        average_facility_energy = 0

    
    # Monthly trend analysis
    
    
    # Monthly trend analysis
    monthly_totals = (
        df.groupby("month")["electricity_kwh"]
        .sum()
        .sort_index()
    )

    trend_direction = "insufficient data"
    trend_change_pct = None
    trend_message = (
        "Select a period containing at least two months "
        "with energy records to calculate a trend."
    )

    if len(monthly_totals) >= 2:
        previous_month = float(monthly_totals.iloc[-2])
        latest_month = float(monthly_totals.iloc[-1])

        previous_label = monthly_totals.index[-2].strftime("%b %Y")
        latest_label = monthly_totals.index[-1].strftime("%b %Y")

        if previous_month > 0:
            trend_change_pct = (
                (latest_month - previous_month)
                / previous_month
            ) * 100

            if trend_change_pct > 0:
                trend_direction = "increased"
            elif trend_change_pct < 0:
                trend_direction = "decreased"
            else:
                trend_direction = "stable"

            trend_message = (
                f"Consumption {trend_direction} by "
                f"{abs(trend_change_pct):.1f}% from "
                f"{previous_label} to {latest_label}."
            )
        else:
            trend_message = (
                f"Consumption in {previous_label} was zero. "
                "A percentage change cannot be calculated."
            )


    # Executive sustainability summary
    if df.empty:
        sustainability_summary = (
            "No records match the selected filters. "
            "Adjust the facility or date range to view findings."
        )
    else:
        sustainability_summary = (
            f"The selected data covers {facility_count} facilities, "
            f"with total electricity consumption of "
            f"{total_energy:,.0f} kWh and estimated emissions of "
            f"{total_emissions:,.0f} kg CO2e. "
            f"{trend_message}"
        )




    # --------------------------------------------------
    # Monthly energy chart
    # --------------------------------------------------

    monthly_data = (
        df.groupby("month", as_index=False)["electricity_kwh"]
        .sum()
        .sort_values("month")
    )

    trend_fig = px.line(
        monthly_data,
        x="month",
        y="electricity_kwh",
        markers=True,
        labels={
            "month": "Month",
            "electricity_kwh": "Electricity (kWh)",
        },
    )

    trend_fig.update_traces(
        line=dict(
            color="#a3e635",
            width=3,
            shape="spline",
        ),
        marker=dict(
            color="#a3e635",
            size=7,
            line=dict(color="#17251a", width=2),
        ),
        fill="tozeroy",
        fillcolor="rgba(163, 230, 53, 0.07)",
        hovertemplate=(
            "<b>%{x|%b %Y}</b><br>"
            "Electricity: %{y:,.0f} kWh"
            "<extra></extra>"
        ),
    )
    
    # --------------------------------------------------
    # Monthly emissions chart with demo target
    # --------------------------------------------------

    emissions_data = (
        df.groupby("month", as_index=False)["emissions_kg"]
        .sum()
        .sort_values("month")
    )

    emissions_fig = px.line(
        emissions_data,
        x="month",
        y="emissions_kg",
        markers=True,
        labels={
            "month": "Month",
            "emissions_kg": "Estimated emissions (kg CO₂e)",
        },
    )

    emissions_fig.update_traces(
        line=dict(
            color="#56d6ad",
            width=3,
            shape="spline",
        ),
        marker=dict(
            color="#56d6ad",
            size=7,
            line=dict(color="#17251a", width=2),
        ),
        hovertemplate=(
            "<b>%{x|%b %Y}</b><br>"
            "Estimated emissions: %{y:,.0f} kg CO₂e"
            "<extra></extra>"
        ),
        name="Estimated emissions",
    )

    # Illustrative target: 10% below the first visible month.
    if not emissions_data.empty:
        baseline_emissions = float(
            emissions_data.iloc[0]["emissions_kg"]
        )
        emissions_target = baseline_emissions * 0.90

        emissions_fig.add_hline(
            y=emissions_target,
            line_dash="dash",
            line_color="#fbbf24",
            line_width=2,
            annotation_text="Demo target: 10% below baseline",
            annotation_position="top left",
            annotation_font_color="#fbbf24",
        )
    else:
        emissions_target = 0.0
    
    # --------------------------------------------------
    # Emissions target progress
    # --------------------------------------------------

    if not emissions_data.empty:
        latest_emissions = float(
            emissions_data.iloc[-1]["emissions_kg"]
        )

        if latest_emissions <= emissions_target:
            emissions_target_status = "Target achieved"
        else:
            emissions_target_status = "Target not yet achieved"

        if baseline_emissions > 0:
            emissions_reduction_pct = (
                (baseline_emissions - latest_emissions)
                / baseline_emissions
            ) * 100
        else:
            emissions_reduction_pct = 0.0
    else:
        latest_emissions = 0.0
        emissions_target_status = "No data"
        emissions_reduction_pct = 0.0



    # --------------------------------------------------
    # Facility comparison chart and table
    # --------------------------------------------------

    facility_data = (
        df.groupby("facility", as_index=False)
        .agg(
            electricity_kwh=("electricity_kwh", "sum"),
            emissions_kg=("emissions_kg", "sum"),
        )
        .sort_values("electricity_kwh", ascending=False)
    )

    facility_fig = px.bar(
        facility_data,
        x="facility",
        y="electricity_kwh",
        color="facility",
        labels={
            "facility": "Facility",
            "electricity_kwh": "Electricity (kWh)",
        },
        color_discrete_sequence=[
            "#a3e635",
            "#56d6ad",
            "#7cbb8a",
            "#82aaff",
            "#c4b5fd",
        ],
    )

    facility_fig.update_traces(
        marker=dict(line=dict(width=0)),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Electricity: %{y:,.0f} kWh"
            "<extra></extra>"
        ),
    )

    # --------------------------------------------------
    # Shared chart styling
    # --------------------------------------------------

    for fig in (trend_fig, facility_fig, emissions_fig):
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Inter, Arial, sans-serif",
                color="#dce7dd",
                size=12,
            ),
            margin=dict(l=20, r=20, t=35, b=25),
            showlegend=False,
            hoverlabel=dict(
                bgcolor="#17251a",
                bordercolor="#36533c",
                font=dict(color="#f0fdf4"),
            ),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            linecolor="rgba(180, 200, 180, 0.15)",
        )

        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(180, 200, 180, 0.10)",
            zeroline=False,
            linecolor="rgba(180, 200, 180, 0.15)",
            rangemode="tozero",
        )

    # --------------------------------------------------
    # Convert charts to HTML
    # --------------------------------------------------

    monthly_chart = trend_fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={
            "responsive": True,
            "displayModeBar": False,
        },
    )

    facility_chart = facility_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={
            "responsive": True,
            "displayModeBar": False,
        },
    )

    # --------------------------------------------------
    # Facility summary table
    # --------------------------------------------------

    
    # Build facility data and attach performance indicators.
    performance_lookup = {
        item["facility"]: item
        for item in facility_ranking
    }

    facilities = []

    for _, row in facility_data.iterrows():
        facility_name = str(row["facility"])
        performance = performance_lookup.get(facility_name, {})

        facilities.append({
            "facility": facility_name,
            "electricity_kwh": round(
                float(row["electricity_kwh"]), 2
            ),
            "emissions_kg": round(
                float(row["emissions_kg"]), 2
            ),
            "performance_status": performance.get(
                "performance_status", "N/A"
            ),
            "performance_level": performance.get(
                "performance_level", "average"
            ),
        })

    
    return {
        "total_energy": round(total_energy, 2),
        "total_emissions": round(total_emissions, 2),
        "facility_count": facility_count,
        "insights": insights,
        "trend_direction": trend_direction,
        "trend_change_pct": trend_change_pct,
        "trend_message": trend_message,
        "sustainability_summary": sustainability_summary,
        
        # Data quality report
        "data_quality": data_quality,
        "records_analyzed": len(df),
        "data_quality_status": (
            "Clean"
            if data_quality.get("removed_rows", 0) == 0
            and data_quality.get("duplicate_rows", 0) == 0
            and data_quality.get("invalid_months", 0) == 0
            and data_quality.get("invalid_energy", 0) == 0
            and data_quality.get("missing_facilities", 0) == 0
            and data_quality.get("negative_energy", 0) == 0
            else "Review recommended"
        ),


        # New analytics metrics
        "average_monthly_consumption": round(
            average_monthly_consumption, 2
        ),
        "emissions_intensity": round(
            emissions_intensity, 4
        ),

        
        # Charts and facility table
        "monthly_chart": monthly_chart,
        "facility_chart": facility_chart,
        "emissions_chart": emissions_fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={"responsive": True},
        ),
        "emissions_target": round(emissions_target, 2),
        "latest_emissions": round(latest_emissions, 2),
        "emissions_target_status": emissions_target_status,
        "emissions_reduction_pct": round(
            emissions_reduction_pct, 2
        ),

        "facilities": facilities,
        "facility_ranking": facility_ranking,


        # Filter controls
        "facility_options": facility_options,
        "selected_facility": selected_facility,
        "start_date": start_date,
        "end_date": end_date,
        "min_date": min_date,
        "max_date": max_date,
    }

