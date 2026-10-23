from pathlib import Path
from datetime import date
import pandas as pd
import duckdb

ROOT = Path(__file__).resolve().parent
DB = ROOT / "pulseiq.duckdb"
HISTORY = ROOT / "data" / "employee_history.csv"

def read_clean(con, table):
    try:
        return con.execute(f'SELECT * FROM "{table}"').fetchdf()
    except Exception as exc:
        raise RuntimeError(f"Clean table {table!r} missing. Run load_to_duckdb.py and etl.py first.") from exc

def as_date(value, default=None, month_period=False):
    if pd.isna(value) or str(value).strip() == "":
        return default
    s = str(value)
    if month_period and len(s) == 7:
        s += "-01"
    return date.fromisoformat(s[:10])

def main():
    con = duckdb.connect(str(DB))
    try:
        employees = read_clean(con, "employees")
        salaries = read_clean(con, "salaries")
        attendance = read_clean(con, "attendance")
        leaves = read_clean(con, "leave")
        payroll = read_clean(con, "payroll")

        history = pd.read_csv(HISTORY, dtype=str) if HISTORY.exists() else pd.DataFrame()
        versions = []
        if not history.empty:
            required = {"employee_id","employee_name","department","age","email","effective_from","effective_to"}
            missing = required - set(history.columns)
            if missing:
                raise ValueError(f"employee_history.csv missing columns: {sorted(missing)}")
            for r in history.to_dict("records"):
                start = as_date(r["effective_from"], date(1900,1,1))
                end = as_date(r["effective_to"], date(9999,12,31))
                if end < start:
                    raise ValueError(f"effective_to before effective_from for employee_id={r['employee_id']}")
                versions.append({
                    "employee_id": int(r["employee_id"]), "employee_name": str(r["employee_name"]),
                    "department": str(r["department"]), "age": int(float(r["age"])), "email": str(r["email"]),
                    "effective_from": start, "effective_to": end,
                    "is_current": str(r.get("is_current","")).strip().lower() in {"true","1","yes"}
                })
            versions.sort(key=lambda v:(v["employee_id"],v["effective_from"]))
            prior_end = {}
            for v in versions:
                eid = v["employee_id"]
                if eid in prior_end and v["effective_from"] <= prior_end[eid]:
                    raise ValueError(f"Overlapping history periods for employee_id={eid}")
                prior_end[eid] = v["effective_to"]
        else:
            for r in employees.to_dict("records"):
                versions.append({
                    "employee_id": int(r["employee_id"]), "employee_name": str(r["employee_name"]),
                    "department": str(r["department"]), "age": int(float(r["age"])), "email": str(r["email"]),
                    "effective_from": date(1900,1,1), "effective_to": date(9999,12,31), "is_current": True
                })

        dept_names = sorted({v["department"] for v in versions})
        departments = pd.DataFrame([{"department_key":i+1,"department_name":d} for i,d in enumerate(dept_names)])
        dept_key = {r["department_name"]:int(r["department_key"]) for r in departments.to_dict("records")}
        emp_rows = []
        for i,v in enumerate(versions,1):
            emp_rows.append({"employee_key":i,"employee_id":v["employee_id"],"employee_name":v["employee_name"],
                "department_key":dept_key[v["department"]],"age":v["age"],"email":v["email"],
                "effective_from":v["effective_from"],"effective_to":v["effective_to"],"is_current":v["is_current"]})
        dim_employee = pd.DataFrame(emp_rows)

        sources = {
            "fact_salary": (salaries,"effective_date",False),
            "fact_attendance": (attendance,"attendance_date",False),
            "fact_leave": (leaves,"start_date",False),
            "fact_payroll": (payroll,"pay_period",True)
        }
        prepared, all_dates = {}, set()
        for fact,(df,date_col,is_period) in sources.items():
            rows=[]
            for idx,r in df.iterrows():
                d=as_date(r[date_col],month_period=is_period)
                all_dates.add(d)
                matches=[v for v in emp_rows if v["employee_id"]==int(r["employee_id"]) and v["effective_from"]<=d<=v["effective_to"]]
                if len(matches)!=1:
                    raise ValueError(f"Employee history lookup failed: {fact}, source row {idx+2}, employee_id={r['employee_id']}, date={d}, matches={len(matches)}. Fix employee_history.csv.")
                item=r.to_dict()
                item["_date"]=d
                item["_employee_key"]=matches[0]["employee_key"]
                if fact=="fact_leave":
                    item["_end_date"]=as_date(r["end_date"])
                    all_dates.add(item["_end_date"])
                rows.append(item)
            prepared[fact]=rows

        date_rows=[]
        for d in sorted(all_dates):
            date_rows.append({"date_key":int(d.strftime("%Y%m%d")),"full_date":d,"year":d.year,
                "quarter":(d.month-1)//3+1,"month":d.month,"month_name":d.strftime("%B"),"day":d.day})
        dim_date=pd.DataFrame(date_rows)
        date_key={r["full_date"]:r["date_key"] for r in date_rows}

        # Drop dependent facts before dimensions; recreate tables for repeatable runs.
        for t in ["fact_salary","fact_attendance","fact_leave","fact_payroll","dim_employee","dim_department","dim_date"]:
            con.execute(f'DROP TABLE IF EXISTS "{t}"')
        ddl=[
        "CREATE TABLE dim_department(department_key INTEGER PRIMARY KEY, department_name VARCHAR UNIQUE NOT NULL)",
        "CREATE TABLE dim_employee(employee_key INTEGER PRIMARY KEY, employee_id BIGINT NOT NULL, employee_name VARCHAR NOT NULL, department_key INTEGER NOT NULL, age INTEGER, email VARCHAR, effective_from DATE NOT NULL, effective_to DATE NOT NULL, is_current BOOLEAN NOT NULL, FOREIGN KEY(department_key) REFERENCES dim_department(department_key))",
        "CREATE TABLE dim_date(date_key INTEGER PRIMARY KEY, full_date DATE UNIQUE NOT NULL, year INTEGER NOT NULL, quarter INTEGER NOT NULL, month INTEGER NOT NULL, month_name VARCHAR NOT NULL, day INTEGER NOT NULL)",
        "CREATE TABLE fact_salary(fact_salary_key BIGINT PRIMARY KEY, salary_id BIGINT UNIQUE NOT NULL, employee_key INTEGER NOT NULL, date_key INTEGER NOT NULL, salary_amount DOUBLE NOT NULL, FOREIGN KEY(employee_key) REFERENCES dim_employee(employee_key), FOREIGN KEY(date_key) REFERENCES dim_date(date_key))",
        "CREATE TABLE fact_attendance(fact_attendance_key BIGINT PRIMARY KEY, attendance_id BIGINT UNIQUE NOT NULL, employee_key INTEGER NOT NULL, date_key INTEGER NOT NULL, status VARCHAR NOT NULL, hours_worked DOUBLE NOT NULL, FOREIGN KEY(employee_key) REFERENCES dim_employee(employee_key), FOREIGN KEY(date_key) REFERENCES dim_date(date_key))",
        "CREATE TABLE fact_leave(fact_leave_key BIGINT PRIMARY KEY, leave_id BIGINT UNIQUE NOT NULL, employee_key INTEGER NOT NULL, start_date_key INTEGER NOT NULL, end_date_key INTEGER NOT NULL, leave_type VARCHAR NOT NULL, status VARCHAR NOT NULL, FOREIGN KEY(employee_key) REFERENCES dim_employee(employee_key), FOREIGN KEY(start_date_key) REFERENCES dim_date(date_key), FOREIGN KEY(end_date_key) REFERENCES dim_date(date_key))",
        "CREATE TABLE fact_payroll(fact_payroll_key BIGINT PRIMARY KEY, payroll_id BIGINT UNIQUE NOT NULL, employee_key INTEGER NOT NULL, date_key INTEGER NOT NULL, pay_period VARCHAR NOT NULL, gross_pay DOUBLE NOT NULL, deductions DOUBLE NOT NULL, net_pay DOUBLE NOT NULL, FOREIGN KEY(employee_key) REFERENCES dim_employee(employee_key), FOREIGN KEY(date_key) REFERENCES dim_date(date_key))"
        ]
        for q in ddl: con.execute(q)

        def insert_df(table,df):
            con.register("load_df",df)
            cols=list(df.columns)
            col_sql=", ".join(f'"{c}"' for c in cols)
            con.execute(f'INSERT INTO "{table}" ({col_sql}) SELECT {col_sql} FROM load_df')
            con.unregister("load_df")
        insert_df("dim_department",departments)
        insert_df("dim_employee",dim_employee)
        insert_df("dim_date",dim_date)

        facts={
        "fact_salary":pd.DataFrame([{"fact_salary_key":i,"salary_id":int(r["salary_id"]),"employee_key":r["_employee_key"],"date_key":date_key[r["_date"]],"salary_amount":float(r["salary_amount"])} for i,r in enumerate(prepared["fact_salary"],1)],columns=["fact_salary_key","salary_id","employee_key","date_key","salary_amount"]),
        "fact_attendance":pd.DataFrame([{"fact_attendance_key":i,"attendance_id":int(r["attendance_id"]),"employee_key":r["_employee_key"],"date_key":date_key[r["_date"]],"status":str(r["status"]),"hours_worked":float(r["hours_worked"])} for i,r in enumerate(prepared["fact_attendance"],1)],columns=["fact_attendance_key","attendance_id","employee_key","date_key","status","hours_worked"]),
        "fact_leave":pd.DataFrame([{"fact_leave_key":i,"leave_id":int(r["leave_id"]),"employee_key":r["_employee_key"],"start_date_key":date_key[r["_date"]],"end_date_key":date_key[r["_end_date"]],"leave_type":str(r["leave_type"]),"status":str(r["status"])} for i,r in enumerate(prepared["fact_leave"],1)],columns=["fact_leave_key","leave_id","employee_key","start_date_key","end_date_key","leave_type","status"]),
        "fact_payroll":pd.DataFrame([{"fact_payroll_key":i,"payroll_id":int(r["payroll_id"]),"employee_key":r["_employee_key"],"date_key":date_key[r["_date"]],"pay_period":str(r["pay_period"]),"gross_pay":float(r["gross_pay"]),"deductions":float(r["deductions"]),"net_pay":float(r["net_pay"])} for i,r in enumerate(prepared["fact_payroll"],1)],columns=["fact_payroll_key","payroll_id","employee_key","date_key","pay_period","gross_pay","deductions","net_pay"])
        }
        for table,df in facts.items(): insert_df(table,df)

        print("\\nFACT ROW COUNT RECONCILIATION")
        for table,expected in [("fact_salary",len(salaries)),("fact_attendance",len(attendance)),("fact_leave",len(leaves)),("fact_payroll",len(payroll))]:
            actual=con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"{table:<20} Task 1 passed={expected:<6} Warehouse={actual:<6} {'PASS' if actual==expected else 'FAIL'}")
            if actual!=expected: raise AssertionError(f"Row count mismatch: {table}")

        checks={
        "fact_salary.employee_key":"SELECT COUNT(*) FROM fact_salary f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL",
        "fact_salary.date_key":"SELECT COUNT(*) FROM fact_salary f LEFT JOIN dim_date d ON f.date_key=d.date_key WHERE d.date_key IS NULL",
        "fact_attendance.employee_key":"SELECT COUNT(*) FROM fact_attendance f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL",
        "fact_attendance.date_key":"SELECT COUNT(*) FROM fact_attendance f LEFT JOIN dim_date d ON f.date_key=d.date_key WHERE d.date_key IS NULL",
        "fact_leave.employee_key":"SELECT COUNT(*) FROM fact_leave f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL",
        "fact_leave.start_date_key":"SELECT COUNT(*) FROM fact_leave f LEFT JOIN dim_date d ON f.start_date_key=d.date_key WHERE d.date_key IS NULL",
        "fact_leave.end_date_key":"SELECT COUNT(*) FROM fact_leave f LEFT JOIN dim_date d ON f.end_date_key=d.date_key WHERE d.date_key IS NULL",
        "fact_payroll.employee_key":"SELECT COUNT(*) FROM fact_payroll f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL",
        "fact_payroll.date_key":"SELECT COUNT(*) FROM fact_payroll f LEFT JOIN dim_date d ON f.date_key=d.date_key WHERE d.date_key IS NULL"}
        print("\\nORPHAN CHECKS")
        for name,sql in checks.items():
            n=con.execute(sql).fetchone()[0]
            print(f"{name:<36} {n}")
            if n: raise AssertionError(f"Orphan records found: {name}={n}")
        print("\\nSUCCESS: row counts reconcile and all checked orphan counts are zero.")
        print(f"Database: {DB}")
    finally:
        con.close()

if __name__=="__main__":
    main()
