from pathlib import Path
import json
import math
import re
from datetime import date, datetime
import duckdb

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "raw"
CONTRACT_PATH = ROOT / "data_contracts.json"
DB_PATH = ROOT / "pulseiq.duckdb"

def is_missing(value):
    if value is None:
        return True
    try:
        return bool(value != value)  # NaN
    except Exception:
        return False

def validate_value(value, rule):
    errors = []
    if is_missing(value) or (isinstance(value, str) and value.strip() == ""):
        if not rule.get("nullable", True):
            errors.append("required value is missing")
        return errors

    kind = rule.get("type", "string")
    parsed = value
    try:
        if kind == "integer":
            # Prevent values like 2.5 being silently accepted as integers.
            number = float(value)
            if not number.is_integer():
                raise ValueError()
            parsed = int(number)
        elif kind == "number":
            parsed = float(value)
            if not math.isfinite(parsed):
                raise ValueError()
        elif kind == "date":
            parsed = date.fromisoformat(str(value)[:10])
        elif kind == "string":
            parsed = str(value)
    except (ValueError, TypeError, OverflowError):
        errors.append(f"expected {kind}")
        return errors

    if "min" in rule and parsed < rule["min"]:
        errors.append(f"value below minimum {rule['min']}")
    if "max" in rule and parsed > rule["max"]:
        errors.append(f"value above maximum {rule['max']}")
    if "min_length" in rule and len(str(parsed)) < rule["min_length"]:
        errors.append(f"length below minimum {rule['min_length']}")
    if "allowed_values" in rule and parsed not in rule["allowed_values"]:
        errors.append(f"value not in allowed values {rule['allowed_values']}")
    if "contains" in rule and rule["contains"] not in str(parsed):
        errors.append(f"value must contain {rule['contains']}")
    return errors

def main():
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Data contract file not found: {CONTRACT_PATH}")
    contracts = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    con = duckdb.connect(str(DB_PATH))
    summary = []
    quarantine_rows = []

    try:
        for table, table_contract in contracts.items():
            csv_path = DATA_DIR / table_contract["file"]
            if not csv_path.exists():
                raise FileNotFoundError(f"Expected input file missing: {csv_path}")

            escaped_path = str(csv_path).replace("\\", "/").replace("'", "''")
            # Read each feed directly so all input rows are checked each run.
            df = con.execute(
                f"SELECT * FROM read_csv_auto('{escaped_path}', header=true, all_varchar=true)"
            ).fetchdf()

            expected_columns = set(table_contract["columns"])
            actual_columns = set(df.columns)
            missing_columns = expected_columns - actual_columns
            unexpected_columns = actual_columns - expected_columns

            if missing_columns:
                raise ValueError(f"{table}: required columns missing: {sorted(missing_columns)}")
            if unexpected_columns:
                print(f"WARNING: {table} has unexpected columns {sorted(unexpected_columns)}; feed will be quarantined for review.")
                # Feed-level contract issue: mark all rows as quarantined instead of silently dropping new fields.
                for idx, row in df.iterrows():
                    quarantine_rows.append({
                        "source_table": table,
                        "source_row_number": int(idx) + 2,
                        "reason": "unexpected column(s): " + ", ".join(sorted(unexpected_columns)),
                        "row_json": row.to_json()
                    })
                summary.append({"table_name": table, "rows_in": len(df), "rows_passed": 0, "rows_quarantined": len(df)})
                continue

            passed_records = []
            quarantined_count = 0
            seen_unique = {col: set() for col, rule in table_contract["columns"].items() if rule.get("unique")}

            for idx, row in df.iterrows():
                row_errors = []
                for col, rule in table_contract["columns"].items():
                    value = row[col]
                    errs = validate_value(value, rule)
                    for err in errs:
                        row_errors.append(f"{col}: {err}")
                    if rule.get("unique") and not is_missing(value):
                        normalized = str(value).strip()
                        if normalized in seen_unique[col]:
                            row_errors.append(f"{col}: duplicate value {normalized}")
                        else:
                            seen_unique[col].add(normalized)

                # Cross-column business rules
                if table == "leave":
                    try:
                        if date.fromisoformat(str(row["end_date"])[:10]) < date.fromisoformat(str(row["start_date"])[:10]):
                            row_errors.append("end_date: earlier than start_date")
                    except Exception:
                        pass
                if table == "payroll":
                    try:
                        if abs(float(row["gross_pay"]) - float(row["deductions"]) - float(row["net_pay"])) > 0.01:
                            row_errors.append("net_pay: gross_pay - deductions does not equal net_pay")
                    except Exception:
                        pass

                record = row.to_dict()
                if row_errors:
                    quarantined_count += 1
                    quarantine_rows.append({
                        "source_table": table,
                        "source_row_number": int(idx) + 2,
                        "reason": "; ".join(row_errors),
                        "row_json": json.dumps(record, default=str)
                    })
                else:
                    passed_records.append(record)

            passed_df = __import__("pandas").DataFrame(passed_records, columns=list(table_contract["columns"]))
            con.register("passed_df", passed_df)
            con.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM passed_df')
            con.unregister("passed_df")

            summary.append({
                "table_name": table,
                "rows_in": len(df),
                "rows_passed": len(passed_records),
                "rows_quarantined": quarantined_count
            })

        import pandas as pd
        quarantine_df = pd.DataFrame(quarantine_rows, columns=["source_table", "source_row_number", "reason", "row_json"])
        con.register("quarantine_df", quarantine_df)
        con.execute("CREATE OR REPLACE TABLE quarantine AS SELECT * FROM quarantine_df")
        con.unregister("quarantine_df")

        summary_df = pd.DataFrame(summary, columns=["table_name", "rows_in", "rows_passed", "rows_quarantined"])
        con.register("summary_df", summary_df)
        con.execute("CREATE OR REPLACE TABLE etl_summary AS SELECT * FROM summary_df")
        con.unregister("summary_df")

        print("\nETL PIPELINE SUMMARY")
        print("-" * 76)
        print(f"{'Table':<16}{'Rows In':>12}{'Passed':>12}{'Quarantined':>16}")
        print("-" * 76)
        for item in summary:
            print(f"{item['table_name']:<16}{item['rows_in']:>12}{item['rows_passed']:>12}{item['rows_quarantined']:>16}")
            assert item["rows_in"] == item["rows_passed"] + item["rows_quarantined"], f"Count mismatch for {item['table_name']}"
        print("-" * 76)
        print(f"Quarantine records: {len(quarantine_rows)}")
        print(f"Database: {DB_PATH}")
        print("Validation completed. Counts reconcile for every table.")
    finally:
        con.close()

if __name__ == "__main__":
    main()
