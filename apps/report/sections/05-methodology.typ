#import "../template.typ": tight, note

= 5. Methodology and Scientific Resources

== Work Process

The team worked in four stages during the event. First, it studied the challenge and the FIRMS products to define the problem and the target region. Second, it designed a harmonization method that could be expressed as SQL and audited line by line. Third, it implemented the pipeline, the database, the API, and the web application in parallel. Fourth, it verified the software with synthetic tests and evaluated the harmonized record with diagnostics on the real data, which are reported in Section 6.

== Data and Scientific Resources

@tbl-sources lists the data used by PyroTrace. The core input is the NASA FIRMS active-fire archive; the other sources provide map context and weather.

#figure(
  table(
    columns: (25%, 42%, 33%),
    table.header([Resource], [Use in PyroTrace], [Source]),
    [MODIS active fires (Terra, Aqua)], [Historical record from November 2000; nominal 1 km pixel], [NASA FIRMS @firmsmodis @firmsarchive],
    [VIIRS 375 m active fires (Suomi-NPP, NOAA-20, NOAA-21)], [Record from 2012; reference unit of the harmonized index], [NASA FIRMS @firmsviirs @viirsguide2024],
    [FIRMS country archive and Area API], [Bulk download of the archive and near-real-time updates], [NASA FIRMS @firmsapi],
    [NASA POWER daily point data], [Weather context for fire events], [NASA Langley @nasapower],
    [Country boundaries], [Country assignment and map outlines], [Natural Earth @naturalearth],
    [Satellite basemap], [Map background], [Esri World Imagery @esriworldimagery],
  ),
  caption: [Data Sources and Scientific Resources],
) <tbl-sources>

Each record keeps its FIRMS attributes: coordinates of the pixel center, acquisition date and time in UTC, satellite, instrument, brightness temperatures, confidence, fire radiative power (FRP), pixel dimensions, day or night flag, and product version. Shared column names for brightness temperatures do not make the spectral bands equivalent, and the numeric codes assigned to VIIRS confidence classes (20, 50, and 90) are a storage convention, not calibrated probabilities @firmsmodis @firmsviirs.

== Harmonization Method

The method runs in four DuckDB SQL stages over the fused archive. It never deletes or moves a detection; it only adds a category, a weight, and a derived FRP value.

=== Stage 1: Local Solar Time and Search Keys

Satellites cross the region at fixed local solar times, so the acquisition time is converted to an approximate local mean solar hour from the UTC hour $h$, the minutes $m$, and the longitude $lambda$ in degrees:

$ h_s = (h + m/60 + lambda/15) mod 24 $ <eq-solar>

The solar hour assigns each detection to an overpass window (@tbl-windows). Each detection also receives a spatial cell and an hourly slot, with latitude $phi$ and a step of $d = 0.02 degree$ (about 2.2 km):

$ y = floor(phi/d), quad x = floor((lambda cos phi)/d), quad s = floor(t/3600) $ <eq-cells>

where $t$ is the acquisition time in seconds since the Unix epoch. The cells only speed up the search; they do not decide whether two detections match.

#figure(
  table(
    columns: (40%, 60%),
    table.header([Window], [Local solar hours]),
    [Morning (Terra)], [08:30 to before 12:00],
    [Afternoon (Aqua and VIIRS)], [12:00 to before 16:00],
    [Night (Terra)], [20:00 to before 23:30],
    [Night and dawn (Aqua and VIIRS)], [23:30 to before 04:00],
    [Off-cycle], [All remaining hours],
  ),
  caption: [Overpass Windows Used by the Method],
) <tbl-windows>
#note[Window boundaries are project choices based on the nominal overpass times of each platform.]

=== Stage 2: MODIS and VIIRS Co-Detections

For each MODIS detection, the method searches the 27 neighboring combinations of cell and hour ($3 times 3 times 3$) and keeps any VIIRS detection from the same country that lies within 2,200 m and 3,600 s. Distance $D$, in meters, uses an equirectangular approximation with the mean latitude $overline(phi)$ of the pair, where 111,320 m is the length of one degree of latitude:

$ D = "111,320" sqrt((Delta phi)^2 + (Delta lambda cos overline(phi))^2) $ <eq-distance>

Both members of a matched pair are flagged as co-detections. Searching neighboring cells removes the artifacts of a fixed grid: two detections two minutes apart across an hour boundary, or a few meters apart across a cell edge, are still matched (Section 6.4).

=== Stage 3: Country Calibration

The number of VIIRS platforms changes over time, so each VIIRS detection is first divided by the number of VIIRS satellites active in its country and year, $p_(c,y)$. Using only the overlap period (2012 onward), the method estimates four ratios for each country $c$:

$ r_m = (sum_(i in V^*) 1/p_(c,y)) / abs(M^*), quad r_a = (sum_(i in V_a) 1/p_(c,y)) / abs(M_a), quad r_n = (sum_(i in V_n) 1/p_(c,y)) / abs(M_n) $ <eq-ratios>

Here $V^*$ and $M^*$ are the co-detected VIIRS and MODIS records; $V_a$ and $M_a$ are all records in the afternoon window; and $V_n$ and $M_n$ are all records in the night and off-cycle windows. A fourth ratio, $r_p$, divides the platform-normalized FRP of co-detected VIIRS records by the FRP of co-detected MODIS records. When a country has at least 100 co-detected MODIS records, each factor is the ratio bounded to a plausible range and rounded to two decimals; otherwise a fallback value is used (@tbl-factors).

$ f = "round"(max(l, min(r, u)), 2) $ <eq-clamp>

#figure(
  table(
    columns: (34%, 18%, 22%, 26%),
    table.header([Factor], [Ratio], [Bounds], [Fallback]),
    [Morning, $f_m$], [$r_m$], [1 to 10], [2.20],
    [Afternoon, $f_a$], [$r_a$], [1 to 20], [6.12],
    [Night and off-cycle, $f_n$], [$r_n$], [1 to 15], [4.50],
    [FRP, $f_p$], [$r_p$], [0.5 to 5], [1.14],
  ),
  caption: [Calibration Factors, Bounds, and Fallback Values],
) <tbl-factors>
#note[The threshold of 100 co-detections, the bounds, and the fallback values are engineering choices of the project. No published study establishes them as transferable constants, and no uncertainty is propagated yet.]

=== Stage 4: Weights and Derived FRP

Each detection $i$ in country $c$ and year $y$ receives the weight

$ w_i = cases(
  1 / p_(c,y) & "if" i "is VIIRS",
  0 & "if" i "is MODIS and co-detected",
  f_m & "if" i "is MODIS in the morning window",
  f_a & "if" i "is MODIS in the afternoon window",
  f_n & "otherwise",
) $ <eq-weight>

The harmonized index of any period and area is the sum of the weights of its detections, $A = sum_i w_i$, expressed in VIIRS-equivalent detections. The same factors apply before 2012, when only MODIS existed. The derived FRP keeps the native VIIRS value, sets co-detected MODIS records to zero, multiplies other MODIS records by $f_p$, and keeps missing values as missing. The index is not a count of independent fires, burned area, or fire energy.

== Statistics Shown in the Application

For the monthly comparison, the baseline of each calendar month is the distribution of that month across all other complete years in the archive; the application reports its 25th, 50th, and 75th percentiles, and each month is labeled above, within, or below that range. A month counts as partial when the archive starts after its third day or ends more than two days before its last day, and as provisional when more than half of its detections come from the near-real-time worker. Partial and provisional months are shown but excluded from the baseline and from the comparison. The annual view reports the raw detections by sensor and the harmonized index for each year, and its median uses complete years only.

== Fire Events

To simplify the map and summarize multi-detection burns, the pipeline groups harmonized detections into spatiotemporal fire events using two DuckDB SQL stages (`01_assign_events.sql` and `02_build_clusters.sql`) executed via the DuckDB CLI. Detections falling in the same $0.02 degree$ (about 2.2 km) spatial cell belong to the same event as long as consecutive detections are no more than 24 hours ($86,400$ s) apart, avoiding artificial splits at UTC midnight. Using DuckDB Spatial, each event computes its centroid (`ST_Centroid`), a perimeter built from the convex hull of its detections (`ST_ConvexHull`) with a $0.0036 degree$ (about 400 m) buffer, total and per-instrument detection counts (MODIS and VIIRS), start and end timestamps, peak and total FRP, and the sum of its harmonized weights. The resulting event tables are bulk-loaded into PostGIS alongside the star schema.

== Verification Approach

The team evaluated the work at three levels. A reproducible test runner builds 810 synthetic detections and runs the four production SQL files unchanged to check boundary cases, platform effects, and missing values. A diagnostic on the real archive measures the harmonized index per MODIS detection, using MODIS as a stable reference across the transition. Finally, every read-only API endpoint was queried against the complete database. The results are reported in Section 6.
