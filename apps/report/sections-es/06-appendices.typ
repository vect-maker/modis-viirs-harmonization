#heading(outlined: false, numbering: none)[Agradecimientos]

PyroTrace utiliza productos de NASA FIRMS y software de código abierto. Las referencias documentan los productos fuente y el contexto metodológico; no implican respaldo de la NASA a los coeficientes de ponderación del proyecto.

#heading(outlined: false, numbering: none)[Referencias]

#bibliography("../references.bib", style: "ieee", title: none)

#v(0.6em)
#set heading(numbering: "A.1")
#counter(heading).update(0)

= Reproducibilidad y Disponibilidad de Datos

Los archivos fuente se encuentran en la copia actual del proyecto. Las cuatro etapas de ponderación están en #raw("apps/pipeline/sql/harmonize/"). No se dispuso de los archivos Parquet originales a nivel de país para la presente revisión.

Una demostración en video del prototipo PyroTrace y su panel de control está disponible en #link("https://youtu.be/WKN75RAhiKw")[https://youtu.be/WKN75RAhiKw].

Ejecutar desde la raíz del repositorio en PowerShell:
#raw("cd apps/report\npython validation/verify_prototype.py", block: true)

Para actualizar la instantánea de evidencia incluida en este informe, agregue la bandera #raw("--refresh-report-data") al comando de Python. Revise los resultados modificados y su interpretación antes de hacerlo.

El ejecutor escribe su espacio de trabajo sintético y sus salidas legibles por máquina bajo el directorio de salida ignorado del informe. Verifica la preservación de campos nativos, los resultados exactos de los escenarios y los cambios en los factores de calibración. La instantánea confirmada registra los hashes SHA-256 de los cuatro archivos SQL. Si esos archivos cambian, vuelva a ejecutar las verificaciones y revise la interpretación científica antes de actualizar la instantánea.

Para compilar el informe usando la instalación existente de Typst:
#raw("$pdf = 'output/report-es.pdf'\ntypst compile --font-path fonts main-es.typ $pdf", block: true)

Las recetas del proyecto también proveen #raw("just report::build-es"), #raw("just report::build"), #raw("just report::preview") y #raw("just report::watch") desde la raíz del repositorio en Git Bash. Liberation Serif se incluye con su licencia; New Computer Modern es provisto por Typst.

#colbreak()

= Registro de Verificación de Fuentes

Las fuentes primarias fueron verificadas el 14 de noviembre de 2026. Los atributos de producto y la guía específica de cada colección prevalecen sobre descripciones genéricas. La bibliografía proporciona URLs estables de las fuentes y DOIs de los artículos.

La página actual de archivo de FIRMS lista la disponibilidad de NOAA-20 desde abril de 2018, mientras que la página general de descripción de VIIRS lista enero de 2020. Este informe utiliza la página de archivo para la disponibilidad histórica.

La guía de Colección 2 de 2024 se utiliza para la interpretación de recuperación de VIIRS. El artículo de algoritmo de 2014 aporta contexto histórico del algoritmo, no evidencia de que el archivo local utilice una colección particular. El estudio de Li et al. de 2018 es explícitamente una comparación de 750 m.

La URL corregida del desafío está registrada en la documentación metodológica complementaria. Su título fue verificado en metadatos oficiales indexados; la recuperación directa de la página no estuvo disponible durante esta revisión. Constituye contexto del proyecto y no evidencia científica.

Ninguna fuente primaria revisada establece los valores 2.20, 6.12, 4.50 o 1.14 como constantes de calibración transferibles para este prototipo. Se eliminaron los umbrales mínimos universales de FRP y las afirmaciones sobre una cuadrícula isotrópica exacta.
