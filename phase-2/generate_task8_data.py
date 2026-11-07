import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

# Reproducible sample data
rng = np.random.default_rng(42)

OUTPUT = Path("data/task8")
OUTPUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------
# 1. Create 16 teams
# -----------------------------------
teams = pd.DataFrame({
    "team_id": range(1, 17),
    "team_name": [f"Team {chr(65+i)}" for i in range(16)],
    "team_size": rng.integers(5, 13, 16),
    "work_type": rng.choice(
        ["Development", "Testing", "Data", "Platform"],
        16
    )
})

# -----------------------------------
# 2. Create 38 sprints
# -----------------------------------
sprint_rows = []

for i in range(38):
    start = pd.Timestamp("2025-01-06") + pd.Timedelta(days=14*i)

    sprint_rows.append({
        "sprint_id": i + 1,
        "sprint_name": f"Sprint {i+1}",
        "start_date": start,
        "end_date": start + pd.Timedelta(days=13),
        "duration_days": 14
    })

sprints = pd.DataFrame(sprint_rows)

# -----------------------------------
# 3. Generate 28,868 tasks
# -----------------------------------
task_rows = []

statuses = ["Completed", "In Progress", "Blocked", "Cancelled"]
probabilities = [0.68, 0.16, 0.09, 0.07]

for task_id in range(1, 28869):

    team = teams.iloc[rng.integers(0, 16)]
    sprint = sprints.iloc[rng.integers(0, 38)]

    status = rng.choice(statuses, p=probabilities)

    created = sprint["start_date"] + pd.Timedelta(
        days=int(rng.integers(0, 10))
    )

    started = created + pd.Timedelta(
        days=int(rng.integers(0, 4))
    )

    story_points = int(rng.choice([1, 2, 3, 5, 8, 13]))

    cycle_days = int(rng.integers(1, 16))

    if status == "Completed":
        completed = started + pd.Timedelta(days=cycle_days)
    else:
        completed = pd.NaT

    due = started + pd.Timedelta(
        days=int(rng.integers(5, 13))
    )

    blocked_days = int(rng.choice([0, 0, 0, 1, 2, 3, 5, 8]))

    reopen_count = int(
        rng.choice([0, 0, 0, 0, 1, 1, 2])
    )

    task_rows.append({
        "task_id": task_id,
        "team_id": int(team["team_id"]),
        "sprint_id": int(sprint["sprint_id"]),
        "status": status,
        "story_points": story_points,
        "created_at": created,
        "started_at": started,
        "completed_at": completed,
        "due_date": due,
        "blocked_days": blocked_days,
        "reopen_count": reopen_count
    })

fact_task = pd.DataFrame(task_rows)

# -----------------------------------
# 4. Save CSV files
# -----------------------------------
teams.to_csv(OUTPUT / "dim_team.csv", index=False)
sprints.to_csv(OUTPUT / "dim_sprint.csv", index=False)
fact_task.to_csv(OUTPUT / "fact_task.csv", index=False)

# -----------------------------------
# 5. Create separate DuckDB database
# -----------------------------------
db = duckdb.connect("task8_sample.duckdb")

db.register("teams_df", teams)
db.register("sprints_df", sprints)
db.register("tasks_df", fact_task)

db.execute("""
    CREATE OR REPLACE TABLE dim_team AS
    SELECT * FROM teams_df
""")

db.execute("""
    CREATE OR REPLACE TABLE dim_sprint AS
    SELECT * FROM sprints_df
""")

db.execute("""
    CREATE OR REPLACE TABLE fact_task AS
    SELECT * FROM tasks_df
""")

# -----------------------------------
# 6. Create metric views
# -----------------------------------
db.execute("""
CREATE OR REPLACE VIEW metric_team_sprint AS
SELECT
    t.team_id,
    t.team_name,
    t.team_size,
    s.sprint_id,
    s.sprint_name,

    COUNT(*) AS total_tasks,

    SUM(CASE
        WHEN f.status = 'Completed' THEN 1
        ELSE 0
    END) AS completed_tasks,

    SUM(CASE
        WHEN f.status = 'Completed' THEN f.story_points
        ELSE 0
    END) AS velocity,

    ROUND(AVG(
        CASE
            WHEN f.status = 'Completed'
            THEN date_diff('day', f.started_at, f.completed_at)
        END
    ), 2) AS avg_cycle_time_days,

    ROUND(
        100.0 * SUM(CASE
            WHEN f.status = 'Completed'
             AND f.completed_at <= f.due_date
            THEN 1 ELSE 0
        END)
        / NULLIF(SUM(CASE
            WHEN f.status = 'Completed' THEN 1 ELSE 0
        END), 0),
        2
    ) AS on_time_rate_pct,

    SUM(CASE
        WHEN f.status = 'Blocked' THEN 1
        ELSE 0
    END) AS blocked_tasks,

    SUM(CASE
        WHEN f.reopen_count > 0 THEN 1
        ELSE 0
    END) AS reopened_tasks,

    SUM(CASE
        WHEN f.status = 'Cancelled' THEN 1
        ELSE 0
    END) AS cancelled_tasks

FROM fact_task f
JOIN dim_team t ON f.team_id = t.team_id
JOIN dim_sprint s ON f.sprint_id = s.sprint_id

GROUP BY
    t.team_id, t.team_name, t.team_size,
    s.sprint_id, s.sprint_name
""")

db.close()

print("\nTASK 8 SAMPLE DATA CREATED SUCCESSFULLY")
print("Tasks:", len(fact_task))
print("Teams:", len(teams))
print("Sprints:", len(sprints))
print("Database: task8_sample.duckdb")
print("CSV folder: data/task8/")

