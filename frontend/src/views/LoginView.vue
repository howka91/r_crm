<script setup lang="ts">
import { AxiosError } from "axios"
import { ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref("")
const password = ref("")
const error = ref<string | null>(null)

async function handleSubmit() {
  error.value = null
  try {
    await auth.login(email.value, password.value)
    const next = typeof route.query.next === "string" ? route.query.next : "/"
    await router.push(next)
  } catch (e) {
    if (e instanceof AxiosError && e.response?.status === 401) {
      error.value = t("auth.invalid_credentials")
    } else {
      error.value = t("errors.unknown")
    }
  }
}
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center bg-surface-50 dark:bg-surface-950 px-4"
  >
    <div
      class="w-full max-w-sm bg-white dark:bg-surface-900 rounded-lg shadow p-8 border border-surface-200 dark:border-surface-800"
    >
      <div class="text-center mb-6">
        <div class="text-2xl font-semibold">{{ t("app.name") }}</div>
        <div class="text-sm text-surface-500 mt-1">{{ t("app.tagline") }}</div>
      </div>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label class="text-sm block mb-1">{{ t("auth.email") }}</label>
          <input
            v-model="email"
            type="email"
            required
            autocomplete="email"
            class="w-full border border-surface-300 dark:border-surface-700 rounded px-3 py-2 bg-transparent"
          />
        </div>
        <div>
          <label class="text-sm block mb-1">{{ t("auth.password") }}</label>
          <input
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            class="w-full border border-surface-300 dark:border-surface-700 rounded px-3 py-2 bg-transparent"
          />
        </div>

        <div v-if="error" class="text-sm text-red-600">
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="auth.loading"
          class="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium rounded px-4 py-2 disabled:opacity-50"
        >
          {{ t("auth.sign_in") }}
        </button>
      </form>
    </div>
  </div>
</template>
