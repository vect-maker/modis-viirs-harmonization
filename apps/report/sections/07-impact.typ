= 7. Impact and Outlook

== Beneficiaries

PyroTrace is designed for four groups:
- people interested in fire, the environment, and satellite observation, who can explore the record without geospatial training;
- students, teachers, and researchers, who need a documented regional record and the raw data in CSV for classes and analysis;
- environmental analysts and protected-area managers, who need to recognize patterns, anomalies, and critical seasons in their territory;
- firefighters and prevention teams, who can compare the current season with previous years when planning resources.

== Applications and Scope

The platform supports seasonal comparisons ("Is this April unusual?"), the identification of areas with recurring activity, teaching about satellite sensors and their limits, and the preparation of historical baselines for research. Its current scope is the seven countries of Central America from November 2000 to the present. Because the pipeline is driven by FIRMS country files and a configurable bounding box, the same method can be extended to other countries without changing the SQL.

The platform does not replace operational fire alerts or ground reports, and the harmonized index should not be read as a count of fires, burned area, or emissions. These limits are stated in the interface and in this report.

== Sustainability

Access will remain free and without registration. The team plans to sustain the platform through voluntary donations, innovation and environmental research funds, technology sponsorships, and cooperation agreements with universities and organizations. Costs are controlled by precomputing historical aggregates and storing data locally, which avoids repeated downloads and processing. Potential partners include NASA FIRMS and Earthdata as data providers, universities and specialists as scientific collaborators, environmental authorities and conservation organizations to validate user needs, and technology providers for infrastructure.

== Limitations and Future Work

The diagnostic in Section 6.3 sets the priorities for the next version:
+ *Recalibrate the MODIS-only factors* with matched observations in each overpass window, and test the result by checking that the index per MODIS detection stays constant across 2012.
+ *Correct the early years* by normalizing MODIS by the number of active MODIS platforms, as the method already does for VIIRS, so that 2001 and 2002 become comparable.
+ *Harmonize the near-real-time data* through the same SQL stages, so that recent months can join the historical comparisons.
+ *Account for observation opportunities* with cloud and overpass information, so that a missing detection can be distinguished from a missed observation @firmsnotes.
+ *Evaluate on held-out data* by withholding VIIRS observations from years after 2012 and measuring bias, mean absolute error, and root-mean-square error of the reconstructed index, with uncertainty from block resampling.
+ *Publish the Spanish version of this report and of the interface*, and add tutorials for teachers and students.
