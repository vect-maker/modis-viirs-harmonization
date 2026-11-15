= Introduction

== Scientific motivation

An active-fire record is a satellite observation of a thermal anomaly. It is not automatically an individual fire event or a measurement of burned area. FIRMS coordinates locate pixel centers; a MODIS pixel can contain more than one fire. MODIS fire detections have nominal 1 km resolution, with larger footprints away from nadir @firmsmodis. VIIRS 375 m detections offer a greater response to smaller fires @firmsviirs. The algorithm publications describe different instrument-specific detection procedures @giglio2016 @schroeder2014.

Consequently, merging records into one schema does not by itself make their counts comparable. Repeated observations, clouds, acquisition timing, collection changes, and the number of operating platforms can affect observed activity. A zero count alone cannot distinguish no fire from missed observation @firmsnotes.

== Prototype objective and scope

PyroTrace is developed in the context of the NASA Space Apps challenge on MODIS and VIIRS hot spots. The objective of this report is to describe a working experimental workflow and its limitations accurately. It does not claim that sensor-transition discontinuities have been removed.

The prototype explores three operations: preserving original observations, identifying candidate MODIS-VIIRS co-occurrences, and weighting MODIS-only records toward a provisional VIIRS-referenced activity index. This reference is not yet fixed to one platform and observation schedule. Historical trend interpretation therefore remains outside the demonstrated scope.

== System and evidence boundaries

The repository contains a Python/SQLite ingestion pipeline, DuckDB/Parquet transformations, a PostgreSQL/PostGIS star schema, a FastAPI backend, and a Vue/MapLibre frontend. These components support data access and visualization; their existence is not evidence of scientific calibration accuracy.

This revision verifies the SQL using synthetic inputs and checks the bundled monthly JSON. Original FIRMS Parquet inputs and cloud/swath metadata were unavailable in this checkout. No new full-archive calibration, field comparison, or real-data accuracy measurement is reported. Previously recorded ingestion timings and backend test counts are not reused as harmonization evidence.

== Verified source boundaries

The FIRMS archive page distinguishes Terra records beginning in November 2000 from Aqua records beginning in July 2002, and lists NOAA-20 archive availability from April 2018 and NOAA-21 from January 2024 @firmsarchive. Launch dates are not interchangeable with product availability. The supplied monthly JSON is not platform-resolved, so this review cannot independently verify its claimed platform mix.

NASA's product documentation supports the sensor properties in this report. It does not establish the project's fallback factors, bin widths, minimum sample count, or clipping bounds. Those are implementation choices documented in Section 2.
