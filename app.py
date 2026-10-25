
from flask import Flask, render_template, request, Response
from services.analytics import get_dashboard_data

app = Flask(__name__)


@app.route("/")
def dashboard():
    selected_facility = request.args.get("facility", "All")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    data = get_dashboard_data(
        selected_facility=selected_facility,
        start_date=start_date,
        end_date=end_date,
    )

    return render_template("index.html", **data)

@app.route("/export")
def export_csv():
    import csv
    import io
    import pandas as pd

    df = pd.read_csv("data/energy_data.csv")

    df.columns = df.columns.str.strip()

    date_column = "date" if "date" in df.columns else "month"

    df[date_column] = pd.to_datetime(
        df[date_column],
        errors="coerce"
    )
    df = df.dropna(subset=[date_column])

    selected_facility = request.args.get("facility", "All")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    if selected_facility != "All":
        df = df[df["facility"] == selected_facility]

    if start_date:
        df = df[df[date_column] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df[date_column] <= pd.to_datetime(end_date)]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(df.columns.tolist())
    writer.writerows(df.itertuples(index=False, name=None))

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=greenpulse_sustainability_report.csv"
        },
    )



if __name__ == "__main__":
    app.run(debug=True)
