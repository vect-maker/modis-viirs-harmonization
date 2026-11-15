= 3. Problema y Objetivos

== Contexto

El fuego es un componente recurrente de la temporada seca en Centroamérica. En el archivo de PyroTrace, la mayoría de las detecciones ocurren entre febrero y mayo, con un pico regional en abril, cuando coinciden las quemas agrícolas, el desmonte de tierras y los incendios forestales. Saber si una temporada es inusual requiere un registro largo y consistente, porque un año individual solo puede evaluarse frente a los años anteriores.

Dos familias de instrumentos proveen ese registro. MODIS, a bordo de los satélites Terra y Aqua, ha observado incendios activos desde noviembre de 2000 (Terra) y julio de 2002 (Aqua) con un píxel nominal de 1 km @firmsarchive @firmsmodis @giglio2016. VIIRS, en Suomi-NPP desde 2012 y en NOAA-20 y NOAA-21 desde 2018 y 2024, observa con un píxel de 375 m y responde a incendios mucho más pequeños @firmsviirs @schroeder2014. Cada detección marca el centro de un píxel con una anomalía térmica; no es un incendio individual, y una detección faltante puede significar ausencia de fuego, cobertura nubosa o falta de paso satelital @firmsnotes.

== Problema

Los dos registros no pueden sumarse directamente. En el archivo centroamericano, las detecciones crudas pasan de 33,313 en 2011 a 213,676 en 2013, un aumento en un factor de 6.41, mientras que las detecciones solo de MODIS crecen en un factor de apenas 1.09. La mayor parte del aumento aparente es, por lo tanto, producto del cambio de instrumentos. El mismo artefacto aparece cada vez que entra en servicio una nueva plataforma VIIRS. Sin armonización, un estudiante, un investigador o un equipo de prevención de incendios que compare 2005 con 2024 llegaría a una conclusión errónea.

La pregunta guía del proyecto es: _¿Cómo pueden combinarse las detecciones de incendios activos de MODIS y VIIRS en un único registro comparable a lo largo del período 2000 a 2025, manteniendo trazable cada observación original?_

== Objetivo General

Construir una plataforma web abierta que armonice los registros de incendios activos MODIS y VIIRS de NASA FIRMS para Centroamérica y permita a cualquier usuario explorar, comparar y descargar la actividad de incendios a través del tiempo y el espacio.

== Objetivos Específicos

+ Reunir el archivo completo de FIRMS para los siete países de Centroamérica en un pipeline reproducible.
+ Diseñar e implementar un método transparente de armonización que preserve las detecciones originales y las exprese en una unidad común.
+ Almacenar el registro armonizado en una base de datos espacial y exponerlo mediante una API documentada.
+ Presentar el registro en un mapa interactivo, un calendario histórico y estadísticas que comparen cada período con su rango histórico.
+ Verificar el comportamiento del software y evaluar el efecto remanente de transición entre sensores mediante diagnósticos explícitos.

== Resultados Esperados

Los resultados esperados son un archivo armonizado y documentado, una aplicación web pública que no requiera conocimientos técnicos ni cuenta de usuario, evidencia cuantitativa de cuánto reduce la armonización el salto por transición de sensores y un plan de validación para los pasos que aún quedan pendientes.
