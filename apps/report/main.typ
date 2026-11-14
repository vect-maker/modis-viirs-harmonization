#import "template.typ": paper

#show: paper.with(
  title: "Multi-Sensor Harmonization of NASA FIRMS MODIS and VIIRS Active Fire Hotspots for Historical Burning Activity Calendars",
  authors: (
    (name: "[Author 1]", affil: "1"),
    (name: "[Author 2]", affil: "1"),
    (name: "[Author 3]", affil: "1"),
  ),
  affiliations: (
    "1": "[Affiliation / Country]",
  ),
  date: "2026 (Draft)",
  abstract: [
    Satellite active fire records from NASA's Moderate Resolution Imaging Spectroradiometer (MODIS, \~1 km, 2000–present) and Visible Infrared Imaging Radiometer Suite (VIIRS, 375 m, 2012–present) cannot be directly compared without accounting for spatial resolution, sensor sensitivity, and orbital overpass differences. As MODIS approaches end-of-life, emergency responders and land managers require a unified, multi-decade burning activity calendar. We present *FIRMS Harmonizer ETL*, an open-source pipeline and interactive web platform developed for the 2026 NASA Space Apps Challenge. Our ETL pipeline combines SQLModel/SQLite metadata orchestration and async HTTP/2 ingestion with out-of-core DuckDB SQL transformations to fuse MODIS and VIIRS archives into ZSTD-compressed Silver Parquet datasets and a deterministic UUIDv5 Star Schema Gold layer for PostGIS. A point-grain-preserving spatio-temporal co-detection model bins detections into \~2 km hourly quadrants to classify five diurnal/sensitivity anomaly regimes and assign harmonized VIIRS-equivalent weights without discarding native coordinates or Fire Radiative Power (FRP). An interactive Vue 3 and MapLibre GL JS frontend renders polygon-filtered hotspots, logarithmic 2000–2025 burning activity calendars, and RFC-4180 CSV exports—demonstrated on 800,480 raw Nicaragua detections (`2000-11-01` to `2025-12-31`).
  ],
  keywords: "NASA FIRMS, MODIS, VIIRS, active fire hotspots, sensor harmonization, DuckDB, PostGIS, burning activity calendar",
)

#include "sections/01-introduction.typ"
#include "sections/02-methods.typ"
#include "sections/03-results.typ"
#include "sections/04-discussion.typ"
#include "sections/05-conclusions.typ"
#include "sections/06-appendices.typ"
