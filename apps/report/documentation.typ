#set document(title: "Armonización de observaciones MODIS y VIIRS en Centroamérica", author: "PyroTrace")
#set page(paper: "us-letter", margin: 1in, header-ascent: 0.5in,
  header: context align(right, counter(page).display()))
#set text(font: "Times New Roman", size: 12pt, lang: "es", top-edge: 0.8em, bottom-edge: -0.2em)
#set par(justify: false, leading: 1em, spacing: 1em,
  first-line-indent: (amount: 0.5in, all: true))
#set block(spacing: 1em)
#set heading(numbering: none)
#set math.equation(numbering: "(1)")
#show heading: it => block(width: 100%, above: 1em, below: 1em, sticky: true)[
  #set text(size: 12pt, weight: "bold")
  #set par(first-line-indent: 0pt)
  #if it.depth == 1 { align(center, it.body) } else { it.body }
]
#show raw: set text(font: "Times New Roman", size: 12pt)
#show link: set text(fill: black)
#set table(stroke: (x,y) => if y == 0 { (top: 0.5pt, bottom: 0.5pt) } else { none },
  inset: (x: 5pt, y: 5pt), align: left)
#show table.cell.where(y: 0): set text(weight: "bold")

#align(center)[
  #set par(first-line-indent: 0pt)
  *Armonización de observaciones MODIS y VIIRS en Centroamérica*
]



PyroTrace integra los registros de fuego activo de MODIS y VIIRS distribuidos por NASA FIRMS para analizar la actividad del fuego en Centroamérica a lo largo del tiempo. El procesamiento conserva las observaciones originales y añade pesos que permiten construir un índice de actividad con VIIRS como referencia.

La integración responde a diferencias entre los sensores. MODIS registra anomalías térmicas con una resolución nominal de 1 km, mientras que el producto VIIRS utilizado corresponde a 375 m y presenta mayor respuesta ante fuegos pequeños. Sus registros también difieren en horarios de adquisición, dimensiones del píxel y frecuencia de observación (NASA FIRMS, s. f.-b, s. f.-c).

El método implementa una ponderación experimental por coincidencia espacial y temporal. La unidad resultante es una contribución ponderada al índice; una detección satelital corresponde a un píxel con anomalía térmica y no necesariamente a un incendio independiente.

= Datos de entrada

El prototipo procesa observaciones de Belice, Costa Rica, El Salvador, Guatemala, Honduras, Nicaragua y Panamá. La selección regional se realiza durante la integración de los archivos de entrada, mientras que los factores de ajuste se estiman por país.

El procesamiento utiliza el archivo #raw("hotspots.parquet"), que reúne las observaciones MODIS y VIIRS en una estructura común. Cada registro incluye país, latitud, longitud, fecha y hora UTC, instrumento, plataforma satelital, temperaturas de brillo, confianza, potencia radiativa del fuego (FRP), dimensiones de barrido y trayectoria del píxel, versión del producto, tipo de anomalía y clasificación diurna o nocturna.

Las coordenadas identifican el centro del píxel observado. La FRP expresa la potencia radiativa integrada en ese píxel, medida en megavatios. Los campos originales se conservan junto con las variables derivadas (NASA FIRMS, s. f.-b, s. f.-c).

La normalización de nombres facilita el almacenamiento y la consulta, pero no iguala las características físicas de las bandas. Del mismo modo, los códigos numéricos asignados a las categorías de confianza VIIRS son una convención de almacenamiento, no probabilidades calibradas equivalentes a la confianza MODIS.

= Procesamiento de las observaciones

== Hora solar local

La hora de adquisición se transforma en una hora solar media local aproximada mediante la longitud geográfica:

$ h_s = h_"UTC" + m/60 + lambda/15 $

En esta expresión, $h_"UTC"$ representa la hora UTC, $m$ los minutos y $lambda$ la longitud en grados, positiva hacia el este. Dividir los minutos entre 60 los convierte a horas. El divisor 15 corresponde a los 360 grados de rotación terrestre distribuidos en 24 horas.

El resultado se ajusta al intervalo de un día:

$ "LST" = ((h_s " mod " 24) + 24) " mod " 24 $

Esta aproximación permite organizar las observaciones según su horario local de adquisición. Las franjas utilizadas por el procesamiento son:


#block(breakable: false)[
#set par(first-line-indent: 0pt)
*Tabla 1*\
_Franjas de adquisición según la hora solar local_

#[
#set par(leading: 0.3em, spacing: 0.3em, first-line-indent: 0pt)
#table(columns: (1fr,1fr),
 table.header([Franja],[Intervalo de hora solar]),
 [Mañana],[Desde 08:30 hasta antes de 12:00],
 [Tarde],[Desde 12:00 hasta antes de 16:00],
 [Noche],[Desde 20:00 hasta antes de 23:30],
 [Madrugada],[Desde 23:30 hasta antes de 04:00],
 [Fuera de ciclo],[Horarios restantes],
 table.hline(stroke: 0.5pt),
)
]
]

Los intervalos son parámetros del método. Sus etiquetas describen franjas horarias y no sustituyen la identificación de la plataforma satelital.

== Agrupación espacial y temporal

Las coordenadas se convierten en claves de agrupación mediante un paso angular $d = 0.02 degree$:

$ y_q = d "round"(phi/d) $


$ x_q = d "round"((lambda cos(phi))/d) $

Aquí, $phi$ es la latitud y $lambda$ la longitud. El SQL convierte la latitud a radianes antes de evaluar el coseno. El paso de latitud equivale aproximadamente a 2.2 km; la transformación de longitud es una aproximación de indexación, no una proyección de distancia o área constante.

La marca temporal se trunca a la hora UTC. Las observaciones se agrupan por país, ambas claves espaciales y bloque horario. Esta combinación permite localizar conjuntos con presencia de los dos instrumentos.

== Identificación de coocurrencias

En cada grupo se cuentan los registros MODIS y VIIRS y se suman sus valores de FRP. Un grupo se considera una coocurrencia candidata cuando contiene al menos una observación de cada instrumento.

La asociación indica proximidad según las claves del procesamiento. La coincidencia física entre detecciones depende también de sus huellas y de la diferencia real entre las adquisiciones.

== Estimación de factores por país

Los factores se calculan con observaciones desde 2012, dentro del período de coexistencia de ambos instrumentos. Para el conjunto #raw("A") de grupos con coocurrencia se obtiene la razón entre detecciones:

$ r_c = (sum_(q in A) V_q)/(sum_(q in A) M_q) $

$V_q$ y $M_q$ representan las cantidades de registros VIIRS y MODIS del grupo. La razón de FRP se calcula de forma análoga:

$ r_"FRP" = (sum_(q in A) P_(V,q))/(sum_(q in A) P_(M,q)) $

$P_(V,q)$ y $P_(M,q)$ son las sumas de FRP de cada instrumento dentro del grupo.

El factor de mañana utiliza la razón de conteos en coocurrencias de todas las franjas. Los factores de tarde y noche se calculan con los totales de sus respectivos horarios, sin exigir emparejamiento espacial; el cálculo nocturno incluye las observaciones fuera de ciclo. La estimación agrupa las plataformas VIIRS disponibles.

Cuando existen al menos 100 grupos con coocurrencia y la razón correspondiente está definida, el factor se limita a un intervalo y se redondea a dos decimales:

$ f = "round"(max(l,min(r,u)),2) $

Los parámetros #raw("l") y #raw("u") representan los límites inferior y superior. Cuando la muestra o la razón no permiten realizar el cálculo, se utilizan valores predeterminados.


#block(breakable: false)[
#set par(first-line-indent: 0pt)
*Tabla 2*\
_Parámetros de ajuste por país_

#[
#set par(leading: 0.3em, spacing: 0.3em, first-line-indent: 0pt)
#table(columns: (1fr,1fr,1fr),
 table.header([Factor],[Límites],[Valor predeterminado]),
 [Mañana],[1 a 10],[2.20],
 [Tarde],[1 a 20],[6.12],
 [Noche y otras horas],[1 a 15],[4.50],
 [FRP],[0.5 a 5],[1.14],
 table.hline(stroke: 0.5pt),
)
]
]

El umbral de 100 grupos, los límites y los valores predeterminados son decisiones de configuración del proyecto. La procedencia empírica de los cuatro valores predeterminados no está documentada.

== Asignación de pesos y FRP derivada

Los pesos se asignan de acuerdo con el instrumento y la presencia de VIIRS en el mismo grupo:


#block(breakable: false)[
#set par(first-line-indent: 0pt)
*Tabla 3*\
_Pesos asignados a las observaciones_

#[
#set par(leading: 0.3em, spacing: 0.3em, first-line-indent: 0pt)
#table(columns: (1fr,1fr),
 table.header([Observación],[Peso asignado]),
 [VIIRS],[1],
 [MODIS con coocurrencia VIIRS],[0],
 [MODIS sin coocurrencia, en la mañana],[Factor de mañana],
 [MODIS sin coocurrencia, en la tarde],[Factor de tarde],
 [Otros registros MODIS],[Factor de noche],
 table.hline(stroke: 0.5pt),
)
]
]

Los mismos factores por franja se aplican a las observaciones MODIS anteriores a 2012. El registro original permanece almacenado incluso cuando su contribución al índice es cero.

La FRP derivada conserva el valor VIIRS, asigna cero al MODIS con coocurrencia y multiplica la FRP de los demás MODIS por el factor específico de FRP. Los valores ausentes se mantienen en el campo original, aunque el campo derivado los reemplaza por cero.

En VIIRS de 375 m, la recuperación de FRP combina la identificación de píxeles afectados por fuego con radiancia M13 de 750 m. Varios subpíxeles detectados pueden compartir fracciones de una misma recuperación de potencia (Schroeder et al., 2024). Por ello, el ajuste de FRP se trata por separado del ajuste de conteos.

= Agregación y uso de los resultados

La actividad mensual se obtiene sumando los pesos de las observaciones del período:

$ A_t = sum_(i in t) w_i $

$A_t$ es el índice del mes y $w_i$ el peso de cada registro. Los valores fraccionarios expresan contribuciones ponderadas; el procedimiento no genera nuevas ubicaciones de fuego.

El archivo #raw("hotspots_harmonized.parquet") conserva las variables originales y añade la franja horaria, la categoría de armonización, el peso y la FRP derivada. El exportador mensual produce el índice junto con los conteos originales y las estadísticas de FRP.

La aplicación utiliza actualmente los conteos originales del archivo mensual para representar el calendario. El índice ponderado se genera como una medida diferenciada de esos conteos.

Una suma de valores de FRP obtenidos en distintos horarios es una estadística de potencia muestreada. Para estimar energía se requiere integrar la potencia respecto al tiempo y definir cómo se representan los intervalos entre adquisiciones.

= Comprobaciones del procesamiento

La ejecución sobre 810 registros sintéticos comprobó la conservación de las tuplas originales evaluadas y permitió examinar el efecto de las reglas de agrupación.


#block(breakable: false)[
#set par(first-line-indent: 0pt)
*Tabla 4*\
_Resultados de las comprobaciones con datos sintéticos_

#[
#set par(leading: 0.3em, spacing: 0.3em, first-line-indent: 0pt)
#table(columns: (1fr,1fr),
 table.header([Caso evaluado],[Índice obtenido]),
 [Misma ubicación, adquisiciones a las 18:31 y 18:33],[1.00],
 [Misma ubicación, adquisiciones a las 18:59 y 19:01],[7.12],
 [Puntos separados por un límite de celda espacial],[7.12],
 [Cien grupos con una plataforma VIIRS],[200.00],
 [Misma actividad simulada con dos plataformas VIIRS],[400.00],
 table.hline(stroke: 0.5pt),
)
]
]

El cambio al cruzar un límite horario o espacial se debe a que el MODIS deja de asociarse con VIIRS y recibe el factor predeterminado de tarde. El experimento con dos plataformas muestra que el índice también responde al número de observaciones incorporadas.

Las comprobaciones se reproducen desde la raíz del repositorio:

#raw("python apps/report/validation/verify_prototype.py", block: true)

Los resultados se guardan en #raw("apps/report/output/validation"), junto con la versión de DuckDB y las huellas SHA-256 de los cuatro archivos SQL.

= Consideraciones metodológicas

La comparabilidad entre años depende de la sensibilidad del instrumento, de la cobertura y de las oportunidades de observación. La incorporación de una plataforma adicional puede incrementar los conteos sin un aumento equivalente del fuego. Las nubes, el humo y la duración de los eventos también afectan la detección (NASA FIRMS, s. f.-a).

Las coincidencias mediante bloques fijos presentan efectos de borde. Su evaluación debe considerar distancia geográfica, huella del píxel y diferencia temporal real. Los factores estimados en coocurrencias pueden favorecer los fuegos detectables por ambos instrumentos; su transferencia a la mañana y a períodos históricos requiere evaluación independiente.

Los límites numéricos y el tamaño mínimo de muestra estabilizan el cálculo, pero no constituyen una prueba de significancia estadística. La validación del índice requiere comparar estimaciones y observaciones de referencia en años o regiones reservados para evaluación, controlando la plataforma y la cobertura. La FRP debe analizarse por separado, considerando que su relación entre sensores depende de la geometría, el ecosistema y la escala de agregación (Li et al., 2018). Esta comparación corresponde a VIIRS de 750 m, por lo que sus coeficientes no se trasladan directamente al producto de 375 m.


#pagebreak()
#align(center)[
  #set par(first-line-indent: 0pt)
  *Referencias*
]

#[
#set par(first-line-indent: 0pt, hanging-indent: 0.5in, leading: 1em, spacing: 1em)
Li, F., Zhang, X., Kondragunta, S., & Csiszar, I. (2018). Comparison of fire radiative power estimates from VIIRS and MODIS observations. _Journal of Geophysical Research: Atmospheres, 123_(9), 4545–4563. #link("https://doi.org/10.1029/2017JD027823")[https://doi.org/10.1029/2017JD027823]

NASA FIRMS. (s. f.-a). _Fire alert notes_. #link("https://firms.modaps.eosdis.nasa.gov/alerts/notes.php")[https://firms.modaps.eosdis.nasa.gov/alerts/notes.php]

NASA FIRMS. (s. f.-b). _MODIS fire and thermal anomalies_. #link("https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html")[https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html]

NASA FIRMS. (s. f.-c). _VIIRS fire and thermal anomalies_. #link("https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html")[https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html]

Schroeder, W., Giglio, L., & Hall, J. (2024). _Collection 2 VIIRS 375-m active fire product user’s guide_ (Versión 1.0). NASA Land Science Investigator Processing System. #link("https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.0.pdf")[https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.0.pdf]
]
