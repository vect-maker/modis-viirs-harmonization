#heading(outlined: false, numbering: none)[Acknowledgments]

PyroTrace uses NASA FIRMS products and open-source software. References document the source products and methodological context; they do not imply NASA endorsement of the project's weighting coefficients.

#heading(outlined: false, numbering: none)[References]

#bibliography("../references.bib", style: "ieee", title: none)

#v(0.6em)
#set heading(numbering: "A.1")
#counter(heading).update(0)

= Reproduction and Data Availability

The source files are in the current project checkout. The four weighting stages are in #raw("apps/pipeline/sql/harmonize/"). No original country-level Parquet files were available for the present review.

A video demonstration of the PyroTrace prototype and dashboard is available at #link("https://youtu.be/WKN75RAhiKw")[https://youtu.be/WKN75RAhiKw].

Run from the repository root in PowerShell:
#raw("cd apps/report\npython validation/verify_prototype.py", block: true)

To refresh the evidence snapshot included in this report, append the flag #raw("--refresh-report-data") to the Python command. Review changed results and their interpretation before doing so.

The runner writes its synthetic workspace and machine-readable outputs beneath the report's ignored output directory. It verifies native-field preservation, exact scenario results, and calibration-factor changes. The committed snapshot records SHA-256 hashes of the four SQL files. If those files change, rerun the checks and review the scientific interpretation before updating the snapshot.

To build the report using the existing Typst installation:
#raw("$pdf = 'output/report.pdf'\ntypst compile --font-path fonts main.typ $pdf", block: true)

The project recipes also provide #raw("just report::build"), #raw("just report::preview"), and #raw("just report::watch") from the repository root in Git Bash. Liberation Serif is bundled with its license; New Computer Modern is supplied by Typst.

#colbreak()

= Source Verification Record

Primary sources were checked on 14 November 2026. Product attributes and collection-specific guidance take precedence over generic descriptions. The bibliography provides stable source URLs and paper DOIs.

The current FIRMS archive page lists NOAA-20 availability from April 2018, while the general VIIRS description page lists January 2020. This report uses the archive page for archive availability.

The 2024 Collection 2 guide is used for VIIRS retrieval interpretation. The 2014 algorithm paper provides historical algorithm context, not evidence that the local archive uses any particular collection. Li et al.'s 2018 study is explicitly a 750 m comparison.

The corrected challenge URL is recorded in the companion methodology documentation. Its title was verified in official indexed metadata; direct page retrieval was unavailable during this revision. It is project context rather than scientific evidence.

No primary source reviewed establishes the values 2.20, 6.12, 4.50, or 1.14 as transferable calibration constants for this prototype. Universal minimum-FRP thresholds and claims of an exact isotropic grid were removed.

= Evidence Status at Delivery

#table(
  columns: (60%, 40%),
  table.header([Evidence item], [Status]),
  [Four SQL stages on synthetic data], [Verified],
  [Native tuples preserved in those checks], [Verified],
  [Original FIRMS archive reprocessing], [Not performed],
  [Cloud/swath exposure correction], [Not implemented],
  [Held-out scientific validation], [Pending],
  [Weighted metric in current calendar], [Not integrated],
)
