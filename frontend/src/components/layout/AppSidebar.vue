<script setup lang="ts">
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

import { usePermissionStore } from "@/stores/permissions"

interface NavItem {
  to: string
  labelKey: string
  icon: string
  permission?: string
}

const { t } = useI18n()
const permissions = usePermissionStore()

// Single, flat nav. Each item may require a permission; items without one are
// visible to everyone who's signed in. Items are filtered at render time.
const items: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: "pi-home" },
  { to: "/admin/users", labelKey: "nav.admin_users", icon: "pi-users", permission: "administration.users.view" },
  { to: "/admin/roles", labelKey: "nav.admin_permissions", icon: "pi-shield", permission: "administration.roles.view" },
]

const visible = computed(() =>
  items.filter((i) => !i.permission || permissions.check(i.permission)),
)
</script>

<template>
  <aside class="app-sidebar">
    <div class="h-14 flex items-center px-4 border-b border-surface-200 dark:border-surface-800">
      <span class="text-lg font-semibold">{{ t("app.name") }}</span>
    </div>
    <nav class="py-4">
      <ul>
        <li v-for="item in visible" :key="item.to">
          <RouterLink
            :to="item.to"
            class="flex items-center gap-3 px-4 py-2 text-sm hover:bg-surface-100 dark:hover:bg-surface-800"
            active-class="bg-primary-50 text-primary-700 dark:bg-primary-950"
          >
            <i :class="['pi', item.icon]" />
            <span>{{ t(item.labelKey) }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </aside>
</template>
