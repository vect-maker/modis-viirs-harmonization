#import "../template.typ": tight, note

= 5. Metodología y Recursos Científicos

== Proceso de Trabajo

El equipo trabajó en cuatro etapas durante el evento. Primero, estudió el desafío y los productos de FIRMS para definir el problema y la región objetivo. Segundo, diseñó un método de armonización que pudiera expresarse en SQL y auditarse línea por línea. Tercero, implementó en paralelo el pipeline, la base de datos, la API y la aplicación web. Cuarto, verificó el software con pruebas sintéticas y evaluó el registro armonizado mediante diagnósticos sobre los datos reales, los cuales se reportan en la Sección 6.

== Datos y Recursos Científicos

@tbl-sources enumera los datos utilizados por PyroTrace. La entrada principal es el archivo de incendios activos de NASA FIRMS; las demás fuentes aportan contexto cartográfico y meteorológico.

#figure(
  table(
    columns: (25%, 42%, 33%),
    table.header([Recurso], [Uso en PyroTrace], [Fuente]),
    [Incendios activos MODIS (Terra, Aqua)], [Registro histórico desde noviembre de 2000; píxel nominal de 1 km], [NASA FIRMS @firmsmodis @firmsarchive],
    [Incendios activos VIIRS 375 m (Suomi-NPP, NOAA-20, NOAA-21)], [Registro desde 2012; unidad de referencia del índice armonizado], [NASA FIRMS @firmsviirs @viirsguide2024],
    [Archivo por país y API Area de FIRMS], [Descarga masiva del archivo y actualizaciones en tiempo casi real], [NASA FIRMS @firmsapi],
    [Datos diarios puntuales de NASA POWER], [Contexto meteorológico para eventos de incendio], [NASA Langley @nasapower],
    [Límites de países], [Asignación por país y contornos del mapa], [Natural Earth @naturalearth],
    [Mapa base satelital], [Fondo cartográfico], [Esri World Imagery @esriworldimagery],
  ),
  caption: [Fuentes de Datos y Recursos Científicos],
) <tbl-sources>

Cada registro conserva sus atributos de FIRMS: coordenadas del centro del píxel, fecha y hora de adquisición en UTC, satélite, instrumento, temperaturas de brillo, confianza, potencia radiativa del fuego (FRP), dimensiones del píxel, indicador día o noche y versión del producto. Los nombres de columna compartidos para temperaturas de brillo no hacen equivalentes a las bandas espectrales, y los códigos numéricos asignados a las clases de confianza de VIIRS (20, 50 y 90) son una convención de almacenamiento, no probabilidades calibradas @firmsmodis @firmsviirs.

== Método de Armonización

El método se ejecuta en cuatro etapas en DuckDB SQL sobre el archivo fusionado. Nunca elimina ni mueve una detección; únicamente agrega una categoría, un peso y un valor de FRP derivada.

=== Etapa 1: Tiempo Solar Local y Claves de Búsqueda

Los satélites cruzan la región a horas solares locales fijas, por lo que la hora de adquisición se convierte en una hora solar media local aproximada a partir de la hora UTC $h$, los minutos $m$ y la longitud $lambda$ en grados:

$ h_s = (h + m/60 + lambda/15) mod 24 $ <eq-solar>

La hora solar asigna cada detección a una ventana de paso satelital (@tbl-windows). Cada detección recibe también una celda espacial y un intervalo horario, con latitud $phi$ y un paso de $d = 0.02 degree$ (alrededor de 2.2 km):

$ y = floor(phi/d), quad x = floor((lambda cos phi)/d), quad s = floor(t/3600) $ <eq-cells>

donde $t$ es el tiempo de adquisición en segundos desde la época Unix. Las celdas únicamente aceleran la búsqueda; no deciden si dos detecciones coinciden.

#figure(
  table(
    columns: (40%, 60%),
    table.header([Ventana], [Horas solares locales]),
    [Mañana (Terra)], [08:30 hasta antes de 12:00],
    [Tarde (Aqua y VIIRS)], [12:00 hasta antes de 16:00],
    [Noche (Terra)], [20:00 hasta antes de 23:30],
    [Noche y madrugada (Aqua y VIIRS)], [23:30 hasta antes de 04:00],
    [Fuera de ciclo], [Todas las horas restantes],
  ),
  caption: [Ventanas de Paso Satelital Utilizadas por el Método],
) <tbl-windows>
#note[Los límites de las ventanas son decisiones del proyecto basadas en las horas nominales de paso de cada plataforma.]

=== Etapa 2: Codetecciones MODIS y VIIRS

Para cada detección MODIS, el método busca en las 27 combinaciones vecinas de celda y hora ($3 times 3 times 3$) y conserva cualquier detección VIIRS del mismo país ubicada dentro de 2,200 m y 3,600 s. La distancia $D$, en metros, utiliza una aproximación equirectangular con la latitud media $overline(phi)$ del par, donde 111,320 m es la longitud de un grado de latitud:

$ D = "111,320" sqrt((Delta phi)^2 + (Delta lambda cos overline(phi))^2) $ <eq-distance>

Ambos miembros de un par emparejado se marcan como codetecciones. Buscar en celdas vecinas elimina los artefactos de una cuadrícula fija: dos detecciones separadas por dos minutos a través de un límite horario, o a pocos metros a través del borde de una celda, siguen emparejándose (Sección 6.4).

=== Etapa 3: Calibración por País

El número de plataformas VIIRS cambia con el tiempo, por lo que cada detección VIIRS se divide primero entre el número de satélites VIIRS activos en su país y año, $p_(c,y)$. Usando únicamente el período de solapamiento (2012 en adelante), el método estima cuatro razones para cada país $c$:

$ r_m = (sum_(i in V^*) 1/p_(c,y)) / abs(M^*), quad r_a = (sum_(i in V_a) 1/p_(c,y)) / abs(M_a), quad r_n = (sum_(i in V_n) 1/p_(c,y)) / abs(M_n) $ <eq-ratios>

Aquí $V^*$ y $M^*$ son los registros VIIRS y MODIS codetectados; $V_a$ y $M_a$ son todos los registros en la ventana de la tarde; y $V_n$ y $M_n$ son todos los registros en las ventanas nocturnas y fuera de ciclo. Una cuarta razón, $r_p$, divide la FRP normalizada por plataforma de los registros VIIRS codetectados entre la FRP de los registros MODIS codetectados. Cuando un país tiene al menos 100 registros MODIS codetectados, cada factor es la razón acotada a un rango plausible y redondeada a dos decimales; en caso contrario se usa un valor de respaldo (@tbl-factors).

$ f = "round"(max(l, min(r, u)), 2) $ <eq-clamp>

#figure(
  table(
    columns: (34%, 18%, 22%, 26%),
    table.header([Factor], [Razón], [Límites], [Respaldo]),
    [Mañana, $f_m$], [$r_m$], [1 a 10], [2.20],
    [Tarde, $f_a$], [$r_a$], [1 a 20], [6.12],
    [Noche y fuera de ciclo, $f_n$], [$r_n$], [1 a 15], [4.50],
    [FRP, $f_p$], [$r_p$], [0.5 a 5], [1.14],
  ),
  caption: [Factores de Calibración, Límites y Valores de Respaldo],
) <tbl-factors>
#note[El umbral de 100 codetecciones, los límites y los valores de respaldo son decisiones de ingeniería del proyecto. Ningún estudio publicado los establece como constantes transferibles, y aún no se propaga incertidumbre.]

=== Etapa 4: Pesos y FRP Derivada

Cada detección $i$ en el país $c$ y año $y$ recibe el peso

$ w_i = cases(
  1 / p_(c,y) & "si" i "es VIIRS",
  0 & "si" i "es MODIS y codetectado",
  f_m & "si" i "es MODIS en la ventana de mañana",
  f_a & "si" i "es MODIS en la ventana de tarde",
  f_n & "en otro caso",
) $ <eq-weight>

El índice armonizado de cualquier período y área es la suma de los pesos de sus detecciones, $A = sum_i w_i$, expresado en detecciones equivalentes a VIIRS. Los mismos factores se aplican antes de 2012, cuando solo existía MODIS. La FRP derivada conserva el valor nativo de VIIRS, asigna cero a los registros MODIS codetectados, multiplica los demás registros MODIS por $f_p$ y mantiene los valores faltantes como faltantes. El índice no es un conteo de incendios independientes, superficie quemada ni energía del fuego.

== Estadísticas Mostradas en la Aplicación

Para la comparación mensual, la línea base de cada mes calendario es la distribución de ese mes a través de todos los demás años completos del archivo; la aplicación reporta sus percentiles 25, 50 y 75, y cada mes se etiqueta como por encima, dentro o por debajo de ese rango. Un mes cuenta como parcial cuando el archivo inicia después de su tercer día o termina más de dos días antes de su último día, y como provisional cuando más de la mitad de sus detecciones provienen del worker en tiempo casi real. Los meses parciales y provisionales se muestran, pero se excluyen de la línea base y de la comparación. La vista anual reporta las detecciones crudas por sensor y el índice armonizado para cada año, y su mediana utiliza únicamente años completos.

== Eventos de Incendio

Para simplificar el mapa, las detecciones se agrupan en eventos de incendio. Las detecciones en la misma celda de 0.02° pertenecen al mismo evento siempre que las detecciones consecutivas no estén separadas por más de 24 horas. Cada evento almacena su centroide, una huella construida a partir de la envolvente convexa de sus detecciones con un buffer de 400 m, su hora de inicio y fin, su FRP pico y total, y la suma de sus pesos armonizados.

== Enfoque de Verificación

El equipo evaluó el trabajo en tres niveles. Un ejecutor de pruebas reproducible construye 810 detecciones sintéticas y ejecuta sin cambios los cuatro archivos SQL de producción para verificar casos límite, efectos de plataforma y valores faltantes. Un diagnóstico sobre el archivo real mide el índice armonizado por cada detección MODIS, usando MODIS como referencia estable a través de la transición. Finalmente, se consultó cada endpoint de solo lectura de la API contra la base de datos completa. Los resultados se reportan en la Sección 6.
