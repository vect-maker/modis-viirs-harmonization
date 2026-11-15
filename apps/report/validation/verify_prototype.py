"""Reproduce known behavior of the unchanged experimental harmonization SQL.

This is a software/assumption check, not empirical scientific validation.
Only Python's standard library and the DuckDB CLI are required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess

REPORT = Path(__file__).resolve().parents[1]
REPO = REPORT.parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPORT / "output" / "validation")
    parser.add_argument("--refresh-report-data", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    workspace = output / "synthetic-workspace"
    for directory in ("data/processed", "data/temp/duckdb", "data/temp/harmonize"):
        (workspace / directory).mkdir(parents=True, exist_ok=True)
    executable = shutil.which("duckdb")
    if executable is None:
        raise SystemExit("DuckDB CLI is required on PATH.")

    def query(sql: str) -> list[dict[str, str]]:
        result = subprocess.run(
            [executable, "-bail", "-csv"], input=sql,
            cwd=workspace, capture_output=True, text=True, check=True,
        )
        return list(csv.DictReader(io.StringIO(result.stdout)))

    # Scenario names occupy the country key only to isolate the experiments.
    # Every coordinate, timestamp, and FRP value below is synthetic.
    query("""
CREATE OR REPLACE TABLE seed (
 country VARCHAR, latitude DOUBLE, longitude DOUBLE,
 acq_datetime TIMESTAMP, instrument VARCHAR, satellite VARCHAR, frp DOUBLE
);
INSERT INTO seed VALUES
 ('same_hour',12,-86.25,'2019-04-01 18:31:00','MODIS','Aqua',10),
 ('same_hour',12,-86.25,'2019-04-01 18:33:00','VIIRS','Suomi-NPP',10),
 ('hour_boundary',12,-86.25,'2019-04-01 18:59:00','MODIS','Aqua',10),
 ('hour_boundary',12,-86.25,'2019-04-01 19:01:00','VIIRS','Suomi-NPP',10),
 ('multiple_viirs',12,-86.25,'2019-04-01 18:20:00','MODIS','Aqua',10),
 ('multiple_viirs',12,-86.25,'2019-04-01 18:21:00','VIIRS','Suomi-NPP',10),
 ('multiple_viirs',12,-86.25,'2019-04-01 18:40:00','VIIRS','NOAA-20',10),
 ('null_frp',12,-86.25,'2019-04-01 18:21:00','VIIRS','Suomi-NPP',NULL);
INSERT INTO seed
 SELECT 'spatial_boundary',12,
        -84.37/cos(radians(12.0)) + sign*0.000001,
        TIMESTAMP '2019-04-01 18:31:00' + delta*INTERVAL '1 minute',
        instrument,satellite,10
 FROM (VALUES (-1,0,'MODIS','Aqua'),(1,2,'VIIRS','Suomi-NPP'))
 AS pair(sign,delta,instrument,satellite);
INSERT INTO seed
 SELECT c,12,-86.25,TIMESTAMP '2019-01-01 18:10:00'+i*INTERVAL '1 day',
        'MODIS','Aqua',10
 FROM (VALUES ('one_viirs'),('two_viirs')) AS countries(c),range(100) AS days(i);
INSERT INTO seed
 SELECT c,12,-86.25+k*0.0001,
        TIMESTAMP '2019-01-01 18:20:00'+i*INTERVAL '1 day',
        'VIIRS',satellite,10
 FROM (VALUES ('one_viirs','Suomi-NPP'),
              ('two_viirs','Suomi-NPP'),
              ('two_viirs','NOAA-20')) AS platforms(c,satellite),
      range(100) AS days(i),range(2) AS pixels(k);
COPY (
 SELECT *,320.0 AS bright_mir,1.0 AS scan,1.0 AS track,
        90 AS confidence,'h' AS confidence_class,'synthetic' AS version,
        295.0 AS bright_tir,'D' AS daynight,0 AS type
 FROM seed
) TO 'data/processed/hotspots.parquet' (FORMAT PARQUET);
""")
    sources = sorted((REPO / "apps/pipeline/sql/harmonize").glob("*.sql"))
    if len(sources) != 4:
        raise AssertionError("Expected the four documented SQL stages.")
    hashes = {}
    for source in sources:
        subprocess.run(
            [executable, "-bail", "-f", str(source)],
            cwd=workspace, capture_output=True, text=True, check=True,
        )
        hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    activity = query("""
SELECT country AS scenario,count(*) AS records,
       sum(harmonized_weight) AS activity,
       count(*) FILTER(WHERE harmonization_category='MODIS_REDUNDANT_CODETECTION')
         AS suppressed_modis
FROM read_parquet('data/processed/hotspots_harmonized.parquet')
GROUP BY country ORDER BY country;
""")
    calibration = query("""
SELECT * FROM read_parquet('data/temp/harmonize/03_country_calibration.parquet')
WHERE country IN ('one_viirs','two_viirs') ORDER BY country;
""")
    native = query("""
WITH original AS (
 SELECT country,latitude,longitude,acq_datetime,instrument,satellite,frp
 FROM read_parquet('data/processed/hotspots.parquet')
), result AS (
 SELECT country,latitude,longitude,acq_datetime,instrument,satellite,frp
 FROM read_parquet('data/processed/hotspots_harmonized.parquet')
)
SELECT count(*) AS mismatches FROM (
 (SELECT * FROM original EXCEPT ALL SELECT * FROM result)
 UNION ALL
 (SELECT * FROM result EXCEPT ALL SELECT * FROM original)
);
""")
    nulls = query("""
SELECT frp IS NULL AS native_is_null, harmonized_frp AS derived_frp
FROM read_parquet('data/processed/hotspots_harmonized.parquet')
WHERE country='null_frp';
""")
    by_case = {row["scenario"]: row for row in activity}
    expected = {
        "same_hour": (2, 1.0), "hour_boundary": (2, 7.12),
        "spatial_boundary": (2, 7.12), "multiple_viirs": (3, 2.0),
        "null_frp": (1, 1.0), "one_viirs": (300, 200.0),
        "two_viirs": (500, 400.0),
    }
    for name, (records, value) in expected.items():
        assert int(by_case[name]["records"]) == records, name
        assert abs(float(by_case[name]["activity"]) - value) < 1e-9, name
    assert int(native[0]["mismatches"]) == 0
    assert sum(int(row["records"]) for row in activity) == 810
    for row, factor in zip(calibration, (2.0, 4.0), strict=True):
        for key in ("f_morning", "f_afternoon", "f_frp"):
            assert float(row[key]) == factor, (row["country"], key)
    assert nulls[0]["native_is_null"] == "true"
    assert float(nulls[0]["derived_frp"]) == 0.0

    archive = json.loads((REPO / "apps/frontend/src/data/historical_monthly.json").read_text(encoding="utf-8"))
    assert sum(month["total"] for month in archive["months"]) == archive["totalRecords"]
    april = [{key: month[key] for key in ("year", "total", "modisCount", "viirsCount", "avgFrp")}
             for month in archive["months"]
             if month["month"] == 4 and month["year"] in (2005, 2011, 2012, 2018, 2020)]
    summary = {
        "status": "synthetic_behavior_verified",
        "scientific_validation": False,
        "synthetic_records": 810,
        "native_mismatches": 0,
        "duckdb_version": query("SELECT version() AS version;")[0]["version"],
        "sql_sha256": hashes,
        "scenarios": activity,
        "calibration": calibration,
        "null_frp": nulls[0],
        "spatial_separation_m": 0.21777478182737448,
        "archive": {key: archive[key] for key in
                    ("country", "harmonized", "coverageVerified", "totalRecords", "firstDetection", "lastDetection")},
        "april": april,
    }
    for filename, rows in (("scenarios.csv", activity), ("calibration.csv", calibration)):
        with (output / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    if args.refresh_report_data:
        (REPORT / "validation/results.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print("Verified 810 synthetic records, four unchanged SQL stages, and archive totals.")
    print("Known limitations reproduced; scientific validation remains pending.")
    print(output / "summary.json")


if __name__ == "__main__":
    main()
