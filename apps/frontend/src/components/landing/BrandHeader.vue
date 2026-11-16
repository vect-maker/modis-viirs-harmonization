<script setup lang="ts">
import { computed, shallowRef, useTemplateRef } from 'vue'
import { ArrowUpRight, LogIn, Menu, User, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import LocaleSwitcher from '@/components/common/LocaleSwitcher.vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()
const menuOpen = shallowRef(false)
const menuToggle = useTemplateRef<HTMLButtonElement>('menu-toggle')
const links = computed(() => [
  { label: t('nav.theProject'), href: '#proyecto' },
  { label: t('nav.data'), href: '#datos' },
  { label: t('nav.audience'), href: '#comunidad' },
  { label: t('nav.team'), href: '#equipo' },
])
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
        :aria-label="t('nav.brandHomeAria')"
        @click="closeMenu()"
      >
        <PyroTraceLogo class="landing-logo" />
      </RouterLink>
      <nav class="landing-desktop-nav" :aria-label="t('nav.primaryNavAria')">
        <a v-for="link in links" :key="link.href" :href="link.href" class="landing-nav-link">{{
          link.label
        }}</a>
      </nav>
      <div class="landing-header-actions">
        <LocaleSwitcher variant="landing" />
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
          <span>{{ t('nav.signIn') }}</span>
        </RouterLink>
        <RouterLink :to="{ name: 'dashboard' }" class="landing-button landing-button-small"
          >{{ t('nav.openExplorer') }} <ArrowUpRight :size="17" aria-hidden="true"
        /></RouterLink>
        <button
          ref="menu-toggle"
          type="button"
          class="landing-menu-toggle"
          :aria-expanded="menuOpen"
          aria-controls="landing-mobile-menu"
          :aria-label="menuOpen ? t('nav.closeMenu') : t('nav.openMenu')"
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
      :aria-label="t('nav.mobileNavAria')"
    >
      <a v-for="link in links" :key="link.href" :href="link.href" @click="closeMenu()"
        >{{ link.label }} <ArrowUpRight :size="20" aria-hidden="true"
      /></a>
      <RouterLink
        v-if="authStore.isAuthenticated"
        :to="{ name: 'profile' }"
        @click="closeMenu()"
      >
        {{ t('nav.profileWithUser', { username: authStore.user?.username }) }}
        <ArrowUpRight :size="20" aria-hidden="true" />
      </RouterLink>
      <RouterLink v-else :to="{ name: 'login' }" @click="closeMenu()">
        {{ t('nav.signIn') }} <ArrowUpRight :size="20" aria-hidden="true" />
      </RouterLink>
      <div class="pt-2">
        <LocaleSwitcher variant="landing" />
      </div>
      <p>{{ t('nav.mobileTagline') }}</p>
    </nav>
  </header>
</template>
