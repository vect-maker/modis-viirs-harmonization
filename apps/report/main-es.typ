#import "template.typ": paper

#show: paper.with(
  title: "PyroTrace: Prototipo experimental de ponderación MODIS-VIIRS para calendarios históricos de actividad de incendios",
  authors: ("Equipo del proyecto PyroTrace",),
  date: "14 de noviembre de 2026 | Informe técnico del prototipo",
  lang: "es",
  abstract: [
    Los registros de incendios activos de NASA FIRMS combinan instrumentos con distintos tamaños de píxel, respuestas de detección y horarios de observación. PyroTrace explora un flujo de trabajo de ponderación que preserva los puntos originales para calendarios históricos de actividad de incendios. Cuatro etapas en DuckDB SQL conservan los atributos nativos, agrupan observaciones por celdas espaciales aproximadas y hora UTC, estiman razones a nivel de país y asignan pesos experimentales junto con una potencia radiativa del fuego (FRP) derivada. Documentamos las ecuaciones implementadas, distinguimos las propiedades publicadas de los productos de los parámetros seleccionados por el proyecto y reproducimos limitaciones conocidas sobre 810 registros sintéticos. Los límites de celdas fijas y las plataformas VIIRS adicionales modifican el índice resultante incluso cuando la actividad simulada se mantiene constante. Estas verificaciones establecen el comportamiento ejecutable y la preservación de metadatos, pero no demuestran exactitud científica. El entregable es un prototipo de software transparente con un plan explícito de validación. Su índice ponderado no debe interpretarse como un conteo de incendios independientes, superficie quemada ni una tendencia comprobada independiente del sensor.
  ],
  keywords: "NASA FIRMS, MODIS, VIIRS, prototipo, incendios activos, ponderación, reproducibilidad",
)

#include "sections-es/01-introduction.typ"
#include "sections-es/02-methods.typ"
#include "sections-es/03-results.typ"
#include "sections-es/04-discussion.typ"
#include "sections-es/05-conclusions.typ"
#include "sections-es/06-appendices.typ"
