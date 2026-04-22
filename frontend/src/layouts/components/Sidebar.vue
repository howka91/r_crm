<script setup lang="ts">
/**
 * Vertical sidebar — Yangi Mahalla brand logo + grouped navigation + user card.
 *
 * Mirrors `yangi-mahalla-main/src/@core/layouts/layout-vertical/components/vertical-nav-menu/VerticalNavMenu.vue`
 * conceptually, adapted to Vue 3 <script setup> + the new design tokens.
 *
 * Menu items come from `@/navigation/vertical`, NOT hardcoded here.
 */
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

import navigation from "@/navigation/vertical"
import { useAuthStore } from "@/store/auth"
import { usePermissionStore } from "@/store/permissions"

const { t } = useI18n()
const permissions = usePermissionStore()
const auth = useAuthStore()

const visibleGroups = computed(() =>
  navigation
    .map((g) => ({
      ...g,
      children: g.children.filter((i) => !i.permission || permissions.check(i.permission)),
    }))
    .filter((g) => g.children.length > 0),
)

const userInitials = computed(() => {
  const staff = auth.user
  if (!staff) return "?"
  const source = staff.full_name || staff.email || ""
  const parts = source.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "?"
  return parts
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
})

const userDisplayName = computed(() => auth.user?.full_name || auth.user?.email || "")
const userRoleLabel = computed(() => auth.user?.role?.code ?? "")
</script>

<template>
  <aside
    class="w-[252px] shrink-0 flex flex-col bg-ym-surface border-r border-ym-line"
  >
    <!-- Logo row -->
    <div class="h-16 flex items-center gap-2.5 px-5 border-b border-ym-line">
      <div
        class="w-9 h-9 rounded-md flex items-center justify-center text-[14px] font-bold relative overflow-hidden bg-ym-primary text-ym-primary-accent shadow-ym-primary-lg tracking-tightest"
      >
        YM
      </div>
      <div class="leading-tight min-w-0">
        <div class="text-[14.5px] font-semibold truncate tracking-[-0.015em]">
          {{ t("app.name") }}
        </div>
        <div class="text-[10.5px] font-mono truncate text-ym-subtle">
          {{ t("app.product") }} · {{ t("app.version") }}
        </div>
      </div>
    </div>

    <!-- Nav groups -->
    <nav class="p-3 flex-1 overflow-auto art-scroll">
      <div v-for="group in visibleGroups" :key="group.headerKey" class="mb-1">
        <div class="nav-header">{{ t(group.headerKey) }}</div>
        <template v-for="item in group.children" :key="item.titleKey">
          <RouterLink
            v-if="item.to && !item.disabled"
            :to="item.to"
            class="nav-item"
            exact-active-class="is-active"
          >
            <i :class="['pi', item.icon, 'text-[13px] w-3.5']" />
            <span class="truncate">{{ t(item.titleKey) }}</span>
          </RouterLink>
          <span
            v-else
            class="nav-item opacity-50 cursor-not-allowed"
            :aria-disabled="true"
          >
            <i :class="['pi', item.icon, 'text-[13px] w-3.5']" />
            <span class="truncate">{{ t(item.titleKey) }}</span>
          </span>
        </template>
      </div>
    </nav>

    <!-- User card -->
    <div
      v-if="auth.user"
      class="p-3 m-3 rounded-xl flex items-center gap-2.5 bg-ym-sunken border border-ym-line-soft"
    >
      <div
        class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 bg-ym-primary text-ym-primary-accent"
      >
        {{ userInitials }}
      </div>
      <div class="min-w-0 flex-1">
        <div class="text-[12.5px] font-medium truncate">{{ userDisplayName }}</div>
        <div
          v-if="userRoleLabel"
          class="text-[10.5px] font-mono truncate text-ym-subtle"
        >
          {{ userRoleLabel }}
        </div>
      </div>
      <button
        type="button"
        class="shrink-0 text-ym-subtle hover:text-ym-text transition-colors"
        :title="t('auth.sign_out')"
        @click="auth.logout()"
      >
        <i class="pi pi-sign-out text-xs" />
      </button>
    </div>
  </aside>
</template>
