<script setup lang="ts">
import { shallowRef, useTemplateRef } from 'vue'
import { ArrowUpRight, Menu, X } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'

const menuOpen = shallowRef(false)
const menuToggle = useTemplateRef<HTMLButtonElement>('menu-toggle')
const links = [
  { label: 'El proyecto', href: '#proyecto' },
  { label: 'Los datos', href: '#datos' },
  { label: 'Para quién', href: '#comunidad' },
]
function closeMenu(returnFocus = false) {
  menuOpen.value = false
  if (returnFocus) menuToggle.value?.focus()
}
</script>

<template>
  <header class="landing-header" @keydown.esc="closeMenu(true)">
    <div class="landing-wrap landing-header-inner">
      <RouterLink to="/" class="landing-brand" aria-label="PyroTrace, inicio" @click="closeMenu()">
        <PyroTraceLogo class="landing-logo" />
      </RouterLink>
      <nav class="landing-desktop-nav" aria-label="Navegación principal">
        <a v-for="link in links" :key="link.href" :href="link.href" class="landing-nav-link">{{
          link.label
        }}</a>
      </nav>
      <div class="landing-header-actions">
        <RouterLink to="/dashboard" class="landing-button landing-button-small"
          >Abrir explorador <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
        <button
          ref="menu-toggle"
          type="button"
          class="landing-menu-toggle"
          :aria-expanded="menuOpen"
          aria-controls="landing-mobile-menu"
          :aria-label="menuOpen ? 'Cerrar menú' : 'Abrir menú'"
          @click="menuOpen = !menuOpen"
        >
          <X v-if="menuOpen" :size="23" aria-hidden="true" /><Menu
            v-else
            :size="23"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
    <nav
      v-if="menuOpen"
      id="landing-mobile-menu"
      class="landing-mobile-nav"
      aria-label="Navegación móvil"
    >
      <a v-for="link in links" :key="link.href" :href="link.href" @click="closeMenu()"
        >{{ link.label }} <ArrowUpRight :size="20" aria-hidden="true"
      /></a>
      <p>Observación satelital, a tu alcance.</p>
    </nav>
  </header>
</template>
