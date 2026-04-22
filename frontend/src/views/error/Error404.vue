<script setup lang="ts">
/** Mirrors `yangi-mahalla-main/src/views/error/Error404.vue`. */
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

const { t } = useI18n()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-ym-bg">
    <div class="text-center space-y-3">
      <div class="text-6xl font-bold text-ym-subtle">404</div>
      <div class="text-lg">{{ t("errors.not_found") }}</div>
      <RouterLink to="/" class="text-ym-primary hover:underline">
        {{ t("common.back") }}
      </RouterLink>
    </div>
  </div>
</template>
