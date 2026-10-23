"""Demonstrate selected DQ tests catch intentionally bad rows in temporary copies."""
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parent
DB=ROOT/'pulseiq.duckdb'
def main():
 con=duckdb.connect(str(DB))
 try:
  # Test the age check against a temporary table copy, never mutate production employees.
  con.execute('CREATE OR REPLACE TEMP TABLE employees_test AS SELECT * FROM employees')
  con.execute('INSERT INTO employees_test SELECT employee_id + 900000, employee_name, department, 12, email FROM employees LIMIT 1')
  bad=con.execute('SELECT COUNT(*) FROM employees_test WHERE age < 18 OR age > 65 OR age IS NULL').fetchone()[0]
  print(f'employees_age_range mutation test: bad_rows={bad} -> {"PASS" if bad>0 else "FAIL"}')
  # Test payroll arithmetic check against a temporary copy.
  con.execute('CREATE OR REPLACE TEMP TABLE payroll_test AS SELECT * FROM payroll')
  con.execute('INSERT INTO payroll_test SELECT payroll_id + 900000, employee_id, pay_period, gross_pay, deductions, net_pay + 123 FROM payroll LIMIT 1')
  bad2=con.execute('SELECT COUNT(*) FROM payroll_test WHERE ABS(net_pay-(gross_pay-deductions)) > 0.01').fetchone()[0]
  print(f'payroll_math_consistent mutation test: bad_rows={bad2} -> {"PASS" if bad2>0 else "FAIL"}')
  if bad==0 or bad2==0: raise SystemExit('A mutation test did not detect the planted issue.')
  print('Note: extend this pattern to each of the 14 checks for full checklist completion.')
 finally: con.close()
if __name__=='__main__': main()
