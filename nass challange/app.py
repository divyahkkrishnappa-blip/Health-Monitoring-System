import os
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, make_response, render_template, request

from database import get_db, initialize_database, utc_now


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
ASTRONAUT_ID = 1
DEFAULT_DEMO_THRESHOLDS = {
    "heart_rate": (45, 120),
    "temperature": (35.0, 38.5),
    "systolic": (80, 180),
    "diastolic": (45, 120),
    "oxygen": (90, 100),
    "sleep": (0, 16),
}
def _load_demo_thresholds():
    thresholds = {}
    for metric, (default_low, default_high) in DEFAULT_DEMO_THRESHOLDS.items():
        prefix = f"ASTROHEALTH_DEMO_{metric.upper()}"
        try:
            low = float(os.environ.get(f"{prefix}_MIN", default_low))
            high = float(os.environ.get(f"{prefix}_MAX", default_high))
        except ValueError as error:
            raise ValueError(f"{prefix}_MIN and {prefix}_MAX must be numeric.") from error
        if low >= high:
            raise ValueError(f"{prefix}_MIN must be less than {prefix}_MAX.")
        thresholds[metric] = (low, high)
    return thresholds


DEMO_THRESHOLDS = _load_demo_thresholds()
METRICS = {
    "heart_rate": ("Heart rate", "bpm"),
    "temperature": ("Body temperature", "°C"),
    "systolic": ("Systolic pressure", "mmHg"),
    "diastolic": ("Diastolic pressure", "mmHg"),
    "oxygen": ("Blood oxygen", "%"),
    "sleep": ("Sleep duration", "h"),
}
INPUT_RANGES = {
    "heart_rate": (0, 300),
    "temperature": (0, 60),
    "systolic": (1, 400),
    "diastolic": (1, 300),
    "oxygen": (0, 100),
    "sleep": (0, 24),
}


@app.before_request
def ensure_database():
    initialize_database()


@app.get("/")
def home():
    return render_template("index.html", title="NASA AstroHealth")


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html", title="Mission dashboard")


@app.get("/monitoring")
def monitoring():
    return render_template("monitoring.html", title="Health monitoring")


@app.get("/camera")
def camera():
    return render_template("camera.html", title="Camera module")


@app.get("/body")
def body():
    return render_template("body.html", title="Human body explorer")


@app.get("/insights")
def insights():
    return render_template("insights.html", title="Health insights")


@app.get("/alerts")
def alerts():
    return render_template("alerts.html", title="Alerts and mission control")


@app.get("/reports")
def reports():
    return render_template("reports.html", title="Health reports")


@app.get("/education")
def education():
    return render_template("education.html", title="Mission health education")


def _json_measurement(row):
    item = dict(row)
    item["value"] = float(item["value"])
    return item


def _create_alert(db, metric, value, unit, low, high):
    if value < low or value > high:
        db.execute(
            """INSERT INTO alerts
               (astronaut_id, severity, title, message, status, created_at)
               VALUES (?, ?, ?, ?, 'Open', ?)""",
            (
                ASTRONAUT_ID,
                "Review",
                f"{METRICS[metric][0]} outside demo range",
                f"Recorded {value:g} {unit}. This configurable demonstration rule is not a clinical threshold. Follow approved mission medical protocols.",
                utc_now(),
            ),
        )


@app.get("/api/profile")
def profile():
    with get_db() as db:
        astronaut = db.execute("SELECT * FROM astronauts WHERE id = ?", (ASTRONAUT_ID,)).fetchone()
    if astronaut is None:
        return jsonify(error="Astronaut profile is unavailable."), 404
    return jsonify(dict(astronaut))


@app.get("/api/measurements")
@app.get("/api/health-history")
def get_measurements():
    metric = request.args.get("metric")
    limit = request.args.get("limit", default=100, type=int)
    if limit is None or limit < 1 or limit > 500:
        return jsonify(error="limit must be between 1 and 500."), 400
    if metric and metric not in METRICS:
        return jsonify(error="Unknown measurement metric."), 400
    with get_db() as db:
        if metric:
            rows = db.execute(
                """SELECT * FROM measurements WHERE astronaut_id = ? AND metric = ?
                   ORDER BY recorded_at DESC LIMIT ?""",
                (ASTRONAUT_ID, metric, limit),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT * FROM measurements WHERE astronaut_id = ?
                   ORDER BY recorded_at DESC LIMIT ?""",
                (ASTRONAUT_ID, limit),
            ).fetchall()
    return jsonify(measurements=[_json_measurement(row) for row in reversed(rows)])


@app.post("/api/measurements")
def create_measurement():
    payload = request.get_json(silent=True) or {}
    metric = payload.get("metric")
    source = payload.get("source", "User entered")
    if metric not in METRICS:
        return jsonify(error="Choose a supported measurement metric."), 400
    if source not in ("User entered", "Synthetic demo"):
        return jsonify(error="Measurement source must be User entered or Synthetic demo."), 400
    try:
        value = float(payload.get("value"))
    except (TypeError, ValueError):
        return jsonify(error="Enter a numeric measurement."), 400
    low_input, high_input = INPUT_RANGES[metric]
    if not (low_input <= value <= high_input):
        return jsonify(error=f"{METRICS[metric][0]} entry must be between {low_input:g} and {high_input:g} {METRICS[metric][1]} for this prototype."), 400
    unit = METRICS[metric][1]
    with get_db() as db:
        db.execute(
            """INSERT INTO measurements
               (astronaut_id, metric, value, unit, source, recorded_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ASTRONAUT_ID, metric, value, unit, source, utc_now(), str(payload.get("notes", ""))[:250]),
        )
        low, high = DEMO_THRESHOLDS[metric]
        _create_alert(db, metric, value, unit, low, high)
    return jsonify(message="Measurement saved.", measurement={
        "metric": metric, "value": value, "unit": unit, "source": source, "recorded_at": utc_now()
    }), 201


@app.post("/api/simulate")
def simulate_measurements():
    now = utc_now()
    synthetic = {
        "heart_rate": (random.randint(62, 78), "bpm"),
        "temperature": (round(random.uniform(36.4, 37.1), 1), "°C"),
        "systolic": (random.randint(108, 124), "mmHg"),
        "diastolic": (random.randint(68, 82), "mmHg"),
        "oxygen": (random.randint(96, 99), "%"),
    }
    with get_db() as db:
        for metric, (value, unit) in synthetic.items():
            db.execute(
                """INSERT INTO measurements
                   (astronaut_id, metric, value, unit, source, recorded_at)
                   VALUES (?, ?, ?, ?, 'Synthetic demo', ?)""",
                (ASTRONAUT_ID, metric, value, unit, now),
            )
            low, high = DEMO_THRESHOLDS[metric]
            _create_alert(db, metric, value, unit, low, high)
    return jsonify(message="Synthetic demo readings recorded.", source="Synthetic demo")


@app.post("/api/check-ins")
def check_in():
    payload = request.get_json(silent=True) or {}
    try:
        mood, stress = int(payload.get("mood")), int(payload.get("stress"))
        sleep_hours = float(payload.get("sleep_hours"))
    except (TypeError, ValueError):
        return jsonify(error="Provide mood, stress (1–5), and sleep hours as numbers."), 400
    if not (1 <= mood <= 5 and 1 <= stress <= 5 and 0 <= sleep_hours <= 24):
        return jsonify(error="Mood and stress must be 1–5; sleep must be 0–24 hours."), 400
    with get_db() as db:
        db.execute(
            """INSERT INTO check_ins
               (astronaut_id, mood, stress, sleep_hours, notes, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ASTRONAUT_ID, mood, stress, sleep_hours, str(payload.get("notes", ""))[:250], utc_now()),
        )
        db.execute(
            """INSERT INTO measurements
               (astronaut_id, metric, value, unit, source, recorded_at)
               VALUES (?, 'sleep', ?, 'h', 'User entered', ?)""",
            (ASTRONAUT_ID, sleep_hours, utc_now()),
        )
    return jsonify(message="Check-in saved."), 201


@app.get("/api/summary")
@app.get("/api/health-summary")
def summary():
    with get_db() as db:
        astronaut = db.execute("SELECT * FROM astronauts WHERE id = ?", (ASTRONAUT_ID,)).fetchone()
        latest = db.execute(
            """SELECT m.* FROM measurements m
               JOIN (SELECT metric, MAX(recorded_at) AS latest FROM measurements
                     WHERE astronaut_id = ? GROUP BY metric) x
               ON x.metric = m.metric AND x.latest = m.recorded_at
               WHERE m.astronaut_id = ?""",
            (ASTRONAUT_ID, ASTRONAUT_ID),
        ).fetchall()
        checkin = db.execute(
            "SELECT * FROM check_ins WHERE astronaut_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (ASTRONAUT_ID,),
        ).fetchone()
        open_alerts = db.execute(
            "SELECT COUNT(*) FROM alerts WHERE astronaut_id = ? AND status = 'Open'",
            (ASTRONAUT_ID,),
        ).fetchone()[0]
    latest_by_metric = {row["metric"]: _json_measurement(row) for row in latest}
    return jsonify(
        astronaut=dict(astronaut) if astronaut else None,
        measurements=latest_by_metric,
        check_in=dict(checkin) if checkin else None,
        open_alerts=open_alerts,
        data_notice="Demonstration data only. Not for diagnosis or treatment.",
    )


@app.get("/api/alerts")
def get_alerts():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM alerts WHERE astronaut_id = ? ORDER BY created_at DESC LIMIT 100",
            (ASTRONAUT_ID,),
        ).fetchall()
    return jsonify(alerts=[dict(row) for row in rows])


@app.post("/api/alerts/<int:alert_id>/acknowledge")
def acknowledge_alert(alert_id):
    with get_db() as db:
        cursor = db.execute(
            """UPDATE alerts SET status = 'Acknowledged', acknowledged_at = ?
               WHERE id = ? AND astronaut_id = ? AND status = 'Open'""",
            (utc_now(), alert_id, ASTRONAUT_ID),
        )
    if cursor.rowcount == 0:
        return jsonify(error="Alert not found or already acknowledged."), 404
    return jsonify(message="Alert acknowledged.")


@app.post("/api/alerts/<int:alert_id>/escalate")
def escalate_alert(alert_id):
    with get_db() as db:
        cursor = db.execute(
            """UPDATE alerts SET severity = 'Escalated',
               message = message || ' Simulated escalation: acknowledgement is still pending; follow approved mission medical protocols.',
               created_at = ?
               WHERE id = ? AND astronaut_id = ? AND status = 'Open' AND severity != 'Escalated'""",
            (utc_now(), alert_id, ASTRONAUT_ID),
        )
    if cursor.rowcount == 0:
        return jsonify(error="Only an open, not-yet-escalated alert can be escalated."), 409
    return jsonify(message="Simulated escalation recorded. No real mission communication was sent.")


@app.get("/api/mission-control")
def mission_control():
    with get_db() as db:
        astronaut = db.execute("SELECT * FROM astronauts WHERE id = ?", (ASTRONAUT_ID,)).fetchone()
        alerts_list = db.execute(
            """SELECT * FROM alerts WHERE astronaut_id = ?
               ORDER BY created_at DESC LIMIT 20""",
            (ASTRONAUT_ID,),
        ).fetchall()
    return jsonify(
        astronaut=dict(astronaut) if astronaut else None,
        alerts=[dict(row) for row in alerts_list],
        communication={"mode": "Simulated", "round_trip_seconds": 18 * 60, "status": "Nominal"},
        note="Communication delay is a demonstration scenario, not a live link.",
    )


def _insight_summary():
    messages = []
    with get_db() as db:
        rows = db.execute(
            """SELECT metric, value, unit, recorded_at FROM measurements
               WHERE astronaut_id = ? ORDER BY recorded_at DESC""",
            (ASTRONAUT_ID,),
        ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["metric"]].append(row)
    for metric, readings in grouped.items():
        if len(readings) < 2:
            continue
        recent = [row["value"] for row in readings[:3]]
        earlier = [row["value"] for row in readings[3:6]]
        if earlier and abs(sum(recent) / len(recent) - sum(earlier) / len(earlier)) > max(abs(sum(earlier) / len(earlier)) * 0.1, 0.5):
            messages.append({
                "metric": metric,
                "title": f"Recent {METRICS[metric][0].lower()} trend changed",
                "detail": "The average of the latest readings differs from the preceding readings. Review the context and confirm with approved monitoring.",
                "kind": "trend",
            })
    if not messages:
        messages.append({
            "metric": None,
            "title": "No notable trend detected in available demo readings",
            "detail": "Limited demonstration data cannot establish health status. Continue routine monitoring and consult approved mission protocols for concerns.",
            "kind": "info",
        })
    return messages


@app.get("/api/insights")
def get_insights():
    return jsonify(
        insights=_insight_summary(),
        method="Transparent prototype rules comparing recent values with preceding values.",
        uncertainty="Not a medical diagnosis or validated prediction. Synthetic and user-entered data may be incomplete.",
    )


@app.get("/api/reports")
def report_data():
    now = datetime.now(timezone.utc)
    periods = {
        "daily": now - timedelta(days=1),
        "weekly": now - timedelta(days=7),
    }
    summaries = {}
    with get_db() as db:
        for key, start in periods.items():
            rows = db.execute(
                """SELECT metric, COUNT(*) AS count, AVG(value) AS average,
                          MIN(value) AS minimum, MAX(value) AS maximum
                   FROM measurements
                   WHERE astronaut_id = ? AND recorded_at >= ?
                   GROUP BY metric ORDER BY metric""",
                (ASTRONAUT_ID, start.isoformat()),
            ).fetchall()
            summaries[key] = {
                "start_at": start.isoformat(),
                "measurement_count": sum(row["count"] for row in rows),
                "metrics": {
                    row["metric"]: {
                        "count": row["count"],
                        "average": round(row["average"], 2),
                        "minimum": row["minimum"],
                        "maximum": row["maximum"],
                        "unit": METRICS[row["metric"]][1],
                    }
                    for row in rows
                },
            }
    with get_db() as db:
        alerts_list = db.execute(
            """SELECT * FROM alerts WHERE astronaut_id = ?
               ORDER BY created_at DESC LIMIT 50""",
            (ASTRONAUT_ID,),
        ).fetchall()
    return jsonify(
        generated_at=now.isoformat(),
        summaries=summaries,
        alerts=[dict(row) for row in alerts_list],
        notice="Descriptive statistics over available demo and user-entered records only; not a clinical summary.",
    )


def _pdf_escape(text):
    return str(text).encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_report_pdf():
    with get_db() as db:
        astronaut = db.execute("SELECT * FROM astronauts WHERE id = ?", (ASTRONAUT_ID,)).fetchone()
        measurements = db.execute(
            """SELECT metric, value, unit, source, recorded_at FROM measurements
               WHERE astronaut_id = ? ORDER BY recorded_at DESC LIMIT 30""",
            (ASTRONAUT_ID,),
        ).fetchall()
        alerts_rows = db.execute(
            "SELECT severity, title, status, created_at FROM alerts WHERE astronaut_id = ? ORDER BY created_at DESC LIMIT 10",
            (ASTRONAUT_ID,),
        ).fetchall()
        since_24h = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        daily_count = db.execute(
            "SELECT COUNT(*) FROM measurements WHERE astronaut_id = ? AND recorded_at >= ?",
            (ASTRONAUT_ID, since_24h),
        ).fetchone()[0]
        weekly_count = db.execute(
            "SELECT COUNT(*) FROM measurements WHERE astronaut_id = ? AND recorded_at >= ?",
            (ASTRONAUT_ID, since_7d),
        ).fetchone()[0]
    lines = [
        "NASA AstroHealth | Demonstration Health Summary",
        f"Astronaut: {astronaut['name']} ({astronaut['call_sign']})",
        f"Mission: {astronaut['mission']} | Mission day {astronaut['mission_day']}",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "NOTICE: Synthetic/user-entered demonstration data. Not for diagnosis or treatment.",
        f"Daily summary: {daily_count} measurement(s) recorded in the last 24 hours.",
        f"Weekly summary: {weekly_count} measurement(s) recorded in the last 7 days.",
        "",
        "Recent measurements:",
    ]
    for item in measurements:
        stamp = str(item["recorded_at"])[:16].replace("T", " ")
        lines.append(f"{item['metric']}: {item['value']:g} {item['unit']} | {item['source']} | {stamp}")
    lines.extend(["", "Recent alerts:"])
    for item in alerts_rows:
        lines.append(f"{item['severity']} | {item['title']} | {item['status']} | {str(item['created_at'])[:16]}")
    lines.extend(["", "For concerns, follow approved mission medical protocols and contact mission medical support."])
    lines = [line[:105] for line in lines]
    content = ["BT", "/F1 10 Tf", "50 750 Td", "14 TL"]
    for line in lines:
        content.append(f"({_pdf_escape(line)}) Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_position = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode())
    return bytes(output)


@app.get("/api/reports.pdf")
def download_report():
    response = make_response(make_report_pdf())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = 'attachment; filename="astrohealth-report.pdf"'
    return response


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.exception("Database operation failed: %s", error)
    return jsonify(error="The health database could not complete this request. Please try again."), 500


@app.errorhandler(500)
def internal_error(_error):
    return jsonify(error="The application encountered an unexpected error. Please try again."), 500


if __name__ == "__main__":
    initialize_database()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
