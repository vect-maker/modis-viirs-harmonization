#import "../template.typ": tight, note
#let evidence = json("../validation/results.json")
#let scenario(name) = evidence.scenarios.find(s => s.scenario == name)
#let fmt(value) = {
  let r = calc.round(float(value) * 100) / 100
  let whole = calc.trunc(r)
  let cents = calc.round((r - whole) * 100)
  str(int(whole)) + "." + (if cents < 10 { "0" } else { "" }) + str(int(cents))
}

= 6. Development, Results, and Evidence

== Assembled Archive

The pipeline assembled 3,621,309 FIRMS detections for the seven countries of Central America between November 1, 2000, and December 31, 2025: 700,335 from MODIS (19.3%) and 2,920,974 from VIIRS (80.7%). The near-real-time worker added 130,129 detections between April 30 and November 15, 2026, for a total of 3,751,438 records in the production database on November 15, 2026. @tbl-countries shows the distribution by country. Honduras, Guatemala, and Nicaragua account for 80.9% of all detections.

#figure(
  table(
    columns: (28%, 18%, 14%, 20%, 20%),
    align: (left, right, right, right, right),
    table.header([Country], [Detections], [Share], [MODIS], [Harmonized index]),
    [Honduras], [1,171,057], [32.3%], [187,527], [1,343,067],
    [Guatemala], [959,372], [26.5%], [256,946], [1,359,213],
    [Nicaragua], [800,480], [22.1%], [119,418], [922,015],
    [Panama], [242,123], [6.7%], [46,928], [314,020],
    [Belize], [174,838], [4.8%], [33,198], [197,183],
    [Costa Rica], [141,572], [3.9%], [28,361], [171,759],
    [El Salvador], [131,867], [3.6%], [27,957], [174,781],
    [*Total*], [*3,621,309*], [*100.0%*], [*700,335*], [*4,482,037*],
  ),
  caption: [Archived Detections and Harmonized Index by Country, November 2000 to December 2025],
) <tbl-countries>
#note[Values queried from the production API (`/dashboard/annual-stats`) on November 15, 2026. The harmonized index is expressed in VIIRS-equivalent detections. Near-real-time detections from 2026 are excluded because they are not yet harmonized.]

== Raw Detections Versus the Harmonized Index

@fig-annual compares the two views of the record for every complete year. In raw counts (panel a), the series jumps when VIIRS begins in 2012: detections rise by a factor of 6.41 between 2011 and 2013, while MODIS detections rise by only 1.09. In the harmonized index (panel b), the same change is a factor of 1.57, and years from both eras fall in a common range around the median year of 169,000 VIIRS-equivalent detections. The harmonized series also highlights years of high activity, such as 2003, 2005, 2013, 2020, and 2024, and years of low activity, such as 2021 and 2022.

#figure(
  image("../images/annual-raw-vs-harmonized.png", width: 100%),
  caption: [Annual Raw Detections by Sensor and Harmonized Index, Central America, 2001 to 2025],
) <fig-annual>
#note[Complete years only. The dotted line marks the start of VIIRS in 2012. Data from the PyroTrace production database.]

== Consistency Diagnostic

MODIS observed the whole period with the same instruments, so the ratio between the harmonized index and the number of MODIS detections should stay roughly constant if the harmonization were complete. @fig-diagnostic shows that this ratio is stable from 2003 to 2011 (mean 5.40) and again from 2012 to 2025 (mean 7.41), but the second level is 37% higher. In addition, 2001 and 2002 have much lower values (2.62 and 3.35) because Aqua MODIS data begin in July 2002: those years lack the afternoon overpass, which carries the largest factor @firmsarchive.

#figure(
  image("../images/index-per-modis.png", width: 100%),
  caption: [Harmonized Index per MODIS Detection, 2001 to 2025],
) <fig-diagnostic>
#note[Dashed lines show the mean of each period. A constant ratio would indicate that the harmonized index follows the stable MODIS reference across the sensor transition.]

The diagnostic leads to two conclusions. First, the harmonization removes most of the artificial jump: the raw record grows by a factor of 6.41 at the transition, and the harmonized record by 1.57, close to the change seen in MODIS alone (1.09) plus the residual step. Second, the remaining step indicates that the MODIS-only factors are too low relative to the VIIRS weights after 2012. A likely cause is that the afternoon and night factors are estimated from total counts in each window rather than from matched observations. Trends that cross 2012 should therefore be interpreted with this residual in mind until the factors are recalibrated (Section 7). MODIS itself is not a perfect reference, since orbital drift of the aging Terra and Aqua platforms can change observation times in recent years.

== Software Verification

The test runner (`apps/report/validation/verify_prototype.py`) builds 810 synthetic detections and runs the four production SQL files unchanged with DuckDB #evidence.duckdb_version. All 810 native records were preserved, with #evidence.native_mismatches mismatches in country, coordinates, time, instrument, satellite, and native FRP. @tbl-synthetic shows the scenarios. The current SQL corrects three behaviors documented in the previous version of this report: detections two minutes apart across an hour boundary, or 0.22 m apart across a cell edge, are now matched; adding a second VIIRS platform no longer doubles the index or the calibration factors; and missing FRP stays missing instead of becoming zero.

#figure(
  table(
    columns: (52%, 12%, 18%, 18%),
    align: (left, right, right, right),
    table.header([Synthetic scenario], [Records], [Index], [Previous index]),
    [Same place, 18:31 and 18:33 UTC], [2], [#fmt(scenario("same_hour").activity)], [1.00],
    [Same place, 18:59 and 19:01 UTC], [2], [#fmt(scenario("hour_boundary").activity)], [7.12],
    [Across a cell edge, 0.22 m apart], [2], [#fmt(scenario("spatial_boundary").activity)], [7.12],
    [One MODIS and two VIIRS platforms], [3], [#fmt(scenario("multiple_viirs").activity)], [2.00],
    [100 fires, one VIIRS platform], [300], [#fmt(scenario("one_viirs").activity)], [200.00],
    [Same 100 fires, two VIIRS platforms], [500], [#fmt(scenario("two_viirs").activity)], [400.00],
    [VIIRS detection without FRP], [1], [#fmt(scenario("null_frp").activity)], [1.00],
  ),
  caption: [Results of the Synthetic Verification],
) <tbl-synthetic>
#note[Values are read from `validation/results.json`, generated by the test runner. "Previous index" is the value reported for the earlier SQL version. Synthetic tests verify software behavior; they do not measure accuracy against real fires.]

The API was also verified against the complete production database. Of 26 read-only requests, 24 returned data, the profile endpoint correctly required a session, and the spatial-anomaly endpoint correctly rejected a test parameter outside its allowed range. Most queries answered in less than 0.3 s; the monthly comparison and the annual statistics took about 4 and 5 s over the full archive.

== The Application

The following figures show the platform running with the complete database. The landing page (@fig-landing) explains the project in plain language and includes the harmonization example from Section 5. The map (@fig-map) displays the 6,012 detections of April 11, 2024, with the date, sensor, and area filters and the CSV export. The historical calendar (@fig-calendar) summarizes every month of the archive, and the statistics panel compares each month with its historical range (@fig-stats-monthly) and shows the annual harmonized series (@fig-stats-annual).

#figure(
  image("../images/landing-hero.jpg", width: 100%),
  caption: [PyroTrace Landing Page],
) <fig-landing>

#figure(
  image("../images/landing-method.jpg", width: 100%),
  caption: [Explanation of the Harmonization Method on the Landing Page],
) <fig-landing-method>

#figure(
  image("../images/app-map-hotspots.jpg", width: 100%),
  caption: [Interactive Map With the Detections of April 11, 2024],
) <fig-map>

#figure(
  image("../images/app-historical-calendar.png", width: 100%),
  caption: [Historical Calendar of Monthly Detections, 2000 to 2026],
) <fig-calendar>
#note[The calendar shows raw detection counts. Gray months have no data; 2026 contains near-real-time data only from April 30.]

#figure(
  image("../images/app-stats-monthly.jpg", width: 100%),
  caption: [Statistics Panel: Monthly Activity in 2024 Against the Historical Baseline],
) <fig-stats-monthly>

#figure(
  image("../images/app-stats-annual.jpg", width: 100%),
  caption: [Statistics Panel: Annual Harmonized Index],
) <fig-stats-annual>
#note[The 2000 bar (two months) and the 2026 bar (partial and not yet harmonized) are faded and excluded from the median.]

== Links

The source code, including the pipeline, the SQL, the API, the web application, the tests, and this report, is available at #link("https://github.com/vect-maker/modis-viirs-harmonization")[github.com/vect-maker/modis-viirs-harmonization]. A deployed instance runs at #link("https://pyrotrace.northcentralus.cloudapp.azure.com/")[pyrotrace.northcentralus.cloudapp.azure.com], and the demonstration video is linked from the team's project page on the Space Apps platform.
