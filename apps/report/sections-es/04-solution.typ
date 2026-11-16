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
    node([FastAPI], [Cerca de 50 endpoints REST y alertas NRT (SSE)]),
    arrow,
    node([App web], [Portada, mapa, calendario, estadísticas, exportación CSV], fill: rgb("#e6f1fb")),
  )),
  caption: [Arquitectura de PyroTrace desde la fuente de datos hasta el usuario],
) <fig-architecture>
#note[Un worker contenedorizado consulta la API Area de FIRMS cada cinco minutos y escribe las nuevas detecciones en PostGIS; NATS JetStream almacena su progreso y distribuye notificaciones en tiempo casi real. Todos los servicios se ejecutan como contenedores Podman detrás de un proxy inverso Caddy en una máquina virtual de Microsoft Azure (`Standard_B2as_v2`, Ubuntu 24.04 LTS, `northcentralus`).]

== Componentes

*Pipeline de datos.* NASA FIRMS solo consolida las detecciones en archivos CSV anuales por país aproximadamente un año en el pasado, por lo que la ingesta se divide en dos partes: archivos históricos y actualizaciones en tiempo casi real mediante la API Area. Para el registro histórico, scripts en Python descargan los archivos por país de FIRMS, registran cada país, año e instrumento en un catálogo SQLite y los convierten a archivos Parquet locales. Toda la transformación y carga posterior se ejecuta mediante la CLI de DuckDB, que procesa el archivo multianual en una sola estación de trabajo sin cargarlo por completo en memoria. El pipeline sigue una secuencia estricta: (1) fusionar los archivos Parquet de MODIS y VIIRS en un solo conjunto unificado, (2) ejecutar las cuatro etapas de armonización en SQL (Sección 5), (3) normalizar el resultado en un esquema en estrella con identificadores determinísticos, (4) cargar masivamente el esquema en estrella en PostgreSQL con PostGIS mediante las extensiones `postgres` y `spatial` de DuckDB, y (5) agrupar las detecciones en eventos de incendio espaciotemporales y cargar esos clústeres en PostGIS.

*Worker en tiempo casi real.* Debido a que los pasos orbitales de los satélites y el procesamiento de datos introducen latencia inherente, los sistemas de monitoreo satelital de incendios en tiempo real estricto no existen; por ello, PyroTrace opera explícitamente en tiempo casi real (NRT). Un servicio independiente cubre la brecha posterior a los años archivados mediante dos estrategias de consulta a la API Area: primero, un proceso de puesta al día consciente de la cuota recupera fechas faltantes en bloques de 5 días (seleccionando fuentes Standard Processing `*_SP` o Near-Real-Time `*_NRT` según disponibilidad de FIRMS); segundo, un ciclo de sondeo NRT consulta la API Area cada cinco minutos para MODIS, Suomi-NPP, NOAA-20 y NOAA-21. Asigna cada detección a un país evaluándola contra polígonos de Natural Earth, la inserta en PostGIS sin duplicados y emite notificaciones a través de NATS JetStream. Estos registros recientes se etiquetan como provisionales hasta que pasan por el pipeline por lotes de armonización.

*API.* Un backend en Python construido con FastAPI y SQLModel —elegido por su velocidad de ejecución, facilidad de desarrollo y documentación OpenAPI automática— expone cerca de 50 endpoints documentados para detecciones, fechas disponibles, actividad diaria, el calendario histórico, estadísticas mensuales y anuales, densidad espacial, detección de anomalías, correlaciones, pronósticos, movimiento de eventos de incendio, contexto meteorológico desde NASA POWER @nasapower, alertas NRT y cuentas de usuario.

*Aplicación web.* Una aplicación de página única (SPA) en Vue 3 —elegida para acelerar el desarrollo de la interfaz y permitir que el equipo se enfocara en el núcleo científico y de ingeniería de datos— consulta directamente los puntos de hotspots y agregados desde la API para filtrar datos, generar estadísticas y renderizar cuatro espacios principales (@fig-map, @fig-calendar, @fig-stats-monthly y @fig-stats-annual en la Sección 6):
- un mapa interactivo con MapLibre con filtros de fecha, sensor y área dibujada, huellas de eventos de incendio y exportación CSV;
- un calendario histórico de actividad mensual desde 2000 hasta el presente;
- un panel de estadísticas con diez gráficos, incluida la comparación de cada mes con su rango histórico y la serie anual en unidades crudas o armonizadas;
- una portada pública que explica los sensores, el método de armonización y los límites de los datos en lenguaje sencillo.

*Despliegue y entorno de ejecución.* La instancia de demostración se ejecuta en una máquina virtual de Microsoft Azure en la región `northcentralus` (perfil de cómputo `Standard_B2as_v2`, Ubuntu 24.04 LTS Server y disco del sistema operativo administrado `Premium_LRS` de 30 GB). Los seis servicios en ejecución (PostGIS, NATS JetStream, backend, worker, frontend y Caddy) se orquestan como contenedores de Podman Compose detrás del proxy inverso con HTTPS automático de Caddy.

== Decisiones Relevantes

El equipo conservó cada detección original en lugar de reemplazar el registro con una cuadrícula derivada, de modo que cada valor en pantalla pueda rastrearse hasta FIRMS. La armonización se expresa como un peso por detección, lo que mantiene el método transparente y permite que la interfaz muestre lado a lado los conteos crudos y el índice armonizado. Las estadísticas solo comparan meses completos: los meses parciales y los meses en tiempo casi real se marcan y se excluyen de la línea base histórica, para que los datos incompletos no parezcan actividad alta o baja de incendios. Finalmente, el repositorio es público para que otros equipos puedan auditar, reutilizar y mejorar el método.

== Aporte Distintivo

PyroTrace combina un registro regional armonizado de 25 años, un método de ponderación transparente y verificable, y una interfaz diseñada para personas sin formación geoespacial. No presenta el índice armonizado como un problema resuelto: informa cuánto del efecto de transición entre sensores elimina y cuánto permanece, y pone los datos crudos a disposición de cualquiera que desee probar un enfoque distinto.
