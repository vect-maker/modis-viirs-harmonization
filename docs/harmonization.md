# Harmonization of MODIS and VIIRS Observations in Central America

## Introduction

PyroTrace integrates MODIS and VIIRS active-fire records distributed by NASA FIRMS to analyze fire activity in Central America over time. The processing preserves the original observations and adds weights to construct an activity index with VIIRS as the reference.

This integration addresses differences between the sensors. MODIS records thermal anomalies at a nominal resolution of 1 km, whereas the VIIRS product used here has a nominal resolution of 375 m and greater sensitivity to small fires. Their records also differ in acquisition times, pixel dimensions, and observation frequency (NASA FIRMS, n.d.-b, n.d.-c).

The method applies experimental weighting based on spatial and temporal coincidence. Each resulting value is a weighted contribution to the index; a satellite detection represents a pixel with a thermal anomaly and does not necessarily correspond to an independent fire.

## Input Data

The prototype processes observations from Belize, Costa Rica, El Salvador, Guatemala, Honduras, Nicaragua, and Panama. Regional selection takes place when the input files are integrated, while adjustment factors are estimated separately for each country.

The processing uses `hotspots.parquet`, which combines MODIS and VIIRS observations in a common structure. Each record includes country, latitude, longitude, UTC date and time, instrument, satellite platform, brightness temperatures, confidence, fire radiative power (FRP), pixel scan and track dimensions, product version, anomaly type, and day or night classification.

The coordinates identify the center of the observed pixel. FRP represents the radiative power integrated over that pixel, measured in megawatts. The original fields are retained alongside the derived variables (NASA FIRMS, n.d.-b, n.d.-c).

Standardizing field names simplifies storage and querying but does not make the physical properties of the bands equivalent. Similarly, the numerical codes assigned to VIIRS confidence categories are a storage convention, not calibrated probabilities equivalent to MODIS confidence values.

## Observation Processing

### Local Solar Time

Acquisition time is converted to an approximate local mean solar time using geographic longitude:

$$
h_s=h_{\mathrm{UTC}}+\frac{m}{60}+\frac{\lambda}{15}
$$

Here, `h_UTC` is the UTC hour, `m` is the number of minutes, and `lambda` is longitude in degrees, positive eastward. Dividing the minutes by 60 converts them to hours. The divisor 15 corresponds to the Earth's 360-degree rotation over 24 hours.

The result is wrapped to a 24-hour interval:

$$
\mathrm{LST}=((h_s\bmod24)+24)\bmod24
$$

This approximation organizes observations by their local acquisition time. The processing uses the following periods:

**Table 1**

*Acquisition Periods Based on Local Solar Time*

| Period | Solar time interval |
| --- | --- |
| Morning | 08:30 to before 12:00 |
| Afternoon | 12:00 to before 16:00 |
| Night | 20:00 to before 23:30 |
| Overnight | 23:30 to before 04:00 |
| Off-cycle | All remaining times |

These intervals are parameters of the method. Their labels describe time periods and do not replace satellite platform identification.

### Spatial and Temporal Grouping

The coordinates are converted into grouping keys using an angular step of `d = 0.02 degrees`:

$$
y_q=d\,\operatorname{round}\left(\frac{\phi}{d}\right)
$$

$$
x_q=d\,\operatorname{round}\left(\frac{\lambda\cos(\phi)}{d}\right)
$$

Here, `phi` is latitude and `lambda` is longitude. The SQL converts latitude to radians before evaluating the cosine. The latitude step is approximately 2.2 km; the longitude transformation is an indexing approximation, not a constant-distance or equal-area projection.

The timestamp is truncated to the UTC hour. Observations are grouped by country, both spatial keys, and hourly bin. This combination identifies groups containing both instruments.

### Identifying Co-occurrences

The processing counts MODIS and VIIRS records and sums their FRP values within each group. A group is considered a candidate co-occurrence when it contains at least one observation from each instrument.

This association indicates proximity according to the processing keys. Physical correspondence between detections also depends on their footprints and the actual time difference between acquisitions.

### Estimating Country-Level Factors

Factors are calculated using observations from 2012 onward, within the period when both instruments operate. For the set `A` of groups with co-occurring observations, the detection count ratio is:

$$
r_c=\frac{\sum_{q\in A}V_q}{\sum_{q\in A}M_q}
$$

`V_q` and `M_q` are the numbers of VIIRS and MODIS records in each group. The FRP ratio is calculated in the same way:

$$
r_{\mathrm{FRP}}=\frac{\sum_{q\in A}P_{V,q}}{\sum_{q\in A}P_{M,q}}
$$

`P_V,q` and `P_M,q` are the FRP sums for each instrument within the group.

The morning factor uses the count ratio from co-occurrences across all periods. The afternoon and night factors use the totals for their respective periods without requiring spatial matching; the night calculation includes off-cycle observations. The estimation pools the available VIIRS platforms.

When there are at least 100 groups with co-occurring observations and the corresponding ratio is defined, the factor is bounded and rounded to two decimal places:

$$
f=\operatorname{round}\left(\max(l,\min(r,u)),2\right)
$$

The parameters `l` and `u` are the lower and upper bounds. Default values are used when the sample or ratio does not support the calculation.

**Table 2**

*Country-Level Adjustment Parameters*

| Factor | Bounds | Default value |
| --- | --- | ---: |
| Morning | 1 to 10 | 2.20 |
| Afternoon | 1 to 20 | 6.12 |
| Night and other hours | 1 to 15 | 4.50 |
| FRP | 0.5 to 5 | 1.14 |

The threshold of 100 groups, the bounds, and the default values are project configuration choices. The empirical basis for the four default values has not been documented.

### Assigning Weights and Derived FRP

Weights are assigned according to the instrument and the presence of VIIRS in the same group:

**Table 3**

*Weights Assigned to Observations*

| Observation | Assigned weight |
| --- | --- |
| VIIRS | 1 |
| MODIS co-occurring with VIIRS | 0 |
| MODIS without co-occurring VIIRS, morning | Morning factor |
| MODIS without co-occurring VIIRS, afternoon | Afternoon factor |
| Other MODIS records | Night factor |

The same period-specific factors are applied to MODIS observations before 2012. The original record remains stored even when its contribution to the index is zero.

Derived FRP retains the VIIRS value, assigns zero to MODIS records co-occurring with VIIRS, and multiplies FRP for the remaining MODIS records by the FRP-specific factor. Missing values are retained in the original field, although the derived field replaces them with zero.

In the 375 m VIIRS product, FRP retrieval combines the identification of fire-affected pixels with 750 m M13 radiance. Several detected subpixels may share fractions of the same power retrieval (Schroeder et al., 2024). FRP adjustment is therefore handled separately from count adjustment.

## Aggregation and Use of Results

Monthly activity is calculated by summing the observation weights for the period:

$$
A_t=\sum_{i\in t}w_i
$$

`A_t` is the monthly index and `w_i` is the weight of each record. Fractional values represent weighted contributions; the procedure does not generate new fire locations.

The `hotspots_harmonized.parquet` file retains the original variables and adds the acquisition period, harmonization category, weight, and derived FRP. The monthly exporter produces the index alongside the original counts and FRP statistics.

The application currently uses the original counts from the monthly file to display the calendar. The weighted index is generated as a separate measure.

Summing FRP values acquired at different times produces a statistic of sampled power. Estimating energy requires integrating power over time and defining how the intervals between acquisitions are represented.

## Processing Checks

Execution on 810 synthetic records verified preservation of the original tuples evaluated and allowed the effects of the grouping rules to be examined.

**Table 4**

*Results of Checks Using Synthetic Data*

| Evaluated case | Resulting index |
| --- | ---: |
| Same location, acquisitions at 18:31 and 18:33 | 1.00 |
| Same location, acquisitions at 18:59 and 19:01 | 7.12 |
| Points separated by a spatial cell boundary | 7.12 |
| One hundred groups with one VIIRS platform | 200.00 |
| Same simulated activity with two VIIRS platforms | 400.00 |

The change when crossing an hourly or spatial boundary occurs because the MODIS record is no longer associated with VIIRS and receives the default afternoon factor. The two-platform experiment shows that the index also responds to the number of observations included.

The checks can be reproduced from the repository root:

~~~powershell
python apps/report/validation/verify_prototype.py
~~~

Results are saved in `apps/report/output/validation`, together with the DuckDB version and SHA-256 hashes of the four SQL files.

## Methodological Considerations

Comparability between years depends on instrument sensitivity, coverage, and observation opportunities. Adding another platform can increase counts without an equivalent increase in fire activity. Clouds, smoke, and event duration also affect detection (NASA FIRMS, n.d.-a).

Matching within fixed bins introduces boundary effects. Evaluation should consider geographic distance, pixel footprint, and actual time differences. Factors estimated from co-occurrences may favor fires detectable by both instruments; applying them to morning observations and historical periods requires independent evaluation.

Numerical bounds and the minimum sample size stabilize the calculation but do not constitute a test of statistical significance. Validating the index requires comparing estimates with reference observations in years or regions held out for evaluation, while controlling for platform and coverage. FRP must be analyzed separately because its relationship between sensors depends on geometry, ecosystem, and aggregation scale (Li et al., 2018). That comparison concerns 750 m VIIRS observations, so its coefficients cannot be applied directly to the 375 m product.

## References

Li, F., Zhang, X., Kondragunta, S., & Csiszar, I. (2018). Comparison of fire radiative power estimates from VIIRS and MODIS observations. *Journal of Geophysical Research: Atmospheres, 123*(9), 4545-4563. https://doi.org/10.1029/2017JD027823

NASA FIRMS. (n.d.-a). *Fire alert notes*. https://firms.modaps.eosdis.nasa.gov/alerts/notes.php

NASA FIRMS. (n.d.-b). *MODIS fire and thermal anomalies*. https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html

NASA FIRMS. (n.d.-c). *VIIRS fire and thermal anomalies*. https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html

Schroeder, W., Giglio, L., & Hall, J. (2024). *Collection 2 VIIRS 375-m active fire product user's guide* (Version 1.0). NASA Land Science Investigator Processing System. https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.0.pdf
