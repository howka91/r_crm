<script setup lang="ts">
import { useI18n } from "vue-i18n"

const { t } = useI18n()
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-semibold">{{ t("nav.dashboard") }}</h1>
    <p class="text-surface-600 dark:text-surface-400">
      Phase 0 scaffold. Real dashboard content lands in later phases.
    </p>
  </div>
</template>
