<script setup lang="ts">
/**
 * "Full" layout — a transparent passthrough with no chrome.
 *
 * Used by public/standalone screens: login, 404, 403. Mirrors
 * `yangi-mahalla-main/src/@core/layouts/layout-full/LayoutFull.vue`.
 */
</script>

<template>
  <div class="min-h-screen w-full bg-ym-bg">
    <RouterView />
  </div>
</template>
