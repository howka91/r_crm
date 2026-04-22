<script setup lang="ts">
/**
 * Main authenticated layout — vertical sidebar + floating navbar + scrollable
 * content. Used by all routes except Login and standalone error pages.
 *
 * Mirrors `yangi-mahalla-main/src/layouts/vertical/LayoutVertical.vue` by name
 * and role; implementation is simpler because the design is flatter.
 */
import Navbar from "@/layouts/components/Navbar.vue"
import Sidebar from "@/layouts/components/Sidebar.vue"
</script>

<template>
  <div class="min-h-screen w-full flex bg-ym-bg">
    <Sidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <Navbar />
      <main class="flex-1 overflow-auto art-scroll px-6 pb-6 pt-2">
        <RouterView />
      </main>
    </div>
  </div>
</template>
