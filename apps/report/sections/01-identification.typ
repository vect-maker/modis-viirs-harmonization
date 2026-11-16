#import "../template.typ": tight
// Invisible first citations: APA assigns n.d.-a, n.d.-b, and so on in title order.
#cite(<firmsarchive>, form: none)#cite(<firmsnotes>, form: none)#cite(<firmsapi>, form: none)#cite(<firmsmodis>, form: none)#cite(<firmsviirs>, form: none)

= 1. Project Identification

PyroTrace is the solution developed by the sdlg team for the NASA Space Apps Challenge 2026 at the Managua Local Event in Nicaragua. It responds to the official challenge _MODIS and VIIRS Hot Spots_ @spaceappschallenge, which asks participants to make active-fire observations from the two sensor generations usable as one consistent record. @tbl-identification summarizes the project.

#figure(
  table(
    columns: (30%, 70%),
    table.header([Item], [Description]),
    [Project], [PyroTrace: satellite data to understand fire activity],
    [Team], [sdlg],
    [Members], [Jose Miranda, Inti Montalvan, Joshua Ordóñez, Fernando Gómez, Geovanny Miranda, and Herman Rodríguez],
    [Official challenge], [MODIS and VIIRS Hot Spots, NASA Space Apps Challenge 2026 @spaceappschallenge],
    [Local event], [Managua, Nicaragua, November 14 and 15, 2026],
    [Solution], [Open-source web platform that harmonizes MODIS and VIIRS active-fire records from NASA FIRMS for the seven countries of Central America and presents them in a map, a historical calendar, and a statistics panel],
    [Source code], [#link("https://github.com/vect-maker/modis-viirs-harmonization")[github.com/vect-maker/modis-viirs-harmonization] (public, open source)],
    [Deployment], [#link("https://pyrotrace.northcentralus.cloudapp.azure.com/")[pyrotrace.northcentralus.cloudapp.azure.com]; this instance may lag behind the repository],
    [Demonstration video], [Linked from the team's project page on the Space Apps platform],
  ),
  caption: [Project Identification],
) <tbl-identification>
