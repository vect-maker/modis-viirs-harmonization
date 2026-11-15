= 3. Problem and Objectives

== Context

Fire is a recurring part of the dry season in Central America. In the PyroTrace archive, most detections occur between February and May, with a regional peak in April, when agricultural burning, land clearing, and wildfires overlap. Knowing whether a season is unusual requires a long and consistent record, because a single year can only be judged against the years before it.

Two instrument families provide that record. MODIS, on the Terra and Aqua satellites, has observed active fires since November 2000 (Terra) and July 2002 (Aqua) with a nominal pixel of 1 km @firmsarchive @firmsmodis @giglio2016. VIIRS, on Suomi-NPP since 2012 and on NOAA-20 and NOAA-21 since 2018 and 2024, observes with a 375 m pixel and responds to much smaller fires @firmsviirs @schroeder2014. Each detection marks the center of a pixel with a thermal anomaly; it is not an individual fire, and a missing detection can mean no fire, cloud cover, or no satellite overpass @firmsnotes.

== Problem

The two records cannot be added directly. In the Central American archive, raw detections rise from 33,313 in 2011 to 213,676 in 2013, an increase by a factor of 6.41, while MODIS detections alone rise by a factor of only 1.09. Most of the apparent increase is therefore produced by the change of instruments. The same artifact appears whenever a new VIIRS platform enters service. Without harmonization, a student, a researcher, or a fire-prevention team that compares 2005 with 2024 would reach the wrong conclusion.

The guiding question of the project is: _How can MODIS and VIIRS active-fire detections be combined into one record that can be compared across the 2000 to 2025 period, while keeping every original observation traceable?_

== General Objective

To build an open web platform that harmonizes MODIS and VIIRS active-fire records from NASA FIRMS for Central America and lets any user explore, compare, and download fire activity across time and space.

== Specific Objectives

+ Assemble the complete FIRMS archive for the seven Central American countries in a reproducible pipeline.
+ Design and implement a transparent harmonization method that preserves original detections and expresses them in a common unit.
+ Store the harmonized record in a spatial database and expose it through a documented API.
+ Present the record in an interactive map, a historical calendar, and statistics that compare each period with its historical range.
+ Verify the software behavior and evaluate the remaining sensor-transition effect with explicit diagnostics.

== Expected Results

The expected results are a harmonized and documented archive, a public web application that does not require technical knowledge or an account, quantitative evidence of how much harmonization reduces the sensor-transition jump, and a validation plan for the steps that are still pending.
