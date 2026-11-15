#import "template.typ": paper

#show: paper.with(
  title: "PyroTrace: An Experimental MODIS-VIIRS Weighting Prototype for Historical Fire Activity Calendars",
  authors: ("PyroTrace project team",),
  date: "14 November 2026 | Prototype technical report",
  abstract: [
    NASA FIRMS active-fire records combine instruments with different pixel sizes, detection responses, and observation schedules. PyroTrace explores a point-preserving weighting workflow for historical fire-activity calendars. Four DuckDB SQL stages retain native attributes, group observations by approximate spatial cells and UTC hour, estimate country-level ratios, and assign experimental weights and derived fire radiative power (FRP). We document the implemented equations, distinguish published product properties from project-selected parameters, and reproduce known limitations on 810 synthetic records. Fixed-bin boundaries and additional VIIRS platforms change the resulting index even when simulated activity is held constant. These checks establish executable behavior and metadata preservation, but do not establish scientific accuracy. The deliverable is a transparent software prototype with an explicit validation plan. Its weighted index must not be interpreted as a count of independent fires, burned area, or a proven sensor-independent trend.
  ],
  keywords: "NASA FIRMS, MODIS, VIIRS, prototype, active fire, weighting, reproducibility",
)

#include "sections/01-introduction.typ"
#include "sections/02-methods.typ"
#include "sections/03-results.typ"
#include "sections/04-discussion.typ"
#include "sections/05-conclusions.typ"
#include "sections/06-appendices.typ"
