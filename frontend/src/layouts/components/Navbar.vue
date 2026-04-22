<script setup lang="ts">
/**
 * Floating top navbar — breadcrumbs + global search + notifications + locale switch.
 *
 * Mirrors `yangi-mahalla-main/src/layouts/components/Navbar.vue` conceptually,
 * adapted to Vue 3 + the new design tokens.
 */
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute } from "vue-router"

import { LOCALES, setLocale, type Locale } from "@/libs/i18n"

const { t, locale } = useI18n()
const route = useRoute()

/** route-name → trail of i18n keys for breadcrumbs (excluding the Home root,
 * which is prepended automatically). Falls back to the route name itself.
 */
const ROUTE_TRAIL: Record<string, string[]> = {
  dashboard: [],
  "admin-users": ["nav.admin_users"],
  "admin-roles": ["nav.admin_permissions"],
  "admin-role-edit": ["nav.admin_permissions"],
  "references-hub": ["nav.references"],
  "references-developers": ["nav.references", "nav.references_developers"],
  "references-sales-offices": ["nav.references", "nav.references_sales_offices"],
  "references-currencies": ["nav.references", "nav.references_currencies"],
  "references-lookups": ["nav.references", "nav.references_lookups"],
}

const crumbs = computed<string[]>(() => {
  const name = route.name?.toString()
  const home = t("nav.dashboard")
  if (!name || name === "dashboard") return [home]
  const trail = ROUTE_TRAIL[name]
  if (!trail) return [home, name]
  return [home, ...trail.map((k) => t(k))]
})

const locales = computed(() =>
  Object.entries(LOCALES).map(([code, meta]) => ({
    code: code as Locale,
    native: meta.native,
  })),
)

function cycleLocale() {
  const codes = locales.value.map((l) => l.code)
  if (codes.length === 0) return
  const idx = codes.indexOf(locale.value as Locale)
  const next = codes[(idx + 1) % codes.length]
  if (next) setLocale(next)
}

const currentLocaleLabel = computed(
  () => locales.value.find((l) => l.code === locale.value)?.native ?? locale.value,
)
</script>

<template>
  <header
    class="mx-6 mt-5 mb-2 h-14 flex items-center gap-4 px-5 rounded-lg bg-ym-surface border border-ym-line shadow-ym-float"
  >
    <!-- Breadcrumbs -->
    <nav class="flex items-center gap-2 text-[13px] text-ym-muted">
      <template v-for="(c, i) in crumbs" :key="i">
        <i v-if="i > 0" class="pi pi-angle-right text-[10px] text-ym-subtle" />
        <span :class="i === crumbs.length - 1 ? 'text-ym-text font-medium' : ''">{{
          c
        }}</span>
      </template>
    </nav>

    <div class="flex-1" />

    <!-- Search -->
    <div class="relative hidden md:block">
      <i
        class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-[12px] text-ym-subtle"
      />
      <input
        class="inp inp-sm w-[280px] pl-8"
        :placeholder="t('topbar.search_placeholder')"
      />
      <span
        class="absolute right-2.5 top-1/2 -translate-y-1/2 font-mono text-[10px] px-1.5 py-0.5 rounded bg-ym-sunken text-ym-subtle border border-ym-line"
        >⌘ K</span
      >
    </div>

    <!-- Notifications -->
    <button type="button" class="btn btn-ghost btn-icon" aria-label="notifications">
      <i class="pi pi-bell text-[13px]" />
    </button>

    <!-- Locale cycle -->
    <button
      type="button"
      class="btn btn-ghost btn-sm font-mono uppercase px-2.5"
      :title="currentLocaleLabel"
      @click="cycleLocale"
    >
      {{ locale }}
    </button>
  </header>
</template>
