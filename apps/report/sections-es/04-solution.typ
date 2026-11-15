#import "../template.typ": tight, note

= 4. Solución Desarrollada

== Descripción General

PyroTrace es un producto de datos completo, desde la descarga hasta la visualización. Un pipeline por lotes ensambla y armoniza el archivo histórico, un worker lo mantiene actualizado con detecciones en tiempo casi real, una base de datos espacial almacena el resultado, una API lo publica y una aplicación web lo presenta al público. @fig-architecture muestra cómo se conectan los componentes.

#let node(title, body, fill: rgb("#f3f5f7")) = box(
  width: 100%,
  inset: 7pt,
  radius: 4pt,
  stroke: 0.6pt + rgb("#6b7785"),
  fill: fill,
)[#text(weight: "bold", size: 10pt)[#title] \ #text(size: 9pt)[#body]]
#let arrow = align(center + horizon, text(size: 14pt)[→])

#figure(
  tight(grid(
    columns: (1fr, 14pt, 1.15fr, 14pt, 1fr, 14pt, 1fr, 14pt, 1.05fr),
    align: horizon,
    node([NASA FIRMS], [Archivo por país (CSV) y API Area para datos en tiempo casi real], fill: rgb("#fff4dc")),
    arrow,
    node([Pipeline], [Descarga Python, fusión DuckDB, armonización en 4 etapas, esquema estrella]),
    arrow,
    node([PostGIS], [Detecciones, pesos, eventos de incendio y geometrías]),
    arrow,
    node([FastAPI], [Cerca de 40 endpoints REST y alertas en vivo (SSE)]),
    arrow,
    node([App web], [Portada, mapa, calendario, estadísticas, exportación CSV], fill: rgb("#e6f1fb")),
  )),
  caption: [Arquitectura de PyroTrace desde la fuente de datos hasta el usuario],
) <fig-architecture>
#note[Un worker contenedorizado consulta la API Area de FIRMS cada cinco minutos y escribe las nuevas detecciones en PostGIS; NATS JetStream almacena su progreso y distribuye notificaciones en vivo. Todos los servicios se ejecutan como contenedores Podman detrás de un proxy inverso Caddy en una máquina virtual de Microsoft Azure.]

== Componentes

*Pipeline de datos.* Scripts en Python descargan los archivos por país de FIRMS como CSV, registran cada país, año e instrumento en un catálogo SQLite y los convierten a Parquet. Todo el procesamiento posterior está escrito en DuckDB SQL, que procesa el archivo multianual en una sola estación de trabajo sin cargarlo por completo en memoria. El pipeline fusiona MODIS y VIIRS en una sola tabla, ejecuta las cuatro etapas de armonización descritas en la Sección 5, construye un esquema en estrella con identificadores determinísticos, agrupa detecciones en eventos de incendio y carga todo en PostgreSQL con PostGIS.

*Worker en tiempo casi real.* Un servicio independiente se pone al día desde el final del archivo histórico y luego sondea la API Area de FIRMS para MODIS, Suomi-NPP, NOAA-20 y NOAA-21. Asigna cada detección a un país evaluándola contra polígonos nacionales y la inserta sin duplicados. Estos registros recientes se etiquetan como provisionales porque aún no han pasado por el pipeline de armonización.

*API.* Un backend en FastAPI y SQLModel expone cerca de 40 endpoints documentados (OpenAPI) para detecciones, fechas disponibles, actividad diaria, el calendario histórico, estadísticas mensuales y anuales, densidad espacial, detección de anomalías, correlaciones, pronósticos, movimiento de eventos de incendio, contexto meteorológico desde NASA POWER @nasapower, alertas y cuentas de usuario.

*Aplicación web.* Una aplicación de página única (SPA) en Vue 3 presenta los datos en cuatro espacios (@fig-map, @fig-calendar, @fig-stats-monthly y @fig-stats-annual en la Sección 6):
- un mapa interactivo con MapLibre con filtros de fecha, sensor y área dibujada, huellas de eventos de incendio y exportación CSV;
- un calendario histórico de actividad mensual desde 2000 hasta el presente;
- un panel de estadísticas con diez gráficos, incluida la comparación de cada mes con su rango histórico y la serie anual en unidades crudas o armonizadas;
- una portada pública que explica los sensores, el método de armonización y los límites de los datos en lenguaje sencillo.

== Decisiones Relevantes

El equipo conservó cada detección original en lugar de reemplazar el registro con una cuadrícula derivada, de modo que cada valor en pantalla pueda rastrearse hasta FIRMS. La armonización se expresa como un peso por detección, lo que mantiene el método transparente y permite que la interfaz muestre lado a lado los conteos crudos y el índice armonizado. Las estadísticas solo comparan meses completos: los meses parciales y los meses en tiempo casi real se marcan y se excluyen de la línea base histórica, para que los datos incompletos no parezcan actividad alta o baja de incendios. Finalmente, el repositorio es público para que otros equipos puedan auditar, reutilizar y mejorar el método.

== Aporte Distintivo

PyroTrace combina un registro regional armonizado de 25 años, un método de ponderación transparente y verificable, y una interfaz diseñada para personas sin formación geoespacial. No presenta el índice armonizado como un problema resuelto: informa cuánto del efecto de transición entre sensores elimina y cuánto permanece, y pone los datos crudos a disposición de cualquiera que desee probar un enfoque distinto.
