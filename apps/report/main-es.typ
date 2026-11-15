#import "template.typ": paper

#show: paper.with(
  title: "PyroTrace: Armonización de registros de incendios activos MODIS y VIIRS para explorar la actividad de incendios en Centroamérica",
  authors: (
    "Jose Miranda",
    "Inti Montalvan",
    "Joshua Ordóñez",
    "Fernando Gómez",
    "Geovanny Miranda",
    "Herman Rodríguez",
  ),
  affiliation: "Equipo PyroTrace, NASA Space Apps Challenge 2026, Evento Local Managua, Nicaragua",
  details: (
    "Desafío: MODIS and VIIRS Hot Spots",
    "15 de noviembre de 2026",
  ),
  lang: "es",
  abstract: [
    Los registros de incendios activos del sistema Fire Information for Resource Management System (FIRMS) de la NASA abarcan dos generaciones de sensores: MODIS desde 2000 y VIIRS desde 2012. VIIRS detecta muchos incendios pequeños que MODIS no alcanza a registrar, por lo que unir ambos registros directamente genera un salto artificial en la actividad de incendios cuando inicia VIIRS. PyroTrace es una plataforma web de código abierto que reúne 3,621,309 detecciones de FIRMS para los siete países de Centroamérica (noviembre de 2000 a diciembre de 2025), las armoniza mediante un método de ponderación en cuatro etapas que preserva los puntos originales escrito en DuckDB SQL, y presenta el resultado en un mapa interactivo, un calendario histórico y un panel de estadísticas. Cada detección conserva sus atributos originales y recibe un peso que la expresa en unidades equivalentes a VIIRS. Entre 2011 y 2013, las detecciones crudas aumentan en un factor de 6.41, mientras que el índice armonizado aumenta en un factor de 1.57. Un diagnóstico de consistencia que utiliza MODIS como referencia estable muestra un escalón residual de alrededor del 37% después de 2012, y un déficit en 2001 y 2002, cuando solo Terra estaba en órbita. Pruebas sintéticas sobre 810 registros construidos confirman que el SQL actual empareja detecciones a través de límites de hora y de celda, es invariante al número de plataformas VIIRS y preserva la potencia radiativa faltante. Por lo tanto, PyroTrace reduce, pero aún no elimina, la discontinuidad por transición entre sensores. Ofrece acceso transparente y reproducible a un registro armonizado de incendios para estudiantes, investigadores y gestores ambientales, junto con un plan concreto de validación.
  ],
  keywords: "NASA FIRMS, MODIS, VIIRS, incendios activos, armonización, Centroamérica, datos abiertos",
)

#include "sections-es/01-identification.typ"
#include "sections-es/02-summary.typ"
#include "sections-es/03-problem.typ"
#include "sections-es/04-solution.typ"
#include "sections-es/05-methodology.typ"
#include "sections-es/06-results.typ"
#include "sections-es/07-impact.typ"
#include "sections-es/08-references.typ"
#include "sections-es/09-appendices.typ"
