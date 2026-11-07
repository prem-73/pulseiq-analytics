# PulseIQ - Workforce Analytics Platform

## Project Overview

PulseIQ is a workforce analytics platform developed using Python, Pandas, DuckDB and Streamlit. It processes workforce data, performs data quality validation, builds analytical data models, and provides dashboards for workforce and team productivity analysis.

This repository consolidates Phase 1, Phase 2 and Phase 3 of the project.

**Note:** Some dashboards use synthetic sample data. Their results do not represent actual company performance.

## Project Phases

### Phase 1 - Data Engineering and Analytics Foundation
- ETL pipeline using Python and Pandas.
- Data cleaning and transformation.
- Star-schema data warehouse using DuckDB.
- Data quality validation using Pandera and SQL checks.
- Governed metric layer with 28 metrics.

### Phase 2 - Workforce and Team Analytics
- Attendance and leave analytics.
- Attrition analytics and risk prediction.
- Team productivity dashboard.
- Sprint velocity, cycle time and on-time delivery.
- Blocked and reopened work analysis.

### Phase 3 - Extended Analytics
- Tasks 9-15 dashboards and analysis.
- Department and payroll analytics.
- Finance and operational analysis.
- Forecasting and anomaly analysis.
- Executive scorecard.

## Project Structure

```text
pulseiq/
â”œâ”€â”€ README.md
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ app.py
â”œâ”€â”€ phase-1/
â”œâ”€â”€ phase-2/
â”œâ”€â”€ phase-3/
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/
â”‚   â”œâ”€â”€ external/
â”‚   â””â”€â”€ task8/
â”œâ”€â”€ models/
â”œâ”€â”€ outputs/
â””â”€â”€ pages/
```

## Technologies Used

- Python
- Pandas
- DuckDB
- Streamlit
- Pandera
- Scikit-learn
- Joblib
- SQL
- Git and GitHub

## Installation

Clone or open the existing project repository.

Activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Running the Project

Run the main application:

```powershell
python -m streamlit run app.py
```

Run the Phase 2 dashboards:

```powershell
python -m streamlit run phase-2\task6_dashboard.py
python -m streamlit run phase-2\task7_dashboard.py
python -m streamlit run phase-2\task8_dashboard.py
```

Run the Phase 3 dashboards individually:

```powershell
python -m streamlit run phase-3\task9_dashboard.py
```

Replace the dashboard filename to run another Phase 3 dashboard.

## Phase 1 Verification

```powershell
python phase-1\dq_checks.py
python phase-1\build_metrics.py
python phase-1\test_dq_checks.py
```

## Data and Privacy

- Sample data is used for demonstration and testing.
- Do not upload confidential employee information, passwords, API keys or `.env` files.
- Local DuckDB database files and virtual environments are excluded from Git.

## Future Work

Phase 4 will be added to this same repository after its official release.

## Repository

This repository contains the consolidated PulseIQ project for review.