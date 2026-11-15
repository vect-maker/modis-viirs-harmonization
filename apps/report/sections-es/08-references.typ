#import "../template.typ": tight, note

= 8. Referencias y Herramientas Utilizadas

== Herramientas

@tbl-tools enumera las principales herramientas utilizadas para construir PyroTrace y este informe.

#figure(
  table(
    columns: (30%, 70%),
    table.header([Área], [Herramientas]),
    [Adquisición de datos], [Python, SQLite, Apache Parquet, API de NASA FIRMS],
    [Procesamiento y armonización], [DuckDB (SQL, extensiones spatial y PostgreSQL)],
    [Almacenamiento], [PostgreSQL con PostGIS],
    [Backend], [FastAPI, SQLModel, Pydantic, NATS JetStream],
    [Frontend], [Vue 3, TypeScript, Vite, Pinia, VueUse, MapLibre GL, ECharts, Tailwind CSS],
    [Operaciones], [Podman Compose, Caddy, just, máquina virtual de Microsoft Azure],
    [Análisis y figuras], [Python, Matplotlib],
    [Documentación], [Typst],
  ),
  caption: [Herramientas Utilizadas en el Proyecto],
) <tbl-tools>

== Uso de Inteligencia Artificial

El equipo utilizó tres herramientas de inteligencia artificial generativa durante el evento: Claude @claude, ChatGPT @chatgpt y Google Antigravity @antigravity. Estas asistieron en la escritura y revisión de código, depuración, diseño de la interfaz, preparación de scripts de análisis y redacción y edición de documentación, incluido este informe. Los integrantes del equipo revisaron, probaron y editaron todo el contenido asistido por IA y asumen la responsabilidad del resultado final. Todas las figuras, tablas y resultados numéricos fueron calculados desde la base de datos de PyroTrace y el ejecutor de pruebas mediante código incluido en el repositorio; ninguno fue generado por una herramienta de IA.

== Referencias

#set par(first-line-indent: 0pt, hanging-indent: 0.5in)
#bibliography("../references.bib", style: "apa", title: none)
