import subprocess
import sys
from pathlib import Path

RAW_ZIP = Path("data/raw")
DB_PATH = "runs.duckdb"
DBT_DIR = Path("fitness_dbt")

def find_zip() -> str:
    zips = list(RAW_ZIP.glob("*.zip"))
    if not zips:
        print("[error] No zip file found in data/raw/")
        sys.exit(1)
    if len(zips) > 1:
        print(f"[warn] Multiple zips found, using most recent: {zips[-1]}")
    return str(sorted(zips)[-1])

def run_extract(zip_path: str):
    print("\n=== EXTRACT ===")
    sys.path.insert(0, str(Path("extract")))
    from extract import extract
    extract(zip_path, DB_PATH)

def run_dbt():
    print("\n=== DBT ===")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=DBT_DIR,
        capture_output=False
    )
    if result.returncode != 0:
        print("[error] dbt run failed")
        sys.exit(1)

if __name__ == "__main__":
    zip_path = find_zip()
    run_extract(zip_path)
    run_dbt()
    print("\n=== DONE === runs.duckdb is ready for Power BI")