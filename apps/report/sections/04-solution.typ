#import "../template.typ": tight, note

= 4. Developed Solution

== Overview

PyroTrace is a complete data product, from download to visualization. A batch pipeline assembles and harmonizes the historical archive, a worker keeps it current with near-real-time detections, a spatial database stores the result, an API publishes it, and a web application presents it to the public. @fig-architecture shows how the components connect.

#let node(title, body, fill: rgb("#f3f5f7")) = box(
  width: 100%,
  inset: 7pt,
  radius: 4pt,
  stroke: 0.6pt + rgb("#6b7785"),
  fill: fill,
)[#text(weight: "bold", size: 10pt)[#title] \ #text(size: 9pt)[#body]]
#let arrow = align(center + horizon, text(size: 14pt)[→])

#figure(
  tight(grid(
    columns: (1fr, 14pt, 1.15fr, 14pt, 1fr, 14pt, 1fr, 14pt, 1.05fr),
    align: horizon,
    node([NASA FIRMS], [Country archive (CSV) and Area API for near-real-time data], fill: rgb("#fff4dc")),
    arrow,
    node([Pipeline], [Python download, DuckDB fusion, four-stage harmonization, star schema]),
    arrow,
    node([PostGIS], [Detections, weights, fire events, and geometries]),
    arrow,
    node([FastAPI], [About 40 REST endpoints and live alerts (SSE)]),
    arrow,
    node([Web app], [Landing page, map, calendar, statistics, CSV export], fill: rgb("#e6f1fb")),
  )),
  caption: [PyroTrace Architecture From Data Source to User],
) <fig-architecture>
#note[A containerized worker queries the FIRMS Area API every five minutes and writes new detections to PostGIS; NATS JetStream stores its progress and distributes live notifications. All services run as Podman containers behind a Caddy reverse proxy on a Microsoft Azure virtual machine.]

== Components

*Data pipeline.* Python scripts download the FIRMS country archives as CSV files, track each country, year, and instrument in a SQLite catalog, and convert them to Parquet. All further processing is written in DuckDB SQL, which processes the multi-year archive on a single workstation without loading it into memory. The pipeline fuses MODIS and VIIRS into one table, runs the four harmonization stages described in Section 5, builds a star schema with deterministic identifiers, groups detections into fire events, and loads everything into PostgreSQL with PostGIS.

*Near-real-time worker.* A separate service catches up from the end of the archive and then polls the FIRMS Area API for MODIS, Suomi-NPP, NOAA-20, and NOAA-21. It assigns each detection to a country by testing it against country polygons and inserts it without duplicates. These recent records are labeled as provisional because they have not yet passed through the harmonization pipeline.

*API.* A FastAPI and SQLModel backend exposes about 40 documented endpoints (OpenAPI) for detections, available dates, daily activity, the historical calendar, monthly and annual statistics, spatial density, anomaly detection, correlations, forecasts, fire-event movement, weather context from NASA POWER @nasapower, alerts, and user accounts.

*Web application.* A Vue 3 single-page application presents the data in four places (@fig-map, @fig-calendar, @fig-stats-monthly, and @fig-stats-annual in Section 6):
- an interactive MapLibre map with date, sensor, and drawn-area filters, fire-event footprints, and CSV export;
- a historical calendar of monthly activity from 2000 to the present;
- a statistics panel with ten charts, including the comparison of each month with its historical range and the annual series in raw or harmonized units;
- a public landing page that explains the sensors, the harmonization method, and the limits of the data in plain language.

== Relevant Decisions

The team kept every original detection instead of replacing the record with a derived grid, so each value on the screen can be traced back to FIRMS. Harmonization is expressed as a weight per detection, which keeps the method transparent and lets the interface show raw counts and the harmonized index side by side. The statistics only compare complete months: partial months and near-real-time months are marked and excluded from the historical baseline, so incomplete data does not look like low or high fire activity. Finally, the repository is public so that other teams can audit, reuse, and improve the method.

== Distinctive Contribution

PyroTrace combines a harmonized 25-year regional record, a transparent and testable weighting method, and an interface designed for people without geospatial training. It does not present the harmonized index as a solved problem. It reports how much of the sensor-transition effect it removes and how much remains, and it makes the raw data available for anyone who wants to test a different approach.
