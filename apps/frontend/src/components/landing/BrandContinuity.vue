<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, Layers3, ScanLine } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const steps = computed(() =>
  [0, 1, 2].map((i) => ({
    title: t(`landing.continuity.steps.${i}.title`),
    text: t(`landing.continuity.steps.${i}.text`),
  })),
)

const example = computed(() =>
  [0, 1, 2, 3].map((i) => ({
    sensor: t(`landing.continuity.exampleRows.${i}.sensor`),
    label: t(`landing.continuity.exampleRows.${i}.label`),
    weight: t(`landing.continuity.exampleRows.${i}.weight`),
  })),
)
</script>

<template>
  <section
    id="proyecto"
    class="landing-section landing-continuity"
    aria-labelledby="continuity-title"
  >
    <div class="landing-wrap">
      <div class="landing-section-heading">
        <h2 id="continuity-title">
          {{ t('landing.continuity.titleLine1') }}<br />{{ t('landing.continuity.titleLine2') }}
        </h2>
        <p>
          {{ t('landing.continuity.subtitle') }}
        </p>
      </div>
      <div class="landing-sensor-story">
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol"><Layers3 :size="26" aria-hidden="true" /></span>
            <div>
              <h3>{{ t('common.modis') }}</h3>
              <span class="landing-sensor-since">{{ t('landing.continuity.modisSince') }}</span>
            </div>
            <span class="landing-resolution">{{ t('landing.continuity.modisRes') }}</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-coarse"
            role="img"
            :aria-label="t('landing.continuity.modisAria')"
          >
            <i v-for="n in 24" :key="n" :class="{ active: [8, 9, 14, 15].includes(n) }" />
          </div>
          <p>{{ t('landing.continuity.modisDesc') }}</p>
        </article>
        <div class="landing-sensor-join" aria-hidden="true"><span>+</span></div>
        <article class="landing-sensor-column">
          <div class="landing-sensor-name">
            <span class="landing-sensor-symbol landing-sensor-symbol-blue"
              ><ScanLine :size="26" aria-hidden="true"
            /></span>
            <div>
              <h3>{{ t('common.viirs') }}</h3>
              <span class="landing-sensor-since">{{ t('landing.continuity.viirsSince') }}</span>
            </div>
            <span class="landing-resolution">{{ t('landing.continuity.viirsRes') }}</span>
          </div>
          <div
            class="landing-resolution-grid landing-grid-fine"
            role="img"
            :aria-label="t('landing.continuity.viirsAria')"
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
          <p>{{ t('landing.continuity.viirsDesc') }}</p>
        </article>
      </div>

      <div class="landing-method" aria-labelledby="method-title">
        <div class="landing-method-steps">
          <h3 id="method-title">{{ t('landing.continuity.howTitle') }}</h3>
          <ol>
            <li v-for="step in steps" :key="step.title">
              <strong>{{ step.title }}</strong>
              <p>{{ step.text }}</p>
            </li>
          </ol>
        </div>
        <figure class="landing-method-example">
          <figcaption>{{ t('landing.continuity.sampleCaption') }}</figcaption>
          <table>
            <caption class="landing-sr-only">
              {{ t('landing.continuity.sampleSrCaption') }}
            </caption>
            <thead>
              <tr>
                <th scope="col">{{ t('landing.continuity.colDetection') }}</th>
                <th scope="col">{{ t('landing.continuity.colWeight') }}</th>
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
                <th scope="row">{{ t('landing.continuity.harmonizedIndex') }}</th>
                <td>7.12</td>
              </tr>
            </tfoot>
          </table>
          <p>
            {{ t('landing.continuity.sampleNote') }}
          </p>
        </figure>
      </div>

      <div class="landing-harmonization-line">
        <p>
          <strong>{{ t('landing.continuity.linePrefix') }}</strong>
          {{ t('landing.continuity.lineText') }}
        </p>
        <a href="#datos" class="landing-text-link"
          >{{ t('landing.continuity.viewData') }} <ArrowDown :size="17" aria-hidden="true"
        /></a>
      </div>
    </div>
  </section>
</template>
