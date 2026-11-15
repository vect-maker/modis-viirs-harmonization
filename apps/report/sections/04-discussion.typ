= Discussion and Validation Plan

== Interpretation of the current result

The defensible result is an experimental observation-weighting workflow with traceable inputs and explicit assumptions. It provides a basis for testing candidate harmonization rules. It does not yet yield a sensor-independent historical series.

The main unresolved issues are fixed-bin boundary effects, pooling multiple platforms without exposure normalization, selection of only co-detected fires for some ratios, transfer to morning and pre-2012 conditions, unverified fallback values, and missing coverage information. Country-level aggregation also mixes seasons and ecosystems.

The prototype keeps all VIIRS records, including separate views of potentially persistent activity. Such observations can be valuable for monitoring, but they must be distinguished from independent fires and normalized appropriately for comparisons over time.

== FRP-specific limitations

A single FRP multiplier cannot be inferred solely from pixel resolution or a difference between mean per-record FRP values. Li et al. document relationships that vary with viewing geometry, ecosystem, season, and aggregation scale @li2018. Their comparison concerns VIIRS 750 m and MODIS 1 km; its coefficients must not be transferred directly to this 375 m workflow.

As an arithmetic check, applying the fallback 1.14 to the reported April 2011 MODIS mean of 32.92 MW gives 37.53 MW. It does not transform that mean into the approximately 10-11 MW means of later mixed-sensor records. A reconstructed population of smaller fires would require a separately defined statistical target and evidence.

== Proposed empirical evaluation

The following is a plan, not a completed experiment.

+ *Specify the target.* Define activity at a fixed spatial support, reference platform, and observation schedule. A provisional afternoon target could use one VIIRS platform and matched Aqua observations during a documented overlap interval. Terra morning observations should remain a separate stratum until transfer is validated.
+ *Control inputs.* Record product collection, science-quality versus NRT provenance, operating periods, anomaly-type policy, and confidence filters. Prefer consistent standard science products for analysis, as recommended by FIRMS @firmsarchive. Retain raw values and quantify the fraction of observations excluded or missing.
+ *Measure observation opportunities.* Use swath and fire-mask/quality information to distinguish observed clear land, clouds, missing acquisitions, and valid no-fire observations. Counts of days with at least one detection are not coverage denominators.
+ *Improve candidate matching.* Use a metric/geodesic distance test, a rolling time tolerance, and available footprint dimensions. Check neighboring spatial and time bins. Select tolerances by sensitivity analysis rather than claiming a universal threshold.
+ *Fit and test separately.* Estimate relationships by platform, season, region/biome, and day/night stratum where sample size permits. Reserve independent years or spatial blocks for evaluation. Simulate historical inference by withholding VIIRS observations from the evaluation set. Co-detection-only fitting must be assessed for selection bias.
+ *Report uncertainty and comparisons.* Compare the adjusted result with raw pooling and sensor-separated baselines. Evaluate bias, MAE, RMSE, temporal residuals, boundary sensitivity, and uncertainty from block resampling. Judge improvement on held-out data and inspect whether any remaining discontinuity tracks platform changes.

For paired target observations $y_j$ and estimates $hat(y)_j$, proposed metrics are:
$ "Bias" = (1/n) sum_(j=1)^n (hat(y)_j-y_j) $
$ "MAE" = (1/n) sum_(j=1)^n abs(hat(y)_j-y_j) $
$ "RMSE" = sqrt((1/n) sum_(j=1)^n (hat(y)_j-y_j)^2) $

No numeric acceptance thresholds are invented here. They should be set before the empirical evaluation, reflect the intended use, and require improvement over relevant baselines without concealing uncertainty.

== Conditions for prototype delivery

The interface can demonstrate raw patterns and explain the experimental weighting workflow. The demonstration should identify raw versus weighted values, disclose the unverified coverage state, and present synthetic examples as synthetic.

The existing export processing flag must not be interpreted as proof of validation. A future integration should distinguish processing status, parameter version, calibration provenance, and scientific validation status. Operational fire-response decisions and long-term climate conclusions are outside the demonstrated evidence.
