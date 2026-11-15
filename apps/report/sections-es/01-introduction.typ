= Introducción

== Motivación científica

Un registro de incendio activo es una observación satelital de una anomalía térmica. No constituye automáticamente un evento de incendio individual ni una medición de superficie quemada. Las coordenadas de FIRMS ubican centros de píxel; un píxel MODIS puede contener más de un incendio. Las detecciones de incendios MODIS tienen una resolución nominal de 1 km, con huellas mayores lejos del nadir @firmsmodis. Las detecciones VIIRS de 375 m ofrecen una mayor respuesta ante incendios más pequeños @firmsviirs. Las publicaciones de los algoritmos describen procedimientos de detección distintos y específicos para cada instrumento @giglio2016 @schroeder2014.

En consecuencia, fusionar registros en un mismo esquema no hace que sus conteos sean comparables por sí solo. Las observaciones repetidas, las nubes, la hora de adquisición, los cambios de colección y el número de plataformas en operación pueden afectar la actividad observada. Un conteo de cero por sí solo no permite distinguir entre ausencia de fuego y observación perdida @firmsnotes.

== Objetivo y alcance del prototipo

PyroTrace se desarrolla en el contexto del desafío NASA Space Apps sobre puntos de calor MODIS y VIIRS. El objetivo de este informe es describir con precisión un flujo de trabajo experimental funcional y sus limitaciones. No afirma que se hayan eliminado las discontinuidades por transición entre sensores.

El prototipo explora tres operaciones: preservar las observaciones originales, identificar coocurrencias candidatas entre MODIS y VIIRS, y ponderar los registros exclusivos de MODIS hacia un índice provisional de actividad referenciado a VIIRS. Esta referencia aún no está fijada a una única plataforma ni a un horario de observación único. Por lo tanto, la interpretación de tendencias históricas permanece fuera del alcance demostrado.

== Límites del sistema y de la evidencia

El repositorio contiene un pipeline de ingesta en Python/SQLite, transformaciones en DuckDB/Parquet, un esquema en estrella en PostgreSQL/PostGIS, un backend en FastAPI y un frontend en Vue/MapLibre. Estos componentes dan soporte al acceso y la visualización de datos; su existencia no constituye evidencia de exactitud en calibración científica.

Esta revisión verifica el SQL mediante entradas sintéticas. Los archivos Parquet originales de FIRMS y los metadatos de nubosidad o franja de barrido (swath) no estaban disponibles en esta copia del repositorio. No se reporta ninguna calibración nueva sobre el archivo completo, comparación en campo ni medición de exactitud sobre datos reales. Los tiempos de ingesta y conteos de pruebas del backend registrados previamente no se reutilizan como evidencia de armonización.

== Límites verificados de las fuentes

La página de archivo de FIRMS distingue los registros de Terra desde noviembre de 2000 de los registros de Aqua desde julio de 2002, y lista la disponibilidad de archivo de NOAA-20 desde abril de 2018 y de NOAA-21 desde enero de 2024 @firmsarchive. Las fechas de lanzamiento no son intercambiables con la disponibilidad del producto.

La documentación de productos de la NASA respalda las propiedades de los sensores citadas en este informe. No establece los factores de respaldo (fallback), anchos de celda, tamaño mínimo de muestra ni límites de recorte del proyecto. Esas son decisiones de implementación documentadas en la Sección 2.
