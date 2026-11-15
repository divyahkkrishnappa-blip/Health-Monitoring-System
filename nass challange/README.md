# NASA AstroHealth

NASA AstroHealth is an independent, local-first demonstration project for the NASA Space Apps Challenge 2026. It explores how a crew-facing interface might organize health check-ins, trends, educational material, and simulated mission alerts.

> **Scope and safety:** This is not a NASA product, medical device, clinical tool, or certified spaceflight system. Sample data is synthetic; readings entered in the interface are user-entered. Demonstration thresholds are configurable prototype rules, not astronaut-specific medical thresholds. This app does not diagnose, predict health events, or give treatment instructions.

## What is included

- Responsive landing page and mission-control dashboard.
- Health history charts, manual measurements, and mood/stress/sleep check-ins.
- SQLite persistence and clearly labeled measurement sources.
- Synthetic sensor-reading action for demos.
- Simulated alerts, acknowledgement, and a manual escalation demonstration.
- Rule-based trend summaries that explain their limitations.
- Optional browser camera preview. No video is uploaded or analyzed.
- Interactive educational body-system diagram.
- Health-record summary PDF download.
- NASA Human Research Program source links and five-hazard overview.

## Run on Windows 11

1. Install Python 3.10 or later from [python.org](https://www.python.org/downloads/). During installation, enable the option to add Python to PATH. The Python launcher (`py`) is used by the run script.
2. Extract/open this project folder.
3. Double-click **Run_Project.bat**. It creates a `.venv` virtual environment if needed, installs Flask, and starts the server.
4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).
5. To stop the server, focus its console window and press **Ctrl+C**.

The first launch needs an internet connection to install Flask. Chart.js, Lucide icons, and the optional web fonts are loaded from CDNs; without internet access, the app still serves its pages and APIs, but chart/icon/font enhancements may not load.

### Run manually

In PowerShell, from the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open `http://127.0.0.1:5000`.

## Project map

| File/folder | Purpose |
| --- | --- |
| `app.py` | Flask page routes, JSON APIs, demo rules, alert handling, and PDF report generation. |
| `database.py` | SQLite connection lifecycle, schema creation, and initial synthetic astronaut/readings. |
| `templates/base.html` | Shared application shell, sidebar, external libraries, and navigation. |
| `templates/index.html` | Landing page and five-hazard overview. |
| `templates/dashboard.html` | Astronaut snapshot, metrics, chart, and recent alerts. |
| `templates/monitoring.html` | Measurement history, manual entry, and wellness check-in. |
| `templates/camera.html` | Optional local camera preview and measurement limitations. |
| `templates/body.html` | Selectable body-system education diagram. |
| `templates/insights.html` | Rule-based trend explanation and uncertainty statements. |
| `templates/alerts.html` | Simulated mission communication, alert history, and actions. |
| `templates/reports.html` | Recent-record summary and PDF download. |
| `templates/education.html` | NASA-linked information about the five human spaceflight hazards. |
| `static/css/style.css` | Responsive space-themed interface and components. |
| `static/js/app.js` | API-backed page data, forms, alerts, and body explorer interactions. |
| `static/js/charts.js` | Chart.js history and dashboard charts. |
| `static/js/camera.js` | Browser camera permission, preview, and stop lifecycle. |
| `requirements.txt` | Python dependency list. |
| `Run_Project.bat` | Windows virtual environment setup and app launcher. |

## Demo data and persistence

On first run, `database.py` creates `astrohealth.db` in the project directory, creates the tables, and seeds one sample astronaut with synthetic readings. New measurements, check-ins, and alerts are stored locally in SQLite. The source label indicates whether a reading was synthetic or user-entered. The database is not encrypted; use demonstration data only.

To use a different database path, set the `ASTROHEALTH_DATABASE` environment variable before launching the app. The Flask server binds to `127.0.0.1` by default; `PORT` can change its local port.

Demonstration alert ranges can be adjusted with `ASTROHEALTH_DEMO_<METRIC>_MIN` and `ASTROHEALTH_DEMO_<METRIC>_MAX` environment variables (metric names: `HEART_RATE`, `TEMPERATURE`, `SYSTOLIC`, `DIASTOLIC`, `OXYGEN`, and `SLEEP`). For example, set `ASTROHEALTH_DEMO_HEART_RATE_MIN=50` and `ASTROHEALTH_DEMO_HEART_RATE_MAX=110` in the same terminal before starting the app. These are demo-only alert rules, not clinical or astronaut-specific thresholds. Invalid or reversed configuration stops startup with an error.

## API overview

- `GET /api/profile` — astronaut profile.
- `GET /api/measurements` and `GET /api/health-history` — stored measurement records; optional `metric` and `limit` query parameters.
- `POST /api/measurements` — save a user-entered measurement.
- `POST /api/simulate` — add a batch of synthetic demo readings.
- `POST /api/check-ins` — store self-reported mood, stress, and sleep.
- `GET /api/summary` and `GET /api/health-summary` — latest readings and open-alert count.
- `GET /api/insights` — transparent rule-based trend review.
- `GET /api/alerts` — alert history.
- `POST /api/alerts/<id>/acknowledge` — acknowledge an open alert.
- `POST /api/alerts/<id>/escalate` — record a simulated escalation; it does not send a real message.
- `GET /api/mission-control` — profile, alerts, and simulated link status.
- `GET /api/reports.pdf` — downloadable demonstration summary.

## Scientific references

The education page links to NASA's [Human Research Program hazards overview](https://www.nasa.gov/hrp/hazards/) and [Human Research Program](https://www.nasa.gov/hrp/). These links provide background; the project summaries are intentionally high-level and are not a substitute for official mission guidance.

The camera module only displays the browser's camera stream after explicit permission. It does not estimate pulse or measure blood pressure, temperature, glucose, oxygen saturation, or sleep. Trend rules are intentionally simple and unvalidated; they must never be treated as medical diagnoses or alerts requiring independent treatment.
