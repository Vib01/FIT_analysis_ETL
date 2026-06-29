import zipfile
import os
import re
import duckdb
from lxml import etree
from datetime import datetime, timedelta
from pathlib import Path

NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
RAW_TABLE = "raw_runs"

def parse_duration_from_filename(fname: str) -> float | None:
    m = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', fname)
    if not m:
        return None
    h = int(m.group(1)) if m.group(1) else 0
    mn = int(m.group(2)) if m.group(2) else 0
    s = float(m.group(3)) if m.group(3) else 0
    dur = h * 60 + mn + s / 60
    return round(dur, 1) if 1 < dur < 300 else None

def parse_tcx(content: bytes, fname: str) -> dict | None:
    try:
        root = etree.fromstring(content)
        tag = lambda t: f"{{{NS}}}{t}"

        act_id = root.find(f".//{tag('Id')}")
        start_time_str = act_id.text if act_id is not None else None
        date_str = start_time_str[:10] if start_time_str else fname[:10]

        trackpoints = root.findall(f".//{tag('Trackpoint')}")
        distances, times = [], []
        for tp in trackpoints:
            d = tp.find(tag("DistanceMeters"))
            t = tp.find(tag("Time"))
            if d is not None and d.text:
                try:
                    distances.append(float(d.text))
                except ValueError:
                    pass
            if t is not None and t.text:
                times.append(t.text)

        distance_km = round(max(distances) / 1000, 2) if distances else 0.0
        if distance_km < 0.5:
            return None

        # Duration: filename first, GPS fallback
        duration_min = parse_duration_from_filename(fname)
        if duration_min is None and len(times) >= 2:
            for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    t1 = datetime.strptime(times[0], fmt)
                    t2 = datetime.strptime(times[-1], fmt)
                    dur = round((t2 - t1).total_seconds() / 60, 1)
                    if 1 < dur < 300:
                        duration_min = dur
                    break
                except ValueError:
                    continue

        if duration_min is None:
            return None

        pace = duration_min / distance_km
        if pace < 2.5 or pace > 20:
            return None

        return {
            "date": date_str,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "pace_min_per_km": round(pace, 2),
            "source_file": fname,
        }

    except Exception as e:
        print(f"  [warn] Failed to parse {fname}: {e}")
        return None

def extract(zip_path: str, db_path: str):
    print(f"[extract] Reading {zip_path}")
    records = []

    with zipfile.ZipFile(zip_path) as z:
        tcx_files = [
            f for f in z.namelist()
            if f.endswith("Running.tcx") and "Activities" in f
        ]
        print(f"[extract] Found {len(tcx_files)} running TCX files")

        for fpath in sorted(tcx_files):
            fname = os.path.basename(fpath)
            content = z.read(fpath)
            result = parse_tcx(content, fname)
            if result:
                records.append(result)

    print(f"[extract] {len(records)} valid runs parsed")

    con = duckdb.connect(db_path)
    con.execute(f"DROP TABLE IF EXISTS {RAW_TABLE}")
    con.execute(f"""
        CREATE TABLE {RAW_TABLE} (
            date VARCHAR,
            distance_km DOUBLE,
            duration_min DOUBLE,
            pace_min_per_km DOUBLE,
            source_file VARCHAR
        )
    """)

    con.executemany(
        f"INSERT INTO {RAW_TABLE} VALUES (?, ?, ?, ?, ?)",
        [(r["date"], r["distance_km"], r["duration_min"],
          r["pace_min_per_km"], r["source_file"]) for r in records]
    )

    count = con.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
    print(f"[extract] {count} rows written to {RAW_TABLE} in {db_path}")
    con.close()