# PyroTrace Reports

The technical documentation describes MODIS-VIIRS harmonization in Central America,
with citations, references, and page formatting following APA seventh edition.
Build it with `just report::documentation`.

From `apps/report` in PowerShell:

```powershell
New-Item -ItemType Directory -Path output -Force | Out-Null
typst compile --font-path fonts documentation.typ output/PyroTrace_Harmonization.pdf
Invoke-Item output/PyroTrace_Harmonization.pdf
```

The editable documentation is [../../docs/harmonization.md](../../docs/harmonization.md).
Both the documentation and the technical report are written in English.

## Check and Build from PowerShell

From the repository root:

```powershell
python apps/report/validation/verify_prototype.py
Set-Location apps/report
New-Item -ItemType Directory -Path output -Force | Out-Null
typst compile --font-path fonts main.typ output/report.pdf
Invoke-Item output/report.pdf
```

In Git Bash, use `just report::validate`, `just report::build`, and `just report::watch`.

## Proposal Report Structure

`main.typ` is the NASA Space Apps proposal report. It follows APA 7th edition formatting
(`template.typ`) and the eight sections required by the Managua participant guide, one file
per section in `sections/01-identification.typ` to `sections/08-references.typ`, plus
appendices in `sections/09-appendices.typ`. Figures live in `images/`; the charts were
generated from the production API and the screenshots from the running application on
15 November 2026. The English version comes first; the Spanish version will follow.

## Refresh the Evidence

From the repository root, after reviewing the results:

```powershell
python apps/report/validation/verify_prototype.py --refresh-report-data
```

The `validation/results.json` snapshot records the results, DuckDB version, and SQL
SHA-256 hashes. Detailed files are written to `output/validation`.
The checks execute four SQL stages on 810 synthetic records and verify tuple
preservation, matching across hour and cell boundaries, invariance to the number of VIIRS
platforms, and preservation of missing FRP.
These checks do not establish scientific accuracy.

References are stored in `references.bib`. The fallback values 2.20, 6.12, 4.50,
and 1.14 are provisional. The current calendar displays raw counts.
Generated PDFs are written to `output`, which is ignored by Git.
Liberation Serif is bundled with its license.
