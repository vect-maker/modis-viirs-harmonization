#import "template.typ": paper

#show: paper.with(
  title: "PyroTrace: Harmonizing MODIS and VIIRS Active-Fire Records to Explore Fire Activity in Central America",
  authors: (
    "Jose Miranda",
    "Inti Montalvan",
    "Joshua Ordóñez",
    "Fernando Gómez",
    "Geovanny Miranda",
    "Herman Rodríguez",
  ),
  affiliation: "PyroTrace Team, NASA Space Apps Challenge 2026, Managua Local Event, Nicaragua",
  details: (
    "Challenge: MODIS and VIIRS Hot Spots",
    "November 15, 2026",
  ),
  abstract: [
    Active-fire records from NASA's Fire Information for Resource Management System (FIRMS) span two generations of sensors: MODIS since 2000 and VIIRS since 2012. VIIRS detects many small fires that MODIS misses, so pooling both records creates an artificial jump in fire activity when VIIRS begins. PyroTrace is an open-source web platform that assembles 3,621,309 FIRMS detections for the seven countries of Central America (November 2000 to December 2025), harmonizes them with a four-stage, point-preserving weighting method written in DuckDB SQL, and presents the result in an interactive map, a historical calendar, and a statistics panel. Each detection keeps its original attributes and receives a weight that expresses it in VIIRS-equivalent units. Between 2011 and 2013, raw detections increase by a factor of 6.41, whereas the harmonized index increases by a factor of 1.57. A consistency diagnostic that uses MODIS as a stable reference shows a residual step of about 37% after 2012, and a deficit in 2001 and 2002, when only Terra was in orbit. Synthetic tests on 810 constructed records confirm that the current SQL pairs detections across hour and cell boundaries, is invariant to the number of VIIRS platforms, and preserves missing radiative power. PyroTrace therefore reduces, but does not yet eliminate, the sensor-transition discontinuity. It offers transparent, reproducible access to a harmonized fire record for students, researchers, and environmental managers, together with a concrete validation plan.
  ],
  keywords: "NASA FIRMS, MODIS, VIIRS, active fire, harmonization, Central America, open data",
)

#include "sections/01-identification.typ"
#include "sections/02-summary.typ"
#include "sections/03-problem.typ"
#include "sections/04-solution.typ"
#include "sections/05-methodology.typ"
#include "sections/06-results.typ"
#include "sections/07-impact.typ"
#include "sections/08-references.typ"
#include "sections/09-appendices.typ"
