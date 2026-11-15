= Conclusions

PyroTrace implements a four-stage, point-preserving MODIS-VIIRS weighting prototype and a historical calendar demonstration (#link("https://youtu.be/WKN75RAhiKw")[video demonstration]). This revision improves its evidentiary basis by citing primary product documentation, describing the actual SQL equations, and distinguishing project parameters from published sensor properties.

Execution on 810 synthetic records reproduced both expected transformations and important limitations. The software preserved the tested native values, but its weighted index changed with bin boundaries and the number of pooled VIIRS platforms.

Accordingly, the current deliverable is an auditable experimental prototype, not a validated harmonized fire record. The four fallback factors, morning transfer, coverage treatment, and cross-era comparability require empirical evaluation.

The next substantive milestone is a platform-controlled, held-out comparison using original FIRMS observations and coverage metadata. That evaluation should precede claims of sensor-independent trends, reconstructed historical fire counts, energy estimates, or operational accuracy.
