from pathlib import Path
from datetime import datetime, timezone
import duckdb

ROOT = Path(__file__).resolve().parent
DB = ROOT / "pulseiq.duckdb"

# Each SQL query returns the number of bad rows. Critical checks fail the run; warnings are recorded.
CHECKS = [
 {"check":"employees_employee_id_unique","table":"employees","severity":"critical","sql":"SELECT COUNT(*) FROM (SELECT employee_id FROM employees GROUP BY employee_id HAVING COUNT(*) > 1)"},
 {"check":"employees_required_fields","table":"employees","severity":"critical","sql":"SELECT COUNT(*) FROM employees WHERE employee_id IS NULL OR employee_name IS NULL OR TRIM(employee_name) = '' OR department IS NULL OR age IS NULL OR email IS NULL OR TRIM(email) = ''"},
 {"check":"employees_department_allowed","table":"employees","severity":"critical","sql":"SELECT COUNT(*) FROM employees WHERE department NOT IN ('IT','HR','Finance','Operations') OR department IS NULL"},
 {"check":"employees_age_range","table":"employees","severity":"critical","sql":"SELECT COUNT(*) FROM employees WHERE TRY_CAST(age AS INTEGER) < 18 OR TRY_CAST(age AS INTEGER) > 65 OR TRY_CAST(age AS INTEGER) IS NULL"},
 {"check":"employees_email_format","table":"employees","severity":"warning","sql":"SELECT COUNT(*) FROM employees WHERE email NOT LIKE '%@%' OR email IS NULL"},
 {"check":"salary_id_unique","table":"salaries","severity":"critical","sql":"SELECT COUNT(*) FROM (SELECT salary_id FROM salaries GROUP BY salary_id HAVING COUNT(*) > 1)"},
 {"check":"salary_amount_nonnegative","table":"salaries","severity":"critical","sql":"SELECT COUNT(*) FROM salaries WHERE TRY_CAST(salary_amount AS DOUBLE) < 0 OR TRY_CAST(salary_amount AS DOUBLE) IS NULL"},
 {"check":"attendance_status_allowed","table":"attendance","severity":"critical","sql":"SELECT COUNT(*) FROM attendance WHERE status NOT IN ('Present','Absent','Leave','Holiday') OR status IS NULL"},
 {"check":"attendance_hours_range","table":"attendance","severity":"critical","sql":"SELECT COUNT(*) FROM attendance WHERE TRY_CAST(hours_worked AS DOUBLE) < 0 OR TRY_CAST(hours_worked AS DOUBLE) > 24 OR TRY_CAST(hours_worked AS DOUBLE) IS NULL"},
 {"check":"leave_dates_ordered","table":"leave","severity":"critical","sql":"SELECT COUNT(*) FROM leave WHERE start_date IS NULL OR end_date IS NULL OR end_date < start_date"},
 {"check":"leave_status_allowed","table":"leave","severity":"critical","sql":"SELECT COUNT(*) FROM leave WHERE status NOT IN ('Approved','Pending','Rejected') OR status IS NULL"},
 {"check":"payroll_math_consistent","table":"payroll","severity":"critical","sql":"SELECT COUNT(*) FROM payroll WHERE TRY_CAST(gross_pay AS DOUBLE) IS NULL OR TRY_CAST(deductions AS DOUBLE) IS NULL OR TRY_CAST(net_pay AS DOUBLE) IS NULL OR ABS(TRY_CAST(net_pay AS DOUBLE) - (TRY_CAST(gross_pay AS DOUBLE) - TRY_CAST(deductions AS DOUBLE))) > 0.01"},
 {"check":"fact_employee_keys_resolve","table":"warehouse facts","severity":"critical","sql":"SELECT (SELECT COUNT(*) FROM fact_salary f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL) + (SELECT COUNT(*) FROM fact_attendance f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL) + (SELECT COUNT(*) FROM fact_leave f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL) + (SELECT COUNT(*) FROM fact_payroll f LEFT JOIN dim_employee d USING(employee_key) WHERE d.employee_key IS NULL)"},
 {"check":"fact_row_counts_reconcile","table":"warehouse facts","severity":"critical","sql":"SELECT (SELECT ABS((SELECT COUNT(*) FROM salaries) - (SELECT COUNT(*) FROM fact_salary))) + (SELECT ABS((SELECT COUNT(*) FROM attendance) - (SELECT COUNT(*) FROM fact_attendance))) + (SELECT ABS((SELECT COUNT(*) FROM leave) - (SELECT COUNT(*) FROM fact_leave))) + (SELECT ABS((SELECT COUNT(*) FROM payroll) - (SELECT COUNT(*) FROM fact_payroll)) )"},
]

def main():
    if not DB.exists():
        raise SystemExit("pulseiq.duckdb not found. Run load_to_duckdb.py, etl.py, and build_warehouse.py first.")
    con=duckdb.connect(str(DB))
    try:
        existing={r[0] for r in con.execute("SHOW TABLES").fetchall()}
        required={"employees","salaries","attendance","leave","payroll","fact_salary","fact_attendance","fact_leave","fact_payroll","dim_employee"}
        missing=required-existing
        if missing: raise SystemExit(f"Missing required tables: {sorted(missing)}. Run Task 1 and Task 2 first.")
        con.execute("CREATE TABLE IF NOT EXISTS dq_results (check_name VARCHAR, table_name VARCHAR, severity VARCHAR, bad_rows BIGINT, status VARCHAR, run_time TIMESTAMP)")
        run_time=datetime.now()
        results=[]
        for c in CHECKS:
            bad=int(con.execute(c["sql"]).fetchone()[0] or 0)
            status="PASS" if bad==0 else ("FAIL" if c["severity"]=="critical" else "WARN")
            results.append((c["check"],c["table"],c["severity"],bad,status,run_time))
        con.execute("DELETE FROM dq_results WHERE run_time = ?",[run_time])
        con.executemany("INSERT INTO dq_results VALUES (?,?,?,?,?,?)",results)
        print("\nPULSEIQ DATA QUALITY REPORT")
        print("="*78)
        print(f"{'CHECK':34} {'SEVERITY':10} {'BAD ROWS':>9} {'STATUS':>8}")
        print("-"*78)
        for name,table,severity,bad,status,ts in results:
            print(f"{name:34} {severity:10} {bad:9} {status:>8}")
        fails=sum(r[4]=="FAIL" for r in results); warns=sum(r[4]=="WARN" for r in results)
        print("-"*78)
        print(f"Checks: {len(results)} | Failed: {fails} | Warnings: {warns} | Passed: {len(results)-fails-warns}")
        print("Saved detailed results to dq_results table in pulseiq.duckdb")
        if fails: raise SystemExit("DATA QUALITY GATE FAILED: fix critical issues before dashboard refresh.")
    finally: con.close()

if __name__=="__main__": main()
