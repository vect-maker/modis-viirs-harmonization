<script setup lang="ts">
import { ArrowDown, Layers3, ScanLine } from '@lucide/vue'

const steps = [
  {
    title: 'Match',
    text: 'We pair MODIS and VIIRS detections of the same fire: within 2.2 km and less than one hour apart.',
  },
  {
    title: 'Weight each detection',
    text: 'Each VIIRS detection is split across the active VIIRS satellites that year. A MODIS detection also seen by VIIRS gets weight 0 to avoid double-counting. A MODIS-only detection receives a time-of-day factor calibrated per country from post-2012 overlaps.',
  },
  {
    title: 'Sum',
    text: 'The harmonized index is the sum of these weights in VIIRS-equivalent detections, making a year like 2005 directly comparable to 2024.',
  },
]

const example = [
  { sensor: 'viirs', label: 'Fire seen by Suomi-NPP', weight: '0.5' },
  { sensor: 'viirs', label: 'Same fire seen by NOAA-20', weight: '0.5' },
  { sensor: 'modis', label: 'Same fire seen by Aqua (MODIS)', weight: '0' },
  { sensor: 'modis', label: 'Another afternoon fire, MODIS only', weight: '6.12' },
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
        <h2 id="continuity-title">Two sensors,<br />one continuous record.</h2>
        <p>
          VIIRS detects many smaller fires that MODIS misses. Adding raw counts directly makes
          years since 2012 look artificially higher. Harmonization bridges that gap.
        </p>
      </div>
      <div class="landing-sensor-story">
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol"><Layers3 :size="26" aria-hidden="true" /></span>
            <div>
              <h3>MODIS</h3>
              <span class="landing-sensor-since">Terra &amp; Aqua, since 2000</span>
            </div>
            <span class="landing-resolution">~1 km pixel</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-coarse"
            role="img"
            aria-label="Diagram of an approximate 1 km MODIS pixel grid"
          >
            <i v-for="n in 24" :key="n" :class="{ active: [8, 9, 14, 15].includes(n) }" />
          </div>
          <p>The long historical record: over two decades to track how fire regimes evolve.</p>
        </article>
        <div class="landing-sensor-join" aria-hidden="true"><span>+</span></div>
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol landing-sensor-symbol-blue"
              ><ScanLine :size="26" aria-hidden="true"
            /></span>
            <div>
              <h3>VIIRS</h3>
              <span class="landing-sensor-since">Suomi-NPP &amp; NOAA-20, since 2012</span>
            </div>
            <span class="landing-resolution">375 m pixel</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-fine"
            role="img"
            aria-label="Diagram of a finer 375 m VIIRS pixel grid"
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
          <p>Higher spatial detail and sensitivity, producing more detections for the same fire.</p>
        </article>
      </div>

      <div class="landing-method" aria-labelledby="method-title">
        <div class="landing-method-steps">
          <h3 id="method-title">How we harmonize</h3>
          <ol>
            <li v-for="step in steps" :key="step.title">
              <strong>{{ step.title }}</strong>
              <p>{{ step.text }}</p>
            </li>
          </ol>
        </div>
        <figure class="landing-method-example">
          <figcaption>Sample overpass</figcaption>
          <table>
            <caption class="landing-sr-only">
              Weight assigned to each detection in the example
            </caption>
            <thead>
              <tr>
                <th scope="col">Detection</th>
                <th scope="col">Weight</th>
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
                <th scope="row">Harmonized index</th>
                <td>7.12</td>
              </tr>
            </tfoot>
          </table>
          <p>
            6.12 is the afternoon reference factor; each country uses its own calibrated factor when
            enough overlaps exist. Methodology remains under active validation.
          </p>
        </figure>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>The explorer shows both:</strong> raw detection counts and the harmonized index.
        </p>
        <a href="#datos" class="landing-text-link"
          >View the data <ArrowDown :size="17" aria-hidden="true"
        /></a>
      </div>
    </div>
  </section>
</template>
