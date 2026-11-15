#let evidence = json("../validation/results.json")

= Results and Verification

== Reproducible synthetic checks

The checked-in Python runner constructs 810 synthetic records and executes the four unchanged production SQL files with DuckDB #evidence.duckdb_version. It requires no downloaded FIRMS archive and uses only Python's standard library plus the DuckDB CLI. Scenario names occupy the country field solely to isolate experiments.

All 810 native record tuples were preserved, with #evidence.native_mismatches mismatches in country, coordinates, UTC time, instrument, satellite, and native FRP. The remaining constructed attributes are placeholders; this is not a complete quality assessment of FIRMS metadata.

#figure(
  table(
    columns: (66%, 17%, 17%),
    align: (left, right, right),
    table.header([Constructed scenario], [Rows], [Index]),
    [Same location; 18:31 / 18:33], [2], [1.00],
    [Same location; 18:59 / 19:01], [2], [7.12],
    [Spatial boundary; 0.218 m apart], [2], [7.12],
    [MODIS plus two VIIRS platforms], [3], [2.00],
    [100 groups; one VIIRS platform], [300], [200.00],
    [Same activity; two VIIRS platforms], [500], [400.00],
    [VIIRS with missing FRP], [1], [1.00],
  ),
  caption: [Observed software behavior on synthetic inputs. Outputs reproduce known limitations; they do not establish real-world accuracy.],
)

For the first three cases, there are fewer than 100 co-occurrence groups, so isolated afternoon MODIS receives the fallback 6.12. Crossing a time or spatial boundary therefore changes the index from 1 to $6.12+1=7.12$. The extremely short spatial separation is a constructed mathematical boundary case, not a claim about satellite geolocation precision.

In the calibration experiments, each of 100 MODIS records has two VIIRS pixels per platform at the same afternoon observation. Adding a second platform reproduces the same simulated signal. The morning, afternoon, and FRP factors change from 2.00 to 4.00. This demonstrates sensitivity to the number of pooled observing platforms.

The missing-FRP case preserves native null but outputs derived FRP 0.00. This documents the current missing-data policy; it does not establish that the physical radiative power was zero.

== What the checks establish

The software can execute its documented transformations, preserve the tested native fields, and reproduce the reported boundary and sampling effects. Source hashes, machine-readable results, and reproduction instructions accompany the report.

No accuracy, precision, recall, uncertainty interval, or real-data cross-sensor bias reduction has yet been measured for this prototype. The former Argentina benchmark placeholder and references to absent benchmark files have been removed. Backend unit tests and successful PDF compilation are not substituted for scientific validation.
