<script setup lang="ts">
import { shallowRef, useTemplateRef } from 'vue'
import { ArrowUpRight, LogIn, Menu, User, X } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const menuOpen = shallowRef(false)
const menuToggle = useTemplateRef<HTMLButtonElement>('menu-toggle')
const links = [
  { label: 'The Project', href: '#proyecto' },
  { label: 'Data', href: '#datos' },
  { label: 'Audience', href: '#comunidad' },
  { label: 'Team', href: '#equipo' },
]
function closeMenu(returnFocus = false) {
  menuOpen.value = false
  if (returnFocus) menuToggle.value?.focus()
}
</script>

<template>
  <header class="landing-header" @keydown.esc="closeMenu(true)">
    <div class="landing-wrap landing-header-inner">
      <RouterLink
        :to="{ name: 'landing' }"
        class="landing-brand"
        aria-label="PyroTrace, home"
        @click="closeMenu()"
      >
        <PyroTraceLogo class="landing-logo" />
      </RouterLink>
      <nav class="landing-desktop-nav" aria-label="Primary navigation">
        <a v-for="link in links" :key="link.href" :href="link.href" class="landing-nav-link">{{
          link.label
        }}</a>
      </nav>
      <div class="landing-header-actions">
        <RouterLink
          v-if="authStore.isAuthenticated"
          :to="{ name: 'profile' }"
          class="landing-nav-link landing-header-login inline-flex items-center gap-1.5"
        >
          <User :size="15" aria-hidden="true" />
          <span>{{ authStore.user?.username }}</span>
        </RouterLink>
        <RouterLink
          v-else
          :to="{ name: 'login' }"
          class="landing-nav-link landing-header-login inline-flex items-center gap-1.5"
        >
          <LogIn :size="15" aria-hidden="true" />
          <span>Sign in</span>
        </RouterLink>
        <RouterLink :to="{ name: 'dashboard' }" class="landing-button landing-button-small"
          >Open Explorer <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
        <button
          ref="menu-toggle"
          type="button"
          class="landing-menu-toggle"
          :aria-expanded="menuOpen"
          aria-controls="landing-mobile-menu"
          :aria-label="menuOpen ? 'Close menu' : 'Open menu'"
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
      aria-label="Mobile navigation"
    >
      <a v-for="link in links" :key="link.href" :href="link.href" @click="closeMenu()"
        >{{ link.label }} <ArrowUpRight :size="20" aria-hidden="true"
      /></a>
      <RouterLink
        v-if="authStore.isAuthenticated"
        :to="{ name: 'profile' }"
        @click="closeMenu()"
      >
        Profile ({{ authStore.user?.username }}) <ArrowUpRight :size="20" aria-hidden="true" />
      </RouterLink>
      <RouterLink v-else :to="{ name: 'login' }" @click="closeMenu()">
        Sign in <ArrowUpRight :size="20" aria-hidden="true" />
      </RouterLink>
      <p>Satellite observation, within reach.</p>
    </nav>
  </header>
</template>
