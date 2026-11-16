#import "../template.typ": tight
// Citas iniciales invisibles: APA asigna n.d.-a, n.d.-b, etc. según el orden alfabético del título.
#cite(<firmsarchive>, form: none)#cite(<firmsnotes>, form: none)#cite(<firmsapi>, form: none)#cite(<firmsmodis>, form: none)#cite(<firmsviirs>, form: none)

= 1. Identificación del Proyecto

PyroTrace es la solución desarrollada por el equipo sdlg para el NASA Space Apps Challenge 2026 en el Evento Local de Managua, Nicaragua. Responde al desafío oficial _MODIS and VIIRS Hot Spots_ @spaceappschallenge, que invita a los participantes a hacer utilizables las observaciones de incendios activos de ambas generaciones de sensores como un registro consistente. @tbl-identification resume el proyecto.

#figure(
  table(
    columns: (30%, 70%),
    table.header([Elemento], [Descripción]),
    [Proyecto], [PyroTrace: datos satelitales para comprender la actividad de incendios],
    [Equipo], [sdlg],
    [Integrantes], [Jose Miranda, Inti Montalvan, Joshua Ordóñez, Fernando Gómez, Geovanny Miranda y Herman Rodríguez],
    [Desafío oficial], [MODIS and VIIRS Hot Spots, NASA Space Apps Challenge 2026 @spaceappschallenge],
    [Evento local], [Managua, Nicaragua, 14 y 15 de noviembre de 2026],
    [Solución], [Plataforma web de código abierto que armoniza registros de incendios activos MODIS y VIIRS de NASA FIRMS para los siete países de Centroamérica y los presenta en un mapa, un calendario histórico y un panel de estadísticas],
    [Código fuente], [#link("https://github.com/vect-maker/modis-viirs-harmonization")[github.com/vect-maker/modis-viirs-harmonization] (público, código abierto)],
    [Despliegue], [#link("https://pyrotrace.northcentralus.cloudapp.azure.com/")[pyrotrace.northcentralus.cloudapp.azure.com]; esta instancia puede ir rezagada respecto al repositorio],
    [Video de demostración], [Enlazado desde la página del proyecto del equipo en la plataforma Space Apps],
  ),
  caption: [Identificación del Proyecto],
) <tbl-identification>
