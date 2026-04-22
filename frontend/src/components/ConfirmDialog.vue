<script setup lang="ts">
/**
 * Styled replacement for `window.confirm` — backed by `useConfirmStore`.
 * One instance is mounted in App.vue; components never import this file
 * directly. See `store/confirm.ts` for the API.
 *
 * Keyboard: Escape → cancel, Enter → confirm. Backdrop click cancels.
 */
import { onMounted, onUnmounted, watch } from "vue"
import { useI18n } from "vue-i18n"

import { useConfirmStore } from "@/store/confirm"

const store = useConfirmStore()
const { t } = useI18n()

function onKey(e: KeyboardEvent) {
  if (!store.isOpen) return
  if (e.key === "Escape") {
    e.preventDefault()
    store.resolve(false)
  } else if (e.key === "Enter") {
    e.preventDefault()
    store.resolve(true)
  }
}

onMounted(() => window.addEventListener("keydown", onKey))
onUnmounted(() => window.removeEventListener("keydown", onKey))

// Lock body scroll while the dialog is open.
watch(
  () => store.isOpen,
  (open) => {
    document.body.style.overflow = open ? "hidden" : ""
  },
)
</script>

<template>
  <Teleport to="body">
    <transition name="confirm">
      <div
        v-if="store.isOpen && store.options"
        class="fixed inset-0 z-[200] bg-black/40 flex items-center justify-center p-4"
        @click.self="store.resolve(false)"
      >
        <div class="card w-full max-w-md p-6 shadow-ym-modal">
          <h2
            v-if="store.options.title"
            class="text-[16px] font-semibold mb-2 leading-snug"
          >
            {{ store.options.title }}
          </h2>
          <p class="text-[13.5px] text-ym-muted leading-snug">
            {{ store.options.message }}
          </p>
          <div class="mt-6 flex justify-end gap-2">
            <button class="btn btn-ghost" @click="store.resolve(false)">
              {{ store.options.cancelLabel || t("common.cancel") }}
            </button>
            <button
              :class="
                store.options.severity === 'danger'
                  ? 'btn btn-danger'
                  : 'btn btn-primary'
              "
              @click="store.resolve(true)"
            >
              {{ store.options.okLabel || t("common.confirm") }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.confirm-enter-active,
.confirm-leave-active {
  transition: opacity 150ms ease;
}
.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}
</style>
