#import "../template.typ": tight, note

#pagebreak()
#align(center)[*Apéndice A*]
#align(center)[*Reproducción*]

El repositorio contiene todo lo necesario para reproducir los resultados. Desde la raíz del repositorio, el pipeline se ejecuta con las recetas `just` siguientes; descargan el archivo de FIRMS, lo fusionan y armonizan, construyen el esquema en estrella y lo cargan en PostGIS.

#tight(raw(block: true, lang: "bash", "just pipeline::setup-env
just pipeline::sync-meta
just pipeline::fetch-central-america
just pipeline::fuse-data
just pipeline::harmonize-data
just pipeline::normalize-data
just pipeline::db-schema
just pipeline::db-load
just pipeline::cluster-events"))

La verificación sintética y este informe se reproducen desde `apps/report`:

#tight(raw(block: true, lang: "bash", "python validation/verify_prototype.py --refresh-report-data
typst compile --font-path fonts main-es.typ output/report-es.pdf"))

El ejecutor requiere la interfaz de línea de comandos de DuckDB. Registra la versión de DuckDB y el hash SHA-256 de cada archivo SQL en `validation/results.json`, que este informe lee directamente. Si el SQL cambia, el ejecutor debe ejecutarse nuevamente antes de recompilar el informe.
