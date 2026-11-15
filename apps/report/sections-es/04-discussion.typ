= Discusión y Plan de Validación

== Interpretación del resultado actual

El resultado defendible es un flujo de trabajo experimental de ponderación de observaciones con entradas trazables y supuestos explícitos. Proporciona una base para probar reglas candidatas de armonización. Todavía no produce una serie histórica independiente del sensor.

Los principales problemas no resueltos son los efectos de límite de celdas fijas, la agrupación de múltiples plataformas sin normalización de exposición, la selección exclusiva de incendios codetectados para ciertas razones, la transferencia hacia condiciones de mañana y previas a 2012, los valores de respaldo no verificados y la falta de información de cobertura. La agregación a nivel de país también mezcla estaciones y ecosistemas.

El prototipo conserva todos los registros VIIRS, incluidas vistas separadas de actividad potencialmente persistente. Estas observaciones pueden ser valiosas para el monitoreo, pero deben distinguirse de incendios independientes y normalizarse adecuadamente para comparaciones a lo largo del tiempo.

== Limitaciones específicas de la FRP

Un único multiplicador de FRP no puede inferirse únicamente a partir de la resolución del píxel o de una diferencia entre valores medios de FRP por registro. Li et al. documentan relaciones que varían con la geometría de observación, el ecosistema, la estación y la escala de agregación @li2018. Su comparación corresponde a VIIRS de 750 m y MODIS de 1 km; sus coeficientes no deben transferirse directamente a este flujo de trabajo de 375 m.

Como verificación aritmética, aplicar el respaldo de 1.14 a la media reportada de MODIS de abril de 2011 de 32.92 MW da 37.53 MW. No transforma esa media en las medias aproximadas de 10-11 MW de registros posteriores con mezcla de sensores. Una población reconstruida de incendios más pequeños requeriría un objetivo estadístico y evidencia definidos por separado.

== Evaluación empírica propuesta

Lo siguiente es un plan, no un experimento completado.

+ *Especificar el objetivo.* Definir la actividad sobre un soporte espacial fijo, una plataforma de referencia y un horario de observación. Un objetivo provisional de tarde podría utilizar una plataforma VIIRS y observaciones emparejadas de Aqua durante un intervalo de solapamiento documentado. Las observaciones de Terra en la mañana deben mantenerse como un estrato separado hasta validar la transferencia.
+ *Controlar las entradas.* Registrar la colección del producto, la procedencia de calidad científica frente a NRT, los períodos de operación, la política de tipo de anomalía y los filtros de confianza. Preferir productos científicos estándar consistentes para el análisis, según recomienda FIRMS @firmsarchive. Conservar los valores crudos y cuantificar la fracción de observaciones excluidas o faltantes.
+ *Medir las oportunidades de observación.* Utilizar información de franja de barrido (swath) y máscaras de fuego/calidad para distinguir tierra despejada observada, nubes, adquisiciones faltantes y observaciones válidas sin fuego. Los conteos de días con al menos una detección no son denominadores de cobertura.
+ *Mejorar el emparejamiento de candidatos.* Usar una prueba de distancia métrica/geodésica, una tolerancia temporal móvil y las dimensiones de huella disponibles. Revisar celdas espaciales y temporales vecinas. Seleccionar tolerancias mediante análisis de sensibilidad en lugar de asumir un umbral universal.
+ *Ajustar y probar por separado.* Estimar relaciones por plataforma, estación, región/bioma y estrato día/noche donde el tamaño de muestra lo permita. Reservar años independientes o bloques espaciales para evaluación. Simular la inferencia histórica ocultando observaciones VIIRS del conjunto de evaluación. El ajuste basado únicamente en codetección debe evaluarse por sesgo de selección.
+ *Reportar incertidumbre y comparaciones.* Comparar el resultado ajustado frente a la agrupación cruda y líneas base separadas por sensor. Evaluar sesgo, MAE, RMSE, residuos temporales, sensibilidad a los límites e incertidumbre mediante remuestreo por bloques. Juzgar la mejora en datos reservados e inspeccionar si cualquier discontinuidad restante sigue los cambios de plataforma.

Para observaciones objetivo emparejadas $y_j$ y estimaciones $hat(y)_j$, las métricas propuestas son:
$ "Sesgo" = (1/n) sum_(j=1)^n (hat(y)_j-y_j) $
$ "MAE" = (1/n) sum_(j=1)^n abs(hat(y)_j-y_j) $
$ "RMSE" = sqrt((1/n) sum_(j=1)^n (hat(y)_j-y_j)^2) $

Aquí no se inventan umbrales numéricos de aceptación. Deben fijarse antes de la evaluación empírica, reflejar el uso previsto y exigir una mejora respecto a líneas base relevantes sin ocultar la incertidumbre.

== Condiciones para la entrega del prototipo

La interfaz puede demostrar patrones crudos y explicar el flujo experimental de ponderación. La demostración debe distinguir los valores crudos de los ponderados, divulgar el estado no verificado de cobertura y presentar los ejemplos sintéticos como sintéticos.

La bandera de procesamiento de exportación existente no debe interpretarse como prueba de validación. Una integración futura debe distinguir el estado de procesamiento, la versión de parámetros, la procedencia de calibración y el estado de validación científica. Las decisiones operativas de respuesta ante incendios y las conclusiones climáticas a largo plazo están fuera de la evidencia demostrada.
