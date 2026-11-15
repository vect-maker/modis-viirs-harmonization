= Método Implementado

== Pipeline de datos y pila tecnológica

PyroTrace separa la adquisición de datos, la transformación analítica, el almacenamiento espacial y la orquestación de tareas en capas diferenciadas para que los archivos satelitales multianuales puedan procesarse de manera confiable en una sola estación de trabajo sin agotar la memoria.

Los archivos crudos de incendios activos se obtienen desde la API de NASA FIRMS como archivos CSV. Scripts en Python (`sync_meta.py`, `transform_meta.py`, `fetcher.py` y `sync_local_files.py`) gestionan los presupuestos de transacciones de la API, registran qué archivos por país, año e instrumento existen en disco dentro de un catálogo local SQLite (`data/pipeline.db`) y escriben los registros descargados de forma atómica como archivos columnares Parquet (`data/raw/<instrument>/<year>/<country>.parquet`). Python se utiliza estrictamente para la comunicación con la API, el seguimiento de estado y la conversión de CSV a Parquet, en lugar de procesamiento analítico sobre todo el archivo.

Procesar archivos continentales o globales multianuales en una sola máquina con herramientas en memoria como pandas conlleva el riesgo de agotar la RAM. En su lugar, toda la fusión de conjuntos de datos (`fuse_datasets.sql`), la armonización en cuatro etapas (`sql/harmonize/`), la normalización en esquema en estrella (`normalize_star_schema.sql`) y el agrupamiento de eventos de incendio (`sql/clusters/`) están escritos como consultas SQL puras en DuckDB. DuckDB ejecuta operaciones vectorizadas fuera de núcleo (out-of-core) directamente sobre archivos Parquet locales con memoria acotada y volcado a disco, y lee el catálogo SQLite mediante `sqlite_scan`. Utilizando las extensiones `postgres` y `spatial` de DuckDB, el mismo motor también realiza la carga masiva de las tablas Gold en Parquet y las geometrías agrupadas directamente en la base de datos PostgreSQL de producción (`load_star_schema.sql`, `load_clusters.sql`).

Las tablas procesadas del esquema en estrella (`dim_country`, `dim_platform`, `fact_hotspots`) y las huellas de eventos de incendio se almacenan en PostgreSQL con la extensión PostGIS (`setup.sql`, `schema.sql`), proporcionando geometrías espaciales indexadas (`ST_Point` y polígonos de huella) para el backend en FastAPI y el mapa interactivo. Los comandos comunes del proyecto se codifican en archivos modulares de recetas `justfile` (un `justfile` raíz que delega a `apps/pipeline/justfile`, `apps/report/justfile` y módulos hermanos de servicio), estandarizando la configuración del entorno, la descarga desde la API, la ejecución SQL en DuckDB, la carga en PostGIS y la compilación del informe en objetivos de un solo comando.

#figure(
  {
    set par(justify: false)
    table(
      columns: (27%, 24%, 49%),
      align: (left, left, left),
      table.header([Capa], [Herramienta], [Rol y criterio de selección]),
      [Ingesta y seguimiento], [Python, SQLite, Parquet], [Descarga CSVs de la API NASA FIRMS, rastrea archivos en disco y almacena archivos crudos columnares.],
      [Transformación y carga], [DuckDB SQL], [Reemplaza pandas en memoria por transformaciones SQL out-of-core en una sola máquina y carga directa a PostgreSQL.],
      [Almacén de producción], [PostgreSQL + PostGIS], [Sirve registros normalizados del esquema en estrella y geometrías espaciales al backend de la aplicación.],
      [API del backend], [FastAPI + SQLModel], [Provee desarrollo rápido de endpoints REST y SSE con modelos compartidos de Pydantic y SQLAlchemy.],
      [SPA del frontend], [Vue 3, Pinia, VueUse], [Entrega una SPA en modo historial con almacenes centralizados en Pinia, composables VueUse y MapLibre GL.],
      [Bus de estado y eventos], [NATS JetStream], [Persiste cursores KV del worker y presencia SSE, y enruta eventos en tiempo real entre réplicas de la API.],
      [Contenedores y proxy], [Podman Compose, Caddy], [Provee orquestación de contenedores sin demonio y sin privilegios root, e ingreso mediante proxy inverso TLS.],
      [Ejecutor de tareas], [`justfile`], [Centraliza comandos comunes del pipeline, base de datos e informes como recetas versionadas.],
    )
  },
  caption: [Pila principal de ETL y orquestación utilizada por el pipeline de PyroTrace.],
)

== Fases de transformación y carga

Una vez registrados en disco los archivos Parquet crudos por país, año e instrumento, el pipeline de DuckDB los procesa a través de cuatro etapas secuenciales, cada una expuesta como una receta de `justfile`:

1. *Fusionar conjunto de datos (`fuse_datasets.sql`, `just pipeline::fuse-data`):* Lee el catálogo de archivos SQLite (`sqlite_scan`) para los archivos Parquet crudos completados (acotados a Centroamérica por defecto, o todos los países globalmente) y unifica los registros MODIS y VIIRS en una única tabla Silver comprimida con ZSTD (`data/processed/hotspots.parquet`). Esta etapa analiza marcas de tiempo, alinea los nombres de columnas de brillo MIR y TIR, expande códigos de satélite VIIRS y mapea la confianza categórica de VIIRS (`l`, `n`, `h`) a códigos numéricos de almacenamiento (`20`, `50`, `90`).
2. *Armonizar datos (`sql/harmonize/01` a `04`, `just pipeline::harmonize-data`):* Ejecuta cuatro scripts SQL secuenciales sobre la tabla Silver para calcular horas solares locales y claves espacio-horarias (`01_base_points.sql`), detectar coocurrencias candidatas MODIS-VIIRS (`02_quadrant_hourly.sql`), derivar razones por país y factores de respaldo (`03_country_calibration.sql`), y asignar categorías por punto, pesos experimentales y FRP derivada (`04_harmonize_points.sql`), generando `data/processed/hotspots_harmonized.parquet`.
3. *Normalizar datos (`normalize_star_schema.sql`, `just pipeline::normalize-data`):* Convierte la tabla armonizada en un esquema en estrella Gold bajo `data/processed/star/` (`dim_country.parquet`, `dim_platform.parquet` y `fact_hotspots.parquet` deduplicado). Se calculan claves determinísticas RFC 4122 UUIDv5 (`firms_uuid5`) a partir de atributos naturales para que las ejecuciones repetidas del pipeline sigan siendo idempotentes.
4. *Cargar datos (`load_star_schema.sql`, `just pipeline::db-load`):* Utiliza las extensiones `postgres` y `spatial` de DuckDB para adjuntar la base de datos PostgreSQL/PostGIS de producción (`$DATABASE_URL`), truncar las tablas existentes y transmitir en bloque los archivos Parquet del esquema en estrella Gold mientras construye geometrías `ST_Point`. Una etapa complementaria de agrupamiento (`just pipeline::cluster-events`) agrupa los puntos de calor en huellas de eventos de incendio y los carga en PostGIS para su visualización en el mapa.

#figure(
  {
    set par(justify: false)
    table(
      columns: (28%, 72%),
      align: (left, left),
      table.header([Fase y receta], [Salida principal y propósito]),
      [1. Fusión\ (`fuse-data`)], [Produce la tabla Silver unificada `hotspots.parquet` a partir de archivos Parquet crudos de MODIS y VIIRS.],
      [2. Armonización\ (`harmonize-data`)], [Produce `hotspots_harmonized.parquet` con pesos, categorías y FRP derivada.],
      [3. Normalización\ (`normalize-data`)], [Divide en archivos Parquet del esquema en estrella Gold (`dim_country`, `dim_platform`, `fact_hotspots`) con claves UUIDv5.],
      [4. Carga\ (`db-load`)], [Inserta masivamente las tablas Gold en PostgreSQL/PostGIS con geometrías `ST_Point`.],
    )
  },
  caption: [Fases secuenciales de transformación y carga en DuckDB SQL.],
)

== Worker de ingesta en vivo desde la API

Junto al pipeline por lotes sobre el archivo histórico, un worker en Python contenedorizado (`apps/worker`) se conecta directamente a la API Area CSV en vivo de NASA FIRMS para cerrar brechas del archivo histórico y mantener actualizaciones en tiempo casi real (NRT) en PostgreSQL/PostGIS. Su ciclo de vida se desarrolla en dos fases, respaldado por resolución de países basada en polígonos.

En la primera fase, un proceso de puesta al día consciente de la cuota (`catchup.py`) se reanuda desde un cursor KV persistido en NATS JetStream (`catchup.cursor`), o desde el `acq_datetime` más reciente almacenado en `fact_hotspots` cuando no existe cursor. Consulta un cuadro delimitador regional (`FIRMS_AREA_BBOX`, por defecto Centroamérica) en lotes de 5 días a través de MODIS, Suomi-NPP, NOAA-20 y NOAA-21, seleccionando fuentes de procesamiento estándar (`_SP`) o en tiempo casi real (`_NRT`) según la disponibilidad de datos de FIRMS. Antes de cada solicitud, el worker verifica el presupuesto de transacciones de `MAP_KEY` (`FIRMS_QUOTA_RESERVE = 50`). Cuando se acerca al límite de cuota u ocurre una respuesta HTTP 429, pausa durante `CATCHUP_COOLDOWN_SECONDS` (610 s por defecto) y se reanuda desde el cursor guardado hasta alcanzar la fecha UTC actual.

Una vez completada la puesta al día, el worker pasa al sondeo en tiempo casi real (`nrt_sync.py`), consultando las cuatro fuentes NRT cada `NRT_POLL_INTERVAL_SECONDS` (300 s por defecto) con una ventana deslizante de 2 días (`day_range = 2`) para capturar los pasos satelitales recién disponibles. Dado que las respuestas de la API Area devuelven detecciones dentro de un cuadro rectangular sin etiquetas de país, `country_resolver.py` evalúa cada coordenada contra los polígonos de `central_america.geojson` usando un índice espacial `STRtree` de Shapely y descarta los puntos fuera de los siete países objetivo. Las detecciones válidas reciben la misma clave determinística `firms_uuid5` en `hotspot_writer.py` y se insertan de forma idempotente (`ON CONFLICT DO NOTHING`) en el esquema en estrella de PostGIS.

== Servicio backend y coordinación con NATS

El backend de la aplicación (`apps/backend`) está implementado con FastAPI y SQLModel. Esta pila se seleccionó por su rapidez para prototipar, la generación automática de esquemas OpenAPI y la unificación de validación Pydantic y mapeo ORM SQLAlchemy sobre el esquema en estrella de PostGIS. Con mayor tiempo de ingeniería, las rutas críticas de rendimiento de la API podrían migrarse de Python a un framework compilado de sistemas como Rust con Axum manteniendo el mismo esquema PostgreSQL/PostGIS y los contratos de mensajería.

NATS actúa tanto como almacén Clave-Valor (KV) de JetStream como bus de eventos pub-sub entre los servicios en ejecución. Como almacén KV, el worker de ingesta persiste su estado operativo en el bucket `worker_state` (`catchup.cursor`, `catchup.completed`, `catchup.last_progress` y `nrt.last_sync`), mientras que las réplicas de FastAPI registran los flujos activos de clientes Server-Sent Events (SSE) en el bucket `sse_presence` (con un TTL predeterminado de 45 s). Como bus de eventos, `NatsService` publica notificaciones globales en `firms.sse.broadcast` y enruta sobres dirigidos a usuarios o inquilinos específicos hacia réplicas concretas del backend mediante `firms.sse.instance.<instance_id>`, recurriendo a entrega local en memoria cuando `NATS_URL` no está configurado. Mientras tanto, los puntos de calor recién ingeridos escritos por el worker en PostgreSQL/PostGIS quedan disponibles de inmediato para los repositorios de FastAPI.

== Portal web SPA

El portal orientado al usuario (`apps/frontend`) está construido como una Single-Page Application (SPA) en Vue 3 con TypeScript, Vite, MapLibre GL para el renderizado geoespacial interactivo y ECharts para visualizaciones estadísticas. La navegación es gestionada por `vue-router` en modo historial HTML5 (`createWebHistory` en navegador, con respaldo `createMemoryHistory` fuera del navegador), ofreciendo URLs limpias en vistas con carga diferida (`/`, `/dashboard`, `/auth/login`, `/auth/register` y `/profile`) junto con guardias de ruta `beforeEach` para inicialización de sesión y control de acceso.

El estado de la aplicación está centralizado en almacenes Pinia (`apps/frontend/src/stores/`) particionados en siete módulos de dominio (`auth`, `calendar`, `clusters`, `feedback`, `filters`, `hotspots` y `notifications`). Las utilidades reutilizables de navegador y reactividad se implementan mediante composables de `@vueuse/core`, incluyendo `createFetch` para solicitudes tipadas a la API (`useApiFetch.ts`), `useEventSource` para flujos SSE en vivo (`useNotificationStream.ts`), `useObjectUrl` para exportaciones CSV en el cliente (`useHotspotCsvDownload.ts`), y `useResizeObserver`, `useIntersectionObserver`, `useMediaQuery` y `useGeolocation` para interacciones responsivas del mapa y del tablero.

== Orquestación de contenedores y despliegue en la nube

Todos los servicios en ejecución se construyen y orquestan usando Podman con Compose (`compose.yml` y `debug.compose.yml`), invocados mediante recetas del `justfile` raíz como `up`, `up-build` y `up-debug`. Podman fue seleccionado por su compatibilidad entre sistemas, su modelo de ejecución sin root por defecto y su arquitectura sin demonio, que evita mantener un proceso persistente en segundo plano con privilegios de administrador.

La topología Compose de producción coordina seis contenedores: `db` (`postgis/postgis:17-3.5`), `nats` (`nats:2.10-alpine` con JetStream habilitado), `backend` (`apps/backend/prod.containerfile`), `worker` (`apps/worker/prod.containerfile`), `frontend` (`apps/frontend/prod.containerfile`) y `caddy` (`caddy:2.9-alpine`). Caddy actúa como el único punto de ingreso público (`Caddyfile`), exponiendo únicamente los puertos 80 y 443. Las solicitudes HTTP en el puerto 80 se redirigen automáticamente a HTTPS en el puerto 443 con certificados TLS gestionados, mientras que las rutas `/api/*` se envían por proxy inverso a `backend:8080` y las demás rutas son servidas por `frontend:8080`.

La pila de contenedores se despliega en una máquina virtual de Microsoft Azure en la región `northcentralus` con un perfil de instancia `Standard_B2as_v2`. El host ejecuta Ubuntu 24.04 LTS Server (`ubuntu-24_04-lts`) respaldado por un disco administrado del sistema operativo `Premium_LRS` de 30 GB, con la autenticación por contraseña deshabilitada en favor del acceso mediante llaves SSH.

== Fuentes de datos y atribución de APIs

Todos los conjuntos de datos externos consumidos por el pipeline, el worker en vivo, el backend y el mapa interactivo están anclados a endpoints explícitos en el código fuente. Las detecciones históricas archivadas se obtienen del host de NASA FIRMS (`https://firms.modaps.eosdis.nasa.gov`) usando el índice resumen anual por país (`data/country/yearly_summary_files.txt`) y el endpoint CSV de disponibilidad de datos (`/api/data_availability/csv`) en `apps/pipeline` @firmsapi @firmsarchive. Las detecciones en tiempo casi real (NRT) y de puesta al día se consultan al mismo host de NASA FIRMS mediante el endpoint Area CSV (`/api/area/csv`) en `apps/worker` @firmsapi.

Para el mapa interactivo y el contexto ambiental, `FireMap.vue` renderiza teselas de imágenes satelitales del servicio Esri ArcGIS World Imagery (`server.arcgisonline.com/.../World_Imagery/MapServer`) @esriworldimagery, los polígonos de límites nacionales provienen de Natural Earth @naturalearth, y el contexto meteorológico diario es obtenido por `WeatherDataClient.py` desde la API NASA POWER Daily Point (`power.larc.nasa.gov/api/temporal/daily/point`) @nasapower.

#figure(
  {
    set par(justify: false)
    table(
      columns: (28%, 32%, 40%),
      align: (left, left, left),
      table.header([Caso de uso], [Fuente y endpoint], [Componente]),
      [Datos históricos de incendios], [Resúmenes por país y CSVs de disponibilidad de NASA FIRMS @firmsapi @firmsarchive], [`apps/pipeline` (`sync_meta.py`, `fetcher.py`)],
      [Datos en tiempo casi real], [API Area CSV de NASA FIRMS (`/api/area/csv`) @firmsapi], [`apps/worker` (`firms_client.py`, `nrt_sync.py`)],
      [Imágenes del mapa], [Teselas `MapServer` de Esri ArcGIS World Imagery @esriworldimagery], [`apps/frontend` (`FireMap.vue`)],
      [Polígonos de países], [Límites vectoriales de Natural Earth @naturalearth], [`apps/frontend`, `apps/worker`],
      [Contexto meteorológico], [API NASA POWER Daily Point @nasapower], [`apps/backend` (`WeatherDataClient.py`)],
    )
  },
  caption: [Fuentes de datos externas y endpoints de API citados por el sistema PyroTrace.],
)

== Entradas y alineación de esquema

La fuente es una tabla Silver en Parquet con país, coordenadas nativas, hora de adquisición UTC, satélite, instrumento, temperaturas de brillo, confianza, FRP, dimensiones de escaneo/pista del píxel, indicador día/noche, versión y tipo de anomalía.

El SQL de fusión renombra el brillo de MODIS y VIIRS I4 a una columna compartida MIR, y la banda 31 de MODIS y VIIRS I5 a una columna compartida TIR. Los nombres compartidos no hacen que las mediciones espectrales sean idénticas. Las categorías de confianza de VIIRS se mapean a códigos numéricos 20, 50 y 90 para su almacenamiento; estos códigos no son probabilidades calibradas de detección ni equivalentes demostrados de la confianza de MODIS. Las etapas de ponderación actualmente no restringen el tipo de anomalía ni la confianza. Un estudio sobre incendios de vegetación debe definir estos filtros explícitamente @firmsmodis @firmsviirs.

== Tiempo solar local y celdas candidatas

Sean $h$ y $m$ la hora y minuto de adquisición UTC, y $lambda$ la longitud en grados, positiva hacia el este. El código calcula:
$ h_s = h + m/60 + lambda/15 $ <eq:solar-hour>
$ "LST" = ((h_s " mod " 24) + 24) " mod " 24 $

Aquí 60 convierte minutos a horas; 15 resulta de 360 grados por 24 horas. El resultado es una aproximación de hora solar media local basada en longitud, no hora civil ni una solución exacta de tiempo solar aparente. El código no utiliza una fecha desplazada por hora solar para el agrupamiento.

#figure(
  table(
    columns: (48%, 52%),
    table.header([Etiqueta de ventana], [Intervalo de hora solar]),
    [Mañana], [08:30 hasta antes de 12:00],
    [Tarde], [12:00 hasta antes de 16:00],
    [Etiqueta noche-Terra], [20:00 hasta antes de 23:30],
    [Etiqueta madrugada/noche], [23:30 a 24:00; 00:00 hasta antes de 04:00],
    [Fuera de ciclo], [Todas las horas restantes],
  ),
  caption: [Ventanas seleccionadas por el proyecto. Las etiquetas describen intervalos horarios; no identifican el satélite ni prueban observación simultánea.],
)

Con latitud $phi$ y un paso angular seleccionado por el proyecto $d=0.02 degree$, las claves espaciales son:
$ y_q = d "round"(phi/d) $ <eq:grid-lat>
$ x_q = d "round"((lambda cos(phi))/d) $ <eq:grid-lon>

El SQL convierte la latitud a radianes antes de evaluar el coseno. Un paso de latitud de 0.02 grados equivale aproximadamente a 2.2 km. La transformación de longitud es una regla aproximada de indexación; no es una proyección validada de igual distancia ni de igual área. Detecciones vecinas pueden caer en lados opuestos de los límites de celda. Las dimensiones de huella del píxel se conservan pero no se usan en esta regla de emparejamiento.

La hora de adquisición se trunca a la hora UTC. La clave está formada por país, $y_q$, $x_q$ y hora truncada. Así, 18:59 y 19:01 quedan separados a pesar de estar a solo dos minutos de distancia.

== Coocurrencia y razones por país

Para cada clave $q$, definimos $M_q$ y $V_q$ como los conteos de registros MODIS y VIIRS. Una coocurrencia candidata pertenece al conjunto $A$ cuando ambos conteos son positivos. Esta es una asociación a nivel de celda, no un duplicado físico verificado.

Para registros de 2012 en adelante, la implementación calcula:
$ r_c = (sum_(q in A) V_q)/(sum_(q in A) M_q) $ <eq:pixel-ratio>
$ r_p = (sum_(q in A) P_(V,q))/(sum_(q in A) P_(M,q)) $ <eq:frp-ratio>

$P_(V,q)$ y $P_(M,q)$ son sumas de valores de FRP registrados, tratando los valores faltantes como cero en el SQL actual. Además:
$ r_a = N_(V,a)/N_(M,a), quad r_n = N_(V,n)/N_(M,n) $ <eq:regime-ratios>

El subíndice $a$ denota totales de tarde; $n$ combina ambas ventanas nocturnas y las observaciones fuera de ciclo. Estos totales no requieren observaciones emparejadas espacialmente. Todas las plataformas VIIRS se agrupan en conjunto.

El código usa $r_c$ para el factor de mañana aunque $A$ no está restringido a observaciones matutinas. La transferencia de esa relación a observaciones de Terra en la mañana es un supuesto no probado.

== Selección de parámetros

Cuando existen al menos 100 grupos de coocurrencia candidatos para un país y la razón requerida está definida, los factores se calculan con:
$ f = "round"(max(l,min(r,u)),2) $ <eq:clamp>

Aquí $l$ y $u$ son los límites; 2 es el número de decimales. Razones indefinidas o grupos insuficientes invocan los siguientes valores de respaldo.

#figure(
  table(
    columns: (18%, 22%, 30%, 30%),
    align: (left, center, center, center),
    table.header([Factor], [Razón], [Límites], [Respaldo]),
    [$f_m$], [$r_c$], [1 a 10], [2.20],
    [$f_a$], [$r_a$], [1 a 20], [6.12],
    [$f_n$], [$r_n$], [1 a 15], [4.50],
    [$f_p$], [$r_p$], [0.5 a 5], [1.14],
  ),
  caption: [Parámetros implementados del proyecto. No se encontraron derivaciones empíricas publicadas de estos valores de respaldo.],
)

El umbral de 100 es una heurística de muestra mínima; no es una prueba de significancia estadística. Actualmente no se producen intervalos de confianza, tamaños efectivos de muestra ni propagación de incertidumbre. Los límites de recorte y el redondeo a dos decimales son decisiones de ingeniería, no resultados de validación. No se afirman interpretaciones regionales o físicas sin respaldo para los valores de respaldo.

== Pesos por punto e índice mensual

Sea $C_i=1$ cuando un registro MODIS comparte su clave candidata con al menos un registro VIIRS, y $C_i=0$ en caso contrario. La regla real de ponderación es:
$ w_i = cases(
  1 & i in V,
  0 & i in M " y " C_i=1,
  f_m & i in M " en mañana",
  f_a & i in M " en tarde",
  f_n & "MODIS restante"
) $ <eq:weight>

Las ramas de mañana y tarde se aplican después de la rama de coocurrencia. Seis categorías almacenadas distinguen registros VIIRS preservados, MODIS suprimidos, MODIS únicos en la mañana, MODIS históricos, MODIS exclusivos de la tarde y otros registros MODIS. La etiqueta histórica no introduce un coeficiente histórico separado: los mismos factores de ventana horaria se aplican antes de 2012. La categoría de mañana tiene precedencia sobre la categoría histórica en el SQL.

Para el mes $t$, el índice experimental de actividad es:
$ A_t = sum_(i in t) w_i $ <eq:activity>

Esta suma no crea ubicaciones de puntos adicionales. Las unidades fraccionarias son contribuciones ponderadas, no incendios contados de forma independiente, hectáreas ni una reconstrucción demostrada de observaciones VIIRS faltantes.

== FRP derivada e interpretación

Con FRP nativa $P_i$, el campo derivado sigue:
$ P_i^* = cases(
  P_i & i in V,
  0 & i in M " y " C_i=1,
  "round"(P_i f_p,2) & "otro MODIS"
) $ <eq:frp-harm>

El SQL actual reemplaza la FRP nativa faltante con cero en este campo derivado, mientras conserva el campo nativo anulable. Las recuperaciones faltantes y la potencia medida igual a cero deben mantenerse diferenciables en la interpretación posterior.

La guía de Colección 2 de la NASA describe una recuperación híbrida que utiliza detecciones en banda I de VIIRS y radiancia M13; las detecciones colocalizadas de 375 m comparten FRP fraccionaria proveniente de la recuperación subyacente @viirsguide2024. Por lo tanto, una FRP media menor por registro VIIRS no implica por sí misma menor intensidad física del fuego.

Una suma mensual de $P_i^*$ es una estadística de potencia sumada por observación. La energía requiere integración temporal, por ejemplo $E=integral P(t) dif t$, junto con supuestos sobre los intervalos no observados. Aquí no se estiman ni energía ni superficie quemada.

== Agrupamiento de eventos de incendio para representación en el mapa

Un único punto de calor satelital representa un píxel térmico detectado más que un incendio completo. Múltiples detecciones MODIS y VIIRS de distintos pasos satelitales suelen pertenecer al mismo episodio de quema. Para evitar saturación visual y presentar un panorama operativo más claro en el mapa, el pipeline agrupa los puntos de calor individuales en *eventos de incendio* mediante dos etapas SQL puras en DuckDB (`sql/clusters/01_assign_events.sql` y `02_build_clusters.sql`) antes de cargarlos masivamente en PostgreSQL/PostGIS:

- *Regla de celda espacial:* Cada punto de calor se asigna a una celda de cuadrícula de `0.02` grados (unos 2.2 km). Todas las detecciones que comparten la misma celda son candidatas para el mismo evento.
- *Regla de continuidad de 24 horas:* Dentro de cada celda, las detecciones se ordenan por hora de adquisición. Las detecciones consecutivas permanecen en el mismo evento de incendio siempre que la brecha entre ellas sea de 24 horas o menos. Una brecha mayor a 24 horas inicia un nuevo evento, lo que evita que incendios continuos de varios días se dividan artificialmente a la medianoche.
- *Regla de geometría de huella:* Para cada evento de incendio, DuckDB Spatial calcula el punto central (centroide) a partir de sus puntos de calor constituyentes y construye un polígono de perímetro tomando la envolvente convexa exterior de los puntos y expandiéndola con un buffer de `0.0036` grados (unos 400 m). Esto garantiza que incluso un evento de uno o dos puntos de calor tenga un polígono válido y un área geodésica en kilómetros cuadrados.
- *Resumen del evento e inspección bajo demanda:* Cada evento registra el conteo total de puntos de calor, conteos separados de MODIS y VIIRS, marcas de tiempo de inicio y fin, FRP pico y total, y el peso de armonización sumado. En el mapa web, los eventos de incendio se muestran como marcadores con anillo a escala regional y perímetros discontinuos al acercar; los puntos de calor individuales constituyentes se obtienen únicamente cuando el usuario hace clic para inspeccionar un evento específico o cambia a la capa de puntos crudos.

Como limitación conocida del agrupamiento basado en cuadrícula, dos detecciones cercanas que caen en lados opuestos de un límite de celda de `0.02` grados se asignan a eventos separados.

== Integración actual en la aplicación

El SQL de exportación calcula el índice experimental y la FRP derivada junto con los conteos crudos. Su bandera de procesamiento la establece el comando de exportación, no una compuerta de validación independiente.

El JSON incluido permanece explícitamente sin armonizar, y el calendario del frontend lee conteos totales crudos o específicos por sensor. La agregación del calendario de incendios en el backend también utiliza conteos y FRP crudos. El flujo de trabajo ponderado está implementado en el pipeline, pero no es la métrica mostrada actualmente por este calendario de demostración.
