/**
 * Permission store.
 *
 * Loads the canonical permission tree from the backend once (on first auth)
 * and exposes a `check(dottedKey)` function that mirrors backend semantics:
 * the key and every ancestor in the role's permissions dict must be True.
 *
 * Also syncs CASL so `v-if="$can('do', 'clients.view')"` works in templates.
 */
import { defineStore } from "pinia"
import { computed, ref } from "vue"

import { permissionsApi } from "@/api/endpoints/permissions"
import { ability } from "@/plugins/casl"
import type { PermissionNode, RoleBrief } from "@/types/models"

export const usePermissionStore = defineStore("permissions", () => {
  const tree = ref<PermissionNode[]>([])
  const rolePerms = ref<Record<string, boolean>>({})
  const isSuperuser = ref(false)

  const isLoaded = computed(() => tree.value.length > 0)

  async function loadTree(): Promise<void> {
    if (isLoaded.value) return
    tree.value = await permissionsApi.getTree()
  }

  function setFromStaff(staff: { is_superuser: boolean; role: RoleBrief | null } | null): void {
    if (!staff) {
      isSuperuser.value = false
      rolePerms.value = {}
      ability.update([])
      return
    }
    isSuperuser.value = staff.is_superuser
    rolePerms.value = staff.role?.permissions ?? {}
    syncCasl()
  }

  function check(dottedKey: string): boolean {
    if (isSuperuser.value) return true
    const perms = rolePerms.value
    const parts = dottedKey.split(".")
    for (let i = 1; i <= parts.length; i++) {
      const prefix = parts.slice(0, i).join(".")
      if (!perms[prefix]) return false
    }
    return true
  }

  function syncCasl(): void {
    if (isSuperuser.value) {
      ability.update([{ action: "manage", subject: "all" }])
      return
    }
    // Each granted permission becomes an "access" rule for CASL, keyed by the
    // dotted string. Components use `$can('access', 'clients.view')`.
    const rules = Object.entries(rolePerms.value)
      .filter(([key]) => check(key)) // only truly-granted (ancestors on)
      .map(([key]) => ({ action: "access", subject: key }))
    ability.update(rules)
  }

  function clear(): void {
    rolePerms.value = {}
    isSuperuser.value = false
    ability.update([])
  }

  return {
    tree,
    rolePerms,
    isSuperuser,
    isLoaded,
    loadTree,
    setFromStaff,
    check,
    clear,
  }
})
