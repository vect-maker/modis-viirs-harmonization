= Implemented Method

== Inputs and schema alignment

The source is a Silver Parquet table with country, native coordinates, UTC acquisition time, satellite, instrument, brightness temperatures, confidence, FRP, pixel scan/track dimensions, day/night flag, version, and anomaly type.

The fusion SQL renames MODIS brightness and VIIRS I4 to a shared MIR column, and MODIS band 31 and VIIRS I5 to a shared TIR column. Shared names do not make the spectral measurements identical. VIIRS confidence categories are mapped to numeric codes 20, 50, and 90 for storage; these codes are not calibrated detection probabilities or demonstrated equivalents of MODIS confidence. The weighting stages do not currently restrict anomaly type or confidence. A vegetation-fire study must define these filters explicitly @firmsmodis @firmsviirs.

== Local solar time and candidate cells

Let $h$ and $m$ be UTC acquisition hour and minute, and $lambda$ longitude in degrees, positive eastward. The code calculates:
$ h_s = h + m/60 + lambda/15 $ <eq:solar-hour>
$ "LST" = ((h_s " mod " 24) + 24) " mod " 24 $

Here 60 converts minutes to hours; 15 follows from 360 degrees per 24 hours. The result is a longitude-based local mean solar-hour approximation, not civil time or an exact apparent-solar-time solution. The code does not use a solar-time-shifted date for grouping.

#figure(
  table(
    columns: (48%, 52%),
    table.header([Window label], [Solar-hour interval]),
    [Morning], [08:30 to before 12:00],
    [Afternoon], [12:00 to before 16:00],
    [Terra-night label], [20:00 to before 23:30],
    [Dawn/night label], [23:30 to 24:00; 00:00 to before 04:00],
    [Off-cycle], [All remaining hours],
  ),
  caption: [Project-selected windows. Labels describe time bins; they do not identify the satellite or prove simultaneous observation.],
)

With latitude $phi$ and a project-selected angular step $d=0.02 degree$, spatial keys are:
$ y_q = d "round"(phi/d) $ <eq:grid-lat>
$ x_q = d "round"((lambda cos(phi))/d) $ <eq:grid-lon>

The SQL converts latitude to radians before evaluating cosine. A 0.02-degree latitude step is about 2.2 km. The longitude transformation is an approximate indexing rule; it is not a validated equal-distance or equal-area projection. Neighboring detections can fall on opposite cell boundaries. Pixel footprint dimensions are retained but not used in this matching rule.

Acquisition time is truncated to the UTC hour. The key is country, $y_q$, $x_q$, and truncated hour. Thus 18:59 and 19:01 are separated despite being only two minutes apart.

== Co-occurrence and country ratios

For each key $q$, define $M_q$ and $V_q$ as MODIS and VIIRS record counts. A candidate co-occurrence belongs to set $A$ when both counts are positive. This is a bin-level association, not a verified physical duplicate.

For records from 2012 onward, the implementation calculates:
$ r_c = (sum_(q in A) V_q)/(sum_(q in A) M_q) $ <eq:pixel-ratio>
$ r_p = (sum_(q in A) P_(V,q))/(sum_(q in A) P_(M,q)) $ <eq:frp-ratio>

$P_(V,q)$ and $P_(M,q)$ are sums of recorded FRP values, with missing values treated as zero by the current SQL. In addition:
$ r_a = N_(V,a)/N_(M,a), quad r_n = N_(V,n)/N_(M,n) $ <eq:regime-ratios>

The subscript $a$ denotes afternoon totals; $n$ combines both night windows and off-cycle observations. These totals do not require spatially matched observations. All VIIRS platforms are pooled.

The code uses $r_c$ for the morning factor even though $A$ is not restricted to morning observations. Transfer of that relationship to Terra morning observations is an untested assumption.

== Parameter selection

When at least 100 candidate co-occurrence groups exist for a country and the required ratio is defined, factors are computed with:
$ f = "round"(max(l,min(r,u)),2) $ <eq:clamp>

Here $l$ and $u$ are bounds; 2 is the number of decimal places. Undefined ratios or insufficient groups invoke the following fallbacks.

#figure(
  table(
    columns: (18%, 22%, 30%, 30%),
    align: (left, center, center, center),
    table.header([Factor], [Ratio], [Bounds], [Fallback]),
    [$f_m$], [$r_c$], [1 to 10], [2.20],
    [$f_a$], [$r_a$], [1 to 20], [6.12],
    [$f_n$], [$r_n$], [1 to 15], [4.50],
    [$f_p$], [$r_p$], [0.5 to 5], [1.14],
  ),
  caption: [Implemented project parameters. Published empirical derivations of these fallback values were not found.],
)

The threshold 100 is a minimum-sample heuristic; it is not a statistical significance test. No confidence intervals, effective sample sizes, or uncertainty propagation are currently produced. Clipping bounds and two-decimal rounding are engineering choices, not validation results. Unsupported regional or physical interpretations of the fallback values are not asserted.

== Point weights and the monthly index

Let $C_i=1$ when a MODIS record shares its candidate key with at least one VIIRS record, and $C_i=0$ otherwise. The actual weighting rule is:
$ w_i = cases(
  1 & i in V,
  0 & i in M " and " C_i=1,
  f_m & i in M " in morning",
  f_a & i in M " in afternoon",
  f_n & "remaining MODIS"
) $ <eq:weight>

The morning and afternoon branches apply after the co-occurrence branch. Six stored categories distinguish VIIRS-preserved, MODIS-suppressed, unique-morning MODIS, historical MODIS, afternoon-only MODIS, and other MODIS records. The historical label does not introduce a separate historical coefficient: the same time-window factors apply before 2012. The morning category takes precedence over the historical category in the SQL.

For month $t$, the experimental activity index is:
$ A_t = sum_(i in t) w_i $ <eq:activity>

This sum does not create additional point locations. Fractional units are weighted contributions, not independently counted fires, hectares, or a demonstrated reconstruction of missing VIIRS observations.

== Derived FRP and interpretation

With native FRP $P_i$, the derived field follows:
$ P_i^* = cases(
  P_i & i in V,
  0 & i in M " and " C_i=1,
  "round"(P_i f_p,2) & "other MODIS"
) $ <eq:frp-harm>

The actual SQL replaces missing native FRP with zero in this derived field, while retaining the native nullable field. Missing retrievals and measured zero power must remain distinguishable in downstream interpretation.

NASA's Collection 2 guide describes a hybrid retrieval using VIIRS I-band detections and M13 radiance; co-located 375 m detections share fractional FRP from the underlying retrieval @viirsguide2024. A smaller mean FRP per VIIRS record therefore does not by itself imply lower physical fire intensity.

A monthly sum of $P_i^*$ is an observation-summed power statistic. Energy requires time integration, for example $E=integral P(t) dif t$, together with assumptions about the intervals not observed. Neither energy nor burned area is estimated here.

== Current application integration

The export SQL computes the experimental index and derived FRP alongside raw counts. Its processing flag is set by the export command, not by an independent validation gate.

The bundled JSON remains explicitly unharmonized, and the frontend calendar reads raw total or sensor-specific counts. The backend fire-calendar aggregation also uses raw counts and FRP. The weighted workflow is implemented in the pipeline but is not the metric currently displayed by this demonstration calendar.
