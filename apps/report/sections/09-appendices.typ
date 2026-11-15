#import "../template.typ": tight, note

#pagebreak()
#align(center)[*Appendix A*]
#align(center)[*Reproduction*]

The repository contains everything needed to reproduce the results. From the repository root, the pipeline is run with the `just` recipes below; they download the FIRMS archive, fuse and harmonize it, build the star schema, and load it into PostGIS.

#tight(raw(block: true, lang: "bash", "just pipeline::setup-env
just pipeline::sync-meta
just pipeline::fetch-central-america
just pipeline::fuse-data
just pipeline::harmonize-data
just pipeline::normalize-data
just pipeline::db-schema
just pipeline::db-load
just pipeline::cluster-events"))

The synthetic verification and this report are reproduced from `apps/report`:

#tight(raw(block: true, lang: "bash", "python validation/verify_prototype.py --refresh-report-data
typst compile --font-path fonts main.typ output/report.pdf"))

The runner requires the DuckDB command-line interface. It records the DuckDB version and the SHA-256 hash of each SQL file in `validation/results.json`, which this report reads directly. If the SQL changes, the runner must be executed again before the report is rebuilt.

#pagebreak()
#align(center)[*Appendix B*]
#align(center)[*Evidence Status at Delivery*]

#figure(
  table(
    columns: (62%, 38%),
    table.header([Evidence item], [Status]),
    [Complete FIRMS archive for seven countries (3,621,309 detections)], [Processed and loaded],
    [Four SQL stages on 810 synthetic records], [Verified],
    [Native attributes preserved in the synthetic tests], [Verified],
    [Harmonized index in the application], [Integrated (statistics panel)],
    [Historical calendar], [Raw counts],
    [Sensor-transition consistency], [Residual step of 37% after 2012],
    [MODIS platform normalization for 2001 and 2002], [Pending],
    [Harmonization of near-real-time data], [Pending],
    [Cloud and overpass coverage correction], [Not implemented],
    [Held-out scientific validation], [Pending],
  ),
  caption: [Status of the Evidence on November 15, 2026],
) <tbl-status>
