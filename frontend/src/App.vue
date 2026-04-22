<script setup lang="ts">
import ConfirmDialog from "primevue/confirmdialog"

import ToastContainer from "@/components/ToastContainer.vue"
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ConfirmDialog />
</template>
