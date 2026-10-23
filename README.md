# PulseIQ — Day 1 ETL Pipeline

A runnable starter project for the Phase 1, Day 1 task. It loads sample HR CSV feeds into DuckDB, validates each column against `data_contracts.json`, stores accepted records in clean tables, sends invalid records to `quarantine`, and writes counts to `etl_summary`.

> The included CSV files are sample data. If your course/task folder contains official PulseIQ files, replace the sample CSVs with those files and update the contract to match the official `README` and `data_contracts` sheets.

## Project structure

```text
pulseiq/
├── data/
│   └── raw/
│       ├── employees.csv
│       ├── salaries.csv
│       ├── attendance.csv
│       ├── leave.csv
│       └── payroll.csv
├── docs/
│   └── contract_notes.md
├── data_contracts.json
├── load_to_duckdb.py
├── etl.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

- Python 3.11+
- PowerShell / terminal
- Optional: Git and a GitHub account

## Run on Windows PowerShell

Open a terminal inside this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python load_to_duckdb.py
python etl.py
```

Run `python etl.py` a second time to test re-runnability. The clean tables, quarantine table, and summary table are replaced each run, so repeated runs do not append duplicate rows.

## Tables created in `pulseiq.duckdb`

- `raw_employees`, `raw_salaries`, `raw_attendance`, `raw_leave`, `raw_payroll`: raw loaded input
- `employees`, `salaries`, `attendance`, `leave`, `payroll`: validated rows
- `quarantine`: invalid rows and rejection reasons
- `etl_summary`: per-feed input/pass/quarantine counts

## Inspect results with Python

You can use the DuckDB Python package:

```powershell
python -c "import duckdb; c=duckdb.connect('pulseiq.duckdb', read_only=True); print(c.sql('SELECT * FROM etl_summary').df()); print(c.sql('SELECT * FROM quarantine').df()); c.close()"
```

## Validation behavior

- Required values, types, numeric limits, allowed values, and selected uniqueness rules are checked.
- Leave end dates cannot be earlier than start dates.
- Payroll net pay must equal gross pay minus deductions (tolerance 0.01).
- Missing required columns stop the run because the feed cannot be validated.
- Unexpected columns generate a warning and quarantine the feed rows for review rather than silently ignoring the new field.
- Every row is either passed or quarantined; the pipeline asserts that `rows_in = rows_passed + rows_quarantined`.

## Git setup

Create a private repository named `pulseiq` on GitHub, then run these commands after configuring your Git identity and remote:

```powershell
git init
git add .
git commit -m "Set up PulseIQ ETL pipeline"
git branch -M main
git remote add origin YOUR_PRIVATE_GITHUB_REPOSITORY_URL
git push -u origin main
```

Do not commit passwords, tokens, `.venv`, or personal/confidential data.
