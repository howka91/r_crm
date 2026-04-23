<script setup lang="ts">
import ConfirmDialog from "@/components/ConfirmDialog.vue"
import PromptDialog from "@/components/PromptDialog.vue"
import ToastContainer from "@/components/ToastContainer.vue"
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ConfirmDialog />
  <PromptDialog />
</template>
