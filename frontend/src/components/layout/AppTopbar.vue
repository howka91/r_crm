<script setup lang="ts">
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { LOCALES, setLocale, type Locale } from "@/i18n"
import { useAuthStore } from "@/stores/auth"

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

function onLocaleChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as Locale
  setLocale(value)
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: "login" })
}
</script>

<template>
  <header class="app-topbar">
    <div class="flex-1" />
    <select
      :value="locale"
      class="border border-surface-300 dark:border-surface-700 rounded px-2 py-1 bg-transparent text-sm"
      @change="onLocaleChange"
    >
      <option v-for="(meta, code) in LOCALES" :key="code" :value="code">
        {{ meta.native }}
      </option>
    </select>
    <button
      type="button"
      class="text-sm px-3 py-1 rounded hover:bg-surface-100 dark:hover:bg-surface-800"
      @click="handleLogout"
    >
      {{ t("auth.sign_out") }}
    </button>
  </header>
</template>
