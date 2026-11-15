#let evidence = json("../validation/results.json")

= Resultados y Verificación

== Verificaciones sintéticas reproducibles

El ejecutor en Python incluido en el repositorio construye 810 registros sintéticos y ejecuta los cuatro archivos SQL de producción sin modificaciones con DuckDB #evidence.duckdb_version. No requiere ningún archivo FIRMS descargado y utiliza únicamente la biblioteca estándar de Python junto con la CLI de DuckDB. Los nombres de escenario ocupan el campo de país únicamente para aislar los experimentos.

Se preservaron las 810 tuplas de registros nativos, con #evidence.native_mismatches discrepancias en país, coordenadas, hora UTC, instrumento, satélite y FRP nativa. Los demás atributos construidos son marcadores de posición; esto no constituye una evaluación completa de la calidad de los metadatos de FIRMS.

#figure(
  table(
    columns: (66%, 17%, 17%),
    align: (left, right, right),
    table.header([Escenario construido], [Filas], [Índice]),
    [Misma ubicación; 18:31 / 18:33], [2], [1.00],
    [Misma ubicación; 18:59 / 19:01], [2], [7.12],
    [Límite espacial; 0.218 m de separación], [2], [7.12],
    [MODIS más dos plataformas VIIRS], [3], [2.00],
    [100 grupos; una plataforma VIIRS], [300], [200.00],
    [Misma actividad; dos plataformas VIIRS], [500], [400.00],
    [VIIRS con FRP faltante], [1], [1.00],
  ),
  caption: [Comportamiento observado del software sobre entradas sintéticas. Las salidas reproducen limitaciones conocidas; no establecen exactitud en el mundo real.],
)

Para los primeros tres casos, existen menos de 100 grupos de coocurrencia, por lo que el registro aislado de MODIS en la tarde recibe el respaldo de 6.12. Cruzar un límite temporal o espacial cambia por lo tanto el índice de 1 a $6.12+1=7.12$. La separación espacial extremadamente corta es un caso límite matemático construido, no una afirmación sobre la precisión de geolocalización satelital.

En los experimentos de calibración, cada uno de los 100 registros MODIS tiene dos píxeles VIIRS por plataforma en la misma observación de la tarde. Añadir una segunda plataforma reproduce la misma señal simulada. Los factores de mañana, tarde y FRP cambian de 2.00 a 4.00. Esto demuestra sensibilidad al número de plataformas de observación agrupadas.

El caso de FRP faltante preserva el valor nulo nativo, pero genera una FRP derivada de 0.00. Esto documenta la política actual de datos faltantes; no establece que la potencia radiativa física haya sido cero.

== Qué establecen las verificaciones

El software puede ejecutar sus transformaciones documentadas, preservar los campos nativos evaluados y reproducir los efectos de límite y muestreo reportados. Los hashes de las fuentes, los resultados legibles por máquina y las instrucciones de reproducción acompañan a este informe.

No se ha medido aún exactitud, precisión, exhaustividad (recall), intervalo de incertidumbre ni reducción de sesgo entre sensores sobre datos reales para este prototipo. El antiguo marcador de posición de referencia para Argentina y las referencias a archivos de referencia ausentes fueron eliminados. Las pruebas unitarias del backend y la compilación exitosa del PDF no sustituyen la validación científica.
