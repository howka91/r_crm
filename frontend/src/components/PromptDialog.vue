<script setup lang="ts">
/**
 * Styled replacement for `window.prompt` — backed by `usePromptStore`.
 * One instance is mounted in App.vue; components never import this file
 * directly. See `store/prompt.ts` for the API.
 *
 * Keyboard: Escape → cancel (null), Enter → submit current value, except
 * in multiline mode where Ctrl/Cmd+Enter submits and plain Enter inserts
 * a line.
 */
import { computed, nextTick, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

import { usePromptStore } from "@/store/prompt"

const store = usePromptStore()
const { t } = useI18n()

const value = ref("")
const inputRef = ref<HTMLInputElement | HTMLTextAreaElement | null>(null)

watch(
  () => store.isOpen,
  (open) => {
    document.body.style.overflow = open ? "hidden" : ""
    if (open) {
      value.value = store.options?.defaultValue ?? ""
      nextTick(() => {
        inputRef.value?.focus()
        inputRef.value?.select?.()
      })
    }
  },
)

const canSubmit = computed(() => {
  if (!store.options?.required) return true
  return value.value.trim().length > 0
})

function submit() {
  if (!canSubmit.value) return
  store.resolve(value.value)
}

function cancel() {
  store.resolve(null)
}

function onKey(e: KeyboardEvent) {
  if (!store.isOpen) return
  if (e.key === "Escape") {
    e.preventDefault()
    cancel()
  } else if (e.key === "Enter") {
    // In multiline mode, plain Enter inserts a newline; Ctrl/Cmd+Enter
    // submits. In single-line mode, Enter always submits.
    if (store.options?.multiline && !(e.ctrlKey || e.metaKey)) return
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <Teleport to="body">
    <transition name="prompt">
      <div
        v-if="store.isOpen && store.options"
        class="fixed inset-0 z-[200] bg-black/40 flex items-center justify-center p-4"
        @keydown="onKey"
      >
        <div class="card w-full max-w-md p-6 shadow-ym-modal">
          <h2
            v-if="store.options.title"
            class="text-[16px] font-semibold mb-2 leading-snug"
          >
            {{ store.options.title }}
          </h2>
          <p
            v-if="store.options.message"
            class="text-[13px] text-ym-muted leading-snug mb-3"
          >
            {{ store.options.message }}
          </p>

          <textarea
            v-if="store.options.multiline"
            ref="inputRef as HTMLTextAreaElement | null"
            v-model="value"
            class="inp"
            rows="3"
            :placeholder="store.options.placeholder || ''"
            @keydown="onKey"
          />
          <input
            v-else
            ref="inputRef as HTMLInputElement | null"
            v-model="value"
            class="inp"
            type="text"
            :placeholder="store.options.placeholder || ''"
            @keydown="onKey"
          />

          <div class="mt-6 flex justify-end gap-2">
            <button class="btn btn-ghost" @click="cancel">
              {{ store.options.cancelLabel || t("common.cancel") }}
            </button>
            <button
              class="btn btn-primary"
              :disabled="!canSubmit"
              @click="submit"
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
.prompt-enter-active,
.prompt-leave-active {
  transition: opacity 150ms ease;
}
.prompt-enter-from,
.prompt-leave-to {
  opacity: 0;
}
</style>
