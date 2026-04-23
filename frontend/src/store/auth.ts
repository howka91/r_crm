/**
 * Auth store (Pinia setup-syntax).
 *
 * Lives under `src/store/` — one file per domain. This mirrors the legacy
 * `yangi-mahalla-main/src/store/` folder at the directory level; internally
 * the Vuex `{state, mutations, actions, getters}` quartet collapses into a
 * single setup-syntax Pinia store (idiomatic Pinia, see ARCHITECTURE.md).
 */
import { defineStore } from "pinia"
import { computed, ref } from "vue"

import { authApi } from "@/api/auth"
import { tokenStore } from "@/libs/axios"
import { setLocale } from "@/libs/i18n"
import { usePermissionStore } from "@/store/permissions"
import type { Staff } from "@/types/models"

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Staff | null>(null)
  const loading = ref(false)
  const initialized = ref(false) // we've run fetchMe at least once this session

  const isAuthenticated = computed(() => user.value !== null)

  async function login(loginValue: string, password: string): Promise<void> {
    loading.value = true
    try {
      const { access, refresh, user: signedIn } = await authApi.login({
        login: loginValue,
        password,
      })
      tokenStore.set(access, refresh)
      applyUser(signedIn)
    } finally {
      loading.value = false
    }
  }

  /** Pull `/auth/me/` using the stored access token. Silent-fails on bad token. */
  async function fetchMe(): Promise<void> {
    initialized.value = true
    if (!tokenStore.getAccess()) {
      applyUser(null)
      return
    }
    try {
      applyUser(await authApi.me())
    } catch {
      applyUser(null)
    }
  }

  async function logout(): Promise<void> {
    const refresh = tokenStore.getRefresh()
    if (refresh) {
      try {
        await authApi.logout()
      } catch {
        /* blacklist failure is non-fatal — we still drop local state */
      }
    }
    tokenStore.clear()
    applyUser(null)
  }

  function applyUser(staff: Staff | null): void {
    user.value = staff
    const permissions = usePermissionStore()
    permissions.setFromStaff(staff)
    if (staff) {
      setLocale(staff.language)
      // Load the permission tree lazily on first sign-in.
      permissions.loadTree().catch(() => {
        /* non-fatal — admin UI will show error */
      })
    }
  }

  return { user, loading, initialized, isAuthenticated, login, fetchMe, logout }
})
