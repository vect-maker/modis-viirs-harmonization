<script setup lang="ts">
import { ArrowDown, Layers3, ScanLine } from '@lucide/vue'

const steps = [
  {
    title: 'Emparejar',
    text: 'Buscamos detecciones MODIS y VIIRS del mismo fuego: a menos de 2.2 km y con menos de una hora de diferencia.',
  },
  {
    title: 'Dar un peso a cada punto',
    text: 'Cada detección VIIRS se reparte entre los satélites VIIRS activos ese año. Una detección MODIS que VIIRS también vio vale 0, porque ya está contada. Una que VIIRS no vio vale un factor según la hora de paso, calculado para cada país con las coincidencias desde 2012.',
  },
  {
    title: 'Sumar',
    text: 'El índice armonizado es la suma de los pesos, en detecciones equivalentes VIIRS. Así un año de 2005 se puede comparar con uno de 2024.',
  },
]

const example = [
  { sensor: 'viirs', label: 'Fuego visto por Suomi-NPP', weight: '0.5' },
  { sensor: 'viirs', label: 'El mismo fuego visto por NOAA-20', weight: '0.5' },
  { sensor: 'modis', label: 'El mismo fuego visto por Aqua (MODIS)', weight: '0' },
  { sensor: 'modis', label: 'Otro fuego, de tarde, solo en MODIS', weight: '6.12' },
]
</script>

<template>
  <section
    id="proyecto"
    class="landing-section landing-continuity"
    aria-labelledby="continuity-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="continuity-title">Dos sensores,<br />una sola serie.</h2>
        <p>
          VIIRS detecta muchos fuegos pequeños que MODIS no ve. Si se suman sin más, los años
          desde 2012 parecen tener mucho más fuego. Armonizar corrige esa diferencia.
        </p>
      </div>
      <div class="landing-sensor-story">
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol"><Layers3 :size="26" aria-hidden="true" /></span>
            <div>
              <h3>MODIS</h3>
              <span class="landing-sensor-since">Terra y Aqua, desde 2000</span>
            </div>
            <span class="landing-resolution">píxel de ~1 km</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-coarse"
            role="img"
            aria-label="Esquema de una cuadrícula MODIS de aproximadamente un kilómetro"
          >
            <i v-for="n in 24" :key="n" :class="{ active: [8, 9, 14, 15].includes(n) }" />
          </div>
          <p>El registro largo: más de dos décadas para ver cómo cambia la actividad de fuego.</p>
        </article>
        <div class="landing-sensor-join" aria-hidden="true"><span>+</span></div>
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol landing-sensor-symbol-blue"
              ><ScanLine :size="26" aria-hidden="true"
            /></span>
            <div>
              <h3>VIIRS</h3>
              <span class="landing-sensor-since">Suomi-NPP y NOAA-20, desde 2012</span>
            </div>
            <span class="landing-resolution">píxel de 375 m</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-fine"
            role="img"
            aria-label="Esquema de una cuadrícula VIIRS de 375 metros, con mayor detalle espacial"
          >
            <i
              v-for="n in 160"
              :key="n"
              :class="{
                active: [51, 52, 67, 68, 69, 83, 84, 85, 86, 98, 99, 100, 101, 115, 116].includes(
                  n,
                ),
              }"
            />
          </div>
          <p>Más detalle y más sensibilidad, por eso cuenta más puntos para el mismo fuego.</p>
        </article>
      </div>

      <div class="landing-method" aria-labelledby="method-title">
        <div class="landing-method-steps">
          <h3 id="method-title">Cómo armonizamos</h3>
          <ol>
            <li v-for="step in steps" :key="step.title">
              <strong>{{ step.title }}</strong>
              <p>{{ step.text }}</p>
            </li>
          </ol>
        </div>
        <figure class="landing-method-example">
          <figcaption>Ejemplo de una pasada</figcaption>
          <table>
            <caption class="landing-sr-only">
              Peso de cada detección en el ejemplo
            </caption>
            <thead>
              <tr>
                <th scope="col">Detección</th>
                <th scope="col">Peso</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in example" :key="row.label">
                <th scope="row">
                  <span :class="row.sensor === 'viirs' ? 'viirs-dot' : 'modis-dot'" />
                  {{ row.label }}
                </th>
                <td>{{ row.weight }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Índice armonizado</th>
                <td>7.12</td>
              </tr>
            </tfoot>
          </table>
          <p>
            6.12 es el factor de referencia para la tarde; cada país usa el suyo cuando tiene
            suficientes coincidencias. El método sigue en validación.
          </p>
        </figure>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>El explorador muestra las dos cosas:</strong> el conteo crudo de detecciones y
          el índice armonizado.
        </p>
        <a href="#datos" class="landing-text-link"
          >Ver los datos <ArrowDown :size="17" aria-hidden="true"
        /></a>
      </div>
    </div>
  </section>
</template>
