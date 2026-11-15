= 7. Impacto y Perspectivas

== Beneficiarios

PyroTrace está diseñado para cuatro grupos:
- personas interesadas en el fuego, el ambiente y la observación satelital, que pueden explorar el registro sin formación geoespacial;
- estudiantes, docentes e investigadores, que necesitan un registro regional documentado y los datos crudos en CSV para clases y análisis;
- analistas ambientales y gestores de áreas protegidas, que necesitan reconocer patrones, anomalías y temporadas críticas en su territorio;
- bomberos y equipos de prevención, que pueden comparar la temporada actual con años anteriores al planificar recursos.

== Aplicaciones y Alcance

La plataforma respalda comparaciones estacionales ("¿Es inusual este abril?"), la identificación de áreas con actividad recurrente, la enseñanza sobre sensores satelitales y sus límites, y la preparación de líneas base históricas para investigación. Su alcance actual son los siete países de Centroamérica desde noviembre de 2000 hasta el presente. Debido a que el pipeline se alimenta de archivos por país de FIRMS y de un cuadro delimitador configurable, el mismo método puede extenderse a otros países sin modificar el SQL.

La plataforma no reemplaza las alertas operativas de incendios ni los reportes en terreno, y el índice armonizado no debe leerse como un conteo de incendios, superficie quemada o emisiones. Estos límites se indican en la interfaz y en este informe.

== Sostenibilidad

El acceso seguirá siendo gratuito y sin registro. El equipo planea sostener la plataforma mediante donaciones voluntarias, fondos de innovación e investigación ambiental, patrocinios tecnológicos y convenios de cooperación con universidades y organizaciones. Los costos se controlan precalculando agregados históricos y almacenando datos localmente, lo que evita descargas y procesamientos repetidos. Entre los posibles aliados se encuentran NASA FIRMS y Earthdata como proveedores de datos, universidades y especialistas como colaboradores científicos, autoridades ambientales y organizaciones de conservación para validar necesidades de usuario, y proveedores tecnológicos para infraestructura.

== Limitaciones y Trabajo Futuro

El diagnóstico de la Sección 6.3 establece las prioridades para la próxima versión:
+ *Recalibrar los factores exclusivos de MODIS* con observaciones emparejadas en cada ventana de paso satelital, y probar el resultado verificando que el índice por detección MODIS se mantenga constante a través de 2012.
+ *Corregir los años iniciales* normalizando MODIS por el número de plataformas MODIS activas, como ya hace el método para VIIRS, para que 2001 y 2002 sean comparables.
+ *Armonizar los datos en tiempo casi real* mediante las mismas etapas SQL, de modo que los meses recientes puedan sumarse a las comparaciones históricas.
+ *Considerar las oportunidades de observación* con información de nubes y pasos satelitales, para distinguir una detección faltante de una observación perdida @firmsnotes.
+ *Evaluar en datos reservados* ocultando observaciones VIIRS de años posteriores a 2012 y midiendo sesgo, error absoluto medio y raíz del error cuadrático medio del índice reconstruido, con incertidumbre mediante remuestreo por bloques.
+ *Publicar la versión en español de este informe y de la interfaz*, y añadir tutoriales para docentes y estudiantes.
