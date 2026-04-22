<script setup lang="ts">
/**
 * Floating toast stack, top-right. Mounted once at the app root.
 *
 * Each toast is a compact `.card` with a left colored stripe matching the
 * severity, an icon, and optional detail text. Auto-dismiss is handled by
 * the store; the × button is for impatient users.
 */
import { useToastStore, type ToastSeverity } from "@/store/toast"

const store = useToastStore()

function stripeClass(s: ToastSeverity): string {
  switch (s) {
    case "success":
      return "bg-ym-success"
    case "error":
      return "bg-ym-danger"
    case "info":
      return "bg-ym-info"
    case "warn":
      return "bg-ym-warning"
  }
}

function iconClass(s: ToastSeverity): string {
  switch (s) {
    case "success":
      return "pi pi-check-circle text-ym-success"
    case "error":
      return "pi pi-times-circle text-ym-danger"
    case "info":
      return "pi pi-info-circle text-ym-info"
    case "warn":
      return "pi pi-exclamation-triangle text-ym-warning"
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none w-full max-w-sm"
    >
      <transition-group name="toast">
        <div
          v-for="t in store.items"
          :key="t.id"
          class="pointer-events-auto card shadow-ym-modal flex items-stretch overflow-hidden"
        >
          <div :class="['w-1 flex-none', stripeClass(t.severity)]" />
          <div class="flex-1 px-4 py-3 flex items-start gap-3">
            <i :class="[iconClass(t.severity), 'text-[16px] mt-0.5 flex-none']" />
            <div class="flex-1 min-w-0">
              <div class="font-medium text-[13px] leading-tight">{{ t.summary }}</div>
              <div
                v-if="t.detail"
                class="text-[12px] text-ym-muted mt-1 break-words leading-snug"
              >
                {{ t.detail }}
              </div>
            </div>
            <button
              type="button"
              class="text-ym-subtle hover:text-ym-text flex-none"
              aria-label="Закрыть"
              @click="store.dismiss(t.id)"
            >
              <i class="pi pi-times text-[11px]" />
            </button>
          </div>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 180ms ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(12px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
