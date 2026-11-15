#import "../template.typ": tight, note
#let evidence = json("../validation/results.json")
#let scenario(name) = evidence.scenarios.find(s => s.scenario == name)
#let fmt(value) = {
  let r = calc.round(float(value) * 100) / 100
  let whole = calc.trunc(r)
  let cents = calc.round((r - whole) * 100)
  str(int(whole)) + "." + (if cents < 10 { "0" } else { "" }) + str(int(cents))
}

= 6. Desarrollo, Resultados y Evidencia

== Archivo Ensamblado

El pipeline reunió 3,621,309 detecciones de FIRMS para los siete países de Centroamérica entre el 1 de noviembre de 2000 y el 31 de diciembre de 2025: 700,335 de MODIS (19.3%) y 2,920,974 de VIIRS (80.7%). El worker en tiempo casi real agregó 130,129 detecciones entre el 30 de abril y el 15 de noviembre de 2026, para un total de 3,751,438 registros en la base de datos de producción al 15 de noviembre de 2026. @tbl-countries muestra la distribución por país. Honduras, Guatemala y Nicaragua concentran el 80.9% de todas las detecciones.

#figure(
  table(
    columns: (23%, 18%, 19%, 18%, 22%),
    align: (left, right, right, right, right),
    table.header([País], [Detecciones], [Participación], [MODIS], [Índice armonizado]),
    [Honduras], [1,171,057], [32.3%], [187,527], [1,343,067],
    [Guatemala], [959,372], [26.5%], [256,946], [1,359,213],
    [Nicaragua], [800,480], [22.1%], [119,418], [922,015],
    [Panamá], [242,123], [6.7%], [46,928], [314,020],
    [Belice], [174,838], [4.8%], [33,198], [197,183],
    [Costa Rica], [141,572], [3.9%], [28,361], [171,759],
    [El Salvador], [131,867], [3.6%], [27,957], [174,781],
    [*Total*], [*3,621,309*], [*100.0%*], [*700,335*], [*4,482,037*],
  ),
  caption: [Detecciones Archivadas e Índice Armonizado por País, Noviembre de 2000 a Diciembre de 2025],
) <tbl-countries>
#note[Valores consultados desde la API de producción (`/dashboard/annual-stats`) el 15 de noviembre de 2026. El índice armonizado se expresa en detecciones equivalentes a VIIRS. Se excluyen las detecciones en tiempo casi real de 2026 porque aún no están armonizadas.]

== Detecciones Crudas Frente al Índice Armonizado

@fig-annual compara ambas vistas del registro para cada año completo. En conteos crudos (panel a), la serie salta cuando inicia VIIRS en 2012: las detecciones aumentan en un factor de 6.41 entre 2011 y 2013, mientras que las detecciones MODIS aumentan en apenas 1.09. En el índice armonizado (panel b), el mismo cambio es un factor de 1.57, y los años de ambas eras caen en un rango común alrededor de la mediana anual de 169,000 detecciones equivalentes a VIIRS. La serie armonizada también resalta años de alta actividad, como 2003, 2005, 2013, 2020 y 2024, y años de baja actividad, como 2021 y 2022.

#figure(
  image("../images/annual-raw-vs-harmonized.png", width: 100%),
  caption: [Detecciones Anuales Crudas por Sensor e Índice Armonizado, Centroamérica, 2001 a 2025],
) <fig-annual>
#note[Únicamente años completos. La línea punteada marca el inicio de VIIRS en 2012. Datos de la base de datos de producción de PyroTrace.]

== Diagnóstico de Consistencia

MODIS observó todo el período con los mismos instrumentos, por lo que la razón entre el índice armonizado y el número de detecciones MODIS debería mantenerse aproximadamente constante si la armonización fuera completa. @fig-diagnostic muestra que esta razón es estable de 2003 a 2011 (media 5.40) y nuevamente de 2012 a 2025 (media 7.41), pero el segundo nivel es un 37% más alto. Además, 2001 y 2002 presentan valores mucho más bajos (2.62 y 3.35) porque los datos de Aqua MODIS comienzan en julio de 2002: esos años carecen del paso vespertino, que conlleva el factor más alto @firmsarchive.

#figure(
  image("../images/index-per-modis.png", width: 100%),
  caption: [Índice Armonizado por Detección MODIS, 2001 a 2025],
) <fig-diagnostic>
#note[Las líneas discontinuas muestran la media de cada período. Una razón constante indicaría que el índice armonizado sigue la referencia estable de MODIS a través de la transición de sensores.]

El diagnóstico conduce a dos conclusiones. Primero, la armonización elimina la mayor parte del salto artificial: el registro crudo crece en un factor de 6.41 en la transición, y el registro armonizado en 1.57, cercano al cambio observado solo en MODIS (1.09) más el escalón residual. Segundo, el escalón restante indica que los factores exclusivos de MODIS son demasiado bajos en relación con los pesos de VIIRS después de 2012. Una causa probable es que los factores de tarde y noche se estiman a partir de conteos totales en cada ventana en lugar de observaciones emparejadas. Por lo tanto, las tendencias que cruzan 2012 deben interpretarse teniendo presente este residuo hasta recalibrar los factores (Sección 7). El propio MODIS no es una referencia perfecta, ya que la deriva orbital de las plataformas envejecidas Terra y Aqua puede modificar las horas de observación en años recientes.

== Verificación de Software

El ejecutor de pruebas (`apps/report/validation/verify_prototype.py`) construye 810 detecciones sintéticas y ejecuta sin modificaciones los cuatro archivos SQL de producción con DuckDB #evidence.duckdb_version. Se preservaron los 810 registros nativos, con #evidence.native_mismatches discrepancias en país, coordenadas, hora, instrumento, satélite y FRP nativa. @tbl-synthetic muestra los escenarios. El SQL actual corrige tres comportamientos documentados en la versión previa de este informe: detecciones separadas por dos minutos a través de un límite horario, o por 0.22 m a través del borde de una celda, ahora se emparejan; agregar una segunda plataforma VIIRS ya no duplica el índice ni los factores de calibración; y la FRP faltante permanece faltante en lugar de convertirse en cero.

#figure(
  table(
    columns: (52%, 12%, 18%, 18%),
    align: (left, right, right, right),
    table.header([Escenario sintético], [Registros], [Índice], [Índice previo]),
    [Mismo lugar, 18:31 y 18:33 UTC], [2], [#fmt(scenario("same_hour").activity)], [1.00],
    [Mismo lugar, 18:59 y 19:01 UTC], [2], [#fmt(scenario("hour_boundary").activity)], [7.12],
    [A través del borde de celda, 0.22 m de separación], [2], [#fmt(scenario("spatial_boundary").activity)], [7.12],
    [Un MODIS y dos plataformas VIIRS], [3], [#fmt(scenario("multiple_viirs").activity)], [2.00],
    [100 incendios, una plataforma VIIRS], [300], [#fmt(scenario("one_viirs").activity)], [200.00],
    [Mismos 100 incendios, dos plataformas VIIRS], [500], [#fmt(scenario("two_viirs").activity)], [400.00],
    [Detección VIIRS sin FRP], [1], [#fmt(scenario("null_frp").activity)], [1.00],
  ),
  caption: [Resultados de la Verificación Sintética],
) <tbl-synthetic>
#note[Los valores se leen desde `validation/results.json`, generado por el ejecutor de pruebas. "Índice previo" es el valor reportado para la versión anterior del SQL. Las pruebas sintéticas verifican el comportamiento del software; no miden exactitud frente a incendios reales.]

La API también fue verificada contra la base de datos completa de producción. De 26 solicitudes de solo lectura, 24 devolvieron datos, el endpoint de perfil exigió correctamente una sesión y el endpoint de anomalía espacial rechazó correctamente un parámetro de prueba fuera del rango permitido. La mayoría de las consultas respondieron en menos de 0.3 s; la comparación mensual y las estadísticas anuales tardaron alrededor de 4 y 5 s sobre el archivo completo.

== La Aplicación

Las siguientes figuras muestran la plataforma en ejecución con la base de datos completa. La portada (@fig-landing) explica el proyecto en lenguaje sencillo e incluye el ejemplo de armonización de la Sección 5. El mapa (@fig-map) muestra las 6,012 detecciones del 11 de abril de 2024, con los filtros de fecha, sensor y área y la exportación CSV. El calendario histórico (@fig-calendar) resume cada mes del archivo, y el panel de estadísticas compara cada mes con su rango histórico (@fig-stats-monthly) y muestra la serie anual armonizada (@fig-stats-annual).

#figure(
  image("../images/landing-hero.jpg", width: 100%),
  caption: [Portada de PyroTrace],
) <fig-landing>

#figure(
  image("../images/landing-method.jpg", width: 100%),
  caption: [Explicación del Método de Armonización en la Portada],
) <fig-landing-method>

#figure(
  image("../images/app-map-hotspots.jpg", width: 100%),
  caption: [Mapa Interactivo con las Detecciones del 11 de Abril de 2024],
) <fig-map>

#figure(
  image("../images/app-historical-calendar.png", width: 100%),
  caption: [Calendario Histórico de Detecciones Mensuales, 2000 a 2026],
) <fig-calendar>
#note[El calendario muestra conteos crudos de detecciones. Los meses en gris no tienen datos; 2026 contiene datos en tiempo casi real únicamente desde el 30 de abril.]

#figure(
  image("../images/app-stats-monthly.jpg", width: 100%),
  caption: [Panel de Estadísticas: Actividad Mensual en 2024 Frente a la Línea Base Histórica],
) <fig-stats-monthly>

#figure(
  image("../images/app-stats-annual.jpg", width: 100%),
  caption: [Panel de Estadísticas: Índice Anual Armonizado],
) <fig-stats-annual>
#note[La barra de 2000 (dos meses) y la barra de 2026 (parcial y aún no armonizada) aparecen atenuadas y se excluyen de la mediana.]

== Enlaces

El código fuente, incluidos el pipeline, el SQL, la API, la aplicación web, las pruebas y este informe, está disponible en #link("https://github.com/vect-maker/modis-viirs-harmonization")[github.com/vect-maker/modis-viirs-harmonization]. Una instancia desplegada funciona en #link("https://pyrotrace.northcentralus.cloudapp.azure.com/")[pyrotrace.northcentralus.cloudapp.azure.com], y el video de demostración está enlazado desde la página del proyecto del equipo en la plataforma Space Apps.
