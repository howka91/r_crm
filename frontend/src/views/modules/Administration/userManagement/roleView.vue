<script setup lang="ts">
/**
 * Role detail — edit the full permission tree.
 *
 * The tree is the single source of truth for what a role can do; the
 * previous separate "Разрешённые типы оплаты" card was folded into
 * `finance.payment_types.{bank,cash,barter}` tree nodes (see migration
 * users/0005).
 */
import { AxiosError } from "axios"
import { computed, onMounted, provide, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import { roleApi } from "@/api/administration"
import { usePermissionStore } from "@/store/permissions"
import type { PermissionNode, Role } from "@/types/models"

import PermissionTreeEditor from "./components/PermissionTreeEditor.vue"

// Single toggle: if anything is expanded, we're in "some-open" mode and the
// button offers to collapse everything. Otherwise it offers to expand all.

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()

const role = ref<Role | null>(null)
const perms = ref<Record<string, boolean>>({})
const saving = ref(false)
const saveError = ref<string | null>(null)

// Shared expansion state for the permission tree. Exposed to the recursive
// editor via provide so "Expand all / Collapse all" can reach every level.
const expandedKeys = ref<Set<string>>(new Set())
provide("permTreeExpanded", expandedKeys)

function walkTree(nodes: PermissionNode[], cb: (n: PermissionNode) => void) {
  for (const n of nodes) {
    cb(n)
    if (n.children) walkTree(n.children, cb)
  }
}

const allExpanded = computed(() => expandedKeys.value.size > 0)

function toggleAll() {
  if (allExpanded.value) {
    expandedKeys.value = new Set()
    return
  }
  const s = new Set<string>()
  walkTree(permissions.tree, (n) => {
    if (n.children && n.children.length) s.add(n.key)
  })
  expandedKeys.value = s
}

const roleId = computed(() => Number(route.params.id))

async function load() {
  const r = await roleApi.retrieve(roleId.value)
  role.value = r
  perms.value = { ...r.permissions }

  // Permission tree comes from the shared store.
  await permissions.loadTree()
}

async function save() {
  if (!role.value) return
  saving.value = true
  saveError.value = null
  try {
    const updated = await roleApi.update(role.value.id, {
      permissions: perms.value,
    })
    role.value = updated
    perms.value = { ...updated.permissions }
    // If the edited role is the current user's, refresh permission cache.
    permissions.setFromStaff({
      is_superuser: false,
      role: updated,
    })
  } catch (e) {
    saveError.value =
      e instanceof AxiosError
        ? JSON.stringify(e.response?.data ?? e.message)
        : t("errors.unknown")
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="role" class="space-y-6 max-w-4xl">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">{{ role.code }}</h1>
        <div class="text-sm text-ym-muted">{{ role.name.ru }}</div>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-ghost" @click="router.push({ name: 'admin-roles' })">
          {{ t("common.cancel") }}
        </button>
        <button :disabled="saving" class="btn btn-primary" @click="save">
          {{ t("common.save") }}
        </button>
      </div>
    </div>

    <!-- Permission tree -->
    <section class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold">Разрешения</h2>
        <button type="button" class="btn btn-ghost btn-xs" @click="toggleAll">
          <i
            :class="[
              'pi text-[10px]',
              allExpanded ? 'pi-angle-double-up' : 'pi-angle-double-down',
            ]"
          />
          {{ allExpanded ? "Свернуть всё" : "Развернуть всё" }}
        </button>
      </div>
      <div v-if="permissions.tree.length === 0" class="text-sm text-ym-muted">
        {{ t("common.loading") }}
      </div>
      <PermissionTreeEditor v-else v-model="perms" :nodes="permissions.tree" />
    </section>

    <div v-if="saveError" class="text-sm text-ym-danger">{{ saveError }}</div>
  </div>
  <div v-else class="text-ym-muted">{{ t("common.loading") }}</div>
</template>
