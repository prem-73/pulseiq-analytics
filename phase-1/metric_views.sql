-- PulseIQ Day 4 governed metric views. Based on the available Task 1/2 schema.
-- Compare these provisional definitions with the official metric_dictionary before submission.
CREATE OR REPLACE VIEW metric_catalog AS SELECT * FROM (VALUES
  ('metric_headcount', 'Current employee count', 'employees', 'HR Analytics'),
  ('metric_headcount_by_department', 'Employee count by department', 'employees', 'HR Analytics'),
  ('metric_average_age', 'Average employee age', 'employees', 'HR Analytics'),
  ('metric_minimum_age', 'Minimum employee age', 'employees', 'HR Analytics'),
  ('metric_maximum_age', 'Maximum employee age', 'employees', 'HR Analytics'),
  ('metric_department_count', 'Number of represented departments', 'employees', 'HR Analytics'),
  ('metric_salary_total', 'Total salary amount in salary records', 'salaries', 'Compensation'),
  ('metric_salary_average', 'Average salary amount', 'salaries', 'Compensation'),
  ('metric_salary_minimum', 'Minimum salary amount', 'salaries', 'Compensation'),
  ('metric_salary_maximum', 'Maximum salary amount', 'salaries', 'Compensation'),
  ('metric_salary_by_department', 'Salary total by department', 'salaries + dim_employee', 'Compensation'),
  ('metric_attendance_records', 'Total attendance records', 'attendance', 'Workforce Operations'),
  ('metric_present_records', 'Attendance records marked Present', 'attendance', 'Workforce Operations'),
  ('metric_absent_records', 'Attendance records marked Absent', 'attendance', 'Workforce Operations'),
  ('metric_attendance_rate', 'Present records divided by non-holiday attendance records', 'attendance', 'Workforce Operations'),
  ('metric_hours_worked_total', 'Total recorded hours worked', 'attendance', 'Workforce Operations'),
  ('metric_hours_worked_average', 'Average hours per attendance record', 'attendance', 'Workforce Operations'),
  ('metric_attendance_by_status', 'Attendance records by status', 'attendance', 'Workforce Operations'),
  ('metric_leave_requests', 'Total leave requests', 'leave', 'Workforce Operations'),
  ('metric_approved_leaves', 'Approved leave requests', 'leave', 'Workforce Operations'),
  ('metric_pending_leaves', 'Pending leave requests', 'leave', 'Workforce Operations'),
  ('metric_rejected_leaves', 'Rejected leave requests', 'leave', 'Workforce Operations'),
  ('metric_leave_days_requested', 'Total calendar days across leave requests', 'leave', 'Workforce Operations'),
  ('metric_payroll_gross_total', 'Total gross payroll', 'payroll', 'Finance'),
  ('metric_payroll_deductions_total', 'Total payroll deductions', 'payroll', 'Finance'),
  ('metric_payroll_net_total', 'Total net payroll', 'payroll', 'Finance'),
  ('metric_payroll_average_net', 'Average net pay per payroll record', 'payroll', 'Finance'),
  ('metric_payroll_by_period', 'Gross, deductions and net pay by pay period', 'payroll', 'Finance')
) AS t(metric_name, definition, source, owner);

CREATE OR REPLACE VIEW metric_headcount AS SELECT COUNT(DISTINCT employee_id) AS employee_count FROM dim_employee WHERE is_current = TRUE;
CREATE OR REPLACE VIEW metric_headcount_by_department AS SELECT d.department_name AS department, COUNT(DISTINCT e.employee_id) AS employee_count FROM dim_employee e JOIN dim_department d USING (department_key) WHERE e.is_current = TRUE GROUP BY d.department_name;
CREATE OR REPLACE VIEW metric_average_age AS SELECT AVG(TRY_CAST(age AS DOUBLE)) AS average_age FROM employees;
CREATE OR REPLACE VIEW metric_minimum_age AS SELECT MIN(age) AS minimum_age FROM employees;
CREATE OR REPLACE VIEW metric_maximum_age AS SELECT MAX(age) AS maximum_age FROM employees;
CREATE OR REPLACE VIEW metric_department_count AS SELECT COUNT(DISTINCT d.department_name) AS department_count FROM dim_employee e JOIN dim_department d USING (department_key) WHERE e.is_current = TRUE;
CREATE OR REPLACE VIEW metric_salary_total AS SELECT SUM(TRY_CAST(salary_amount AS DOUBLE)) AS salary_total FROM salaries;
CREATE OR REPLACE VIEW metric_salary_average AS SELECT AVG(TRY_CAST(salary_amount AS DOUBLE)) AS average_salary FROM salaries;
CREATE OR REPLACE VIEW metric_salary_minimum AS SELECT MIN(TRY_CAST(salary_amount AS DOUBLE)) AS minimum_salary FROM salaries;
CREATE OR REPLACE VIEW metric_salary_maximum AS SELECT MAX(TRY_CAST(salary_amount AS DOUBLE)) AS maximum_salary FROM salaries;
CREATE OR REPLACE VIEW metric_salary_by_department AS SELECT d.department_name AS department, SUM(TRY_CAST(f.salary_amount AS DOUBLE)) AS salary_total FROM fact_salary f JOIN dim_employee e USING(employee_key) JOIN dim_department d USING(department_key) GROUP BY d.department_name;
CREATE OR REPLACE VIEW metric_attendance_records AS SELECT COUNT(*) AS attendance_records FROM attendance;
CREATE OR REPLACE VIEW metric_present_records AS SELECT COUNT(*) AS present_records FROM attendance WHERE status='Present';
CREATE OR REPLACE VIEW metric_absent_records AS SELECT COUNT(*) AS absent_records FROM attendance WHERE status='Absent';
CREATE OR REPLACE VIEW metric_attendance_rate AS SELECT 100.0 * COUNT(*) FILTER (WHERE status='Present') / NULLIF(COUNT(*) FILTER (WHERE status <> 'Holiday'),0) AS attendance_rate_pct FROM attendance;
CREATE OR REPLACE VIEW metric_hours_worked_total AS SELECT SUM(TRY_CAST(hours_worked AS DOUBLE)) AS total_hours_worked FROM attendance;
CREATE OR REPLACE VIEW metric_hours_worked_average AS SELECT AVG(TRY_CAST(hours_worked AS DOUBLE)) AS average_hours_worked FROM attendance;	
CREATE OR REPLACE VIEW metric_attendance_by_status AS SELECT status, COUNT(*) AS record_count FROM attendance GROUP BY status;
CREATE OR REPLACE VIEW metric_leave_requests AS SELECT COUNT(*) AS leave_requests FROM leave;
CREATE OR REPLACE VIEW metric_approved_leaves AS SELECT COUNT(*) AS approved_leaves FROM leave WHERE status='Approved';
CREATE OR REPLACE VIEW metric_pending_leaves AS SELECT COUNT(*) AS pending_leaves FROM leave WHERE status='Pending';
CREATE OR REPLACE VIEW metric_rejected_leaves AS SELECT COUNT(*) AS rejected_leaves FROM leave WHERE status='Rejected';
CREATE OR REPLACE VIEW metric_leave_days_requested AS SELECT SUM(date_diff('day', TRY_CAST(start_date AS DATE), TRY_CAST(end_date AS DATE)) + 1) AS leave_days_requested FROM leave;
CREATE OR REPLACE VIEW metric_payroll_gross_total AS SELECT SUM(TRY_CAST(gross_pay AS DOUBLE)) AS gross_pay_total FROM payroll;
CREATE OR REPLACE VIEW metric_payroll_deductions_total AS SELECT SUM(TRY_CAST(deductions AS DOUBLE)) AS deductions_total FROM payroll;
CREATE OR REPLACE VIEW metric_payroll_net_total AS SELECT SUM(TRY_CAST(net_pay AS DOUBLE)) AS net_pay_total FROM payroll;
CREATE OR REPLACE VIEW metric_payroll_average_net AS SELECT AVG(TRY_CAST(net_pay AS DOUBLE)) AS average_net_pay FROM payroll;
CREATE OR REPLACE VIEW metric_payroll_by_period AS SELECT pay_period, SUM(TRY_CAST(gross_pay AS DOUBLE)) AS gross_pay, SUM(TRY_CAST(deductions AS DOUBLE)) AS deductions, SUM(TRY_CAST(net_pay AS DOUBLE)) AS net_pay FROM payroll GROUP BY pay_period;
CREATE OR REPLACE VIEW metric_headcount_monthly AS WITH months AS (SELECT CAST(date_trunc('month', full_date) + INTERVAL '1 month' - INTERVAL '1 day' AS DATE) AS month_end FROM dim_date GROUP BY 1) SELECT m.month_end, COUNT(DISTINCT e.employee_id) AS employee_count FROM months m LEFT JOIN dim_employee e ON e.effective_from <= m.month_end AND e.effective_to > m.month_end GROUP BY m.month_end ORDER BY m.month_end;
