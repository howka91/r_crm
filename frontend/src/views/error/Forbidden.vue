<script setup lang="ts">
/** 403 screen — shown when router guards reject the user's permission. */
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

const { t } = useI18n()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-ym-bg">
    <div class="text-center space-y-3">
      <div class="text-6xl font-bold text-ym-subtle">403</div>
      <div class="text-lg">{{ t("errors.forbidden") }}</div>
      <RouterLink to="/" class="text-ym-primary hover:underline">
        {{ t("common.back") }}
      </RouterLink>
    </div>
  </div>
</template>
