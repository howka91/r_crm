<script setup lang="ts">
import AppSidebar from "./AppSidebar.vue"
import AppTopbar from "./AppTopbar.vue"
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopbar />
      <main class="app-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
