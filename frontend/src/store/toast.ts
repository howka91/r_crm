/**
 * Toast store — floating notifications using the Yangi Mahalla design tokens.
 *
 * PrimeVue's Toast was registered in `main.ts` but the project runs it in
 * `unstyled` mode with an empty preset, so those toasts rendered as bare
 * unstyled nodes. This store drives a local `ToastContainer.vue` that uses
 * `.card` + the `ym-*` palette for a consistent look.
 *
 * API mirrors PrimeVue's shape (`severity`, `summary`, `detail`, `life`)
 * so switching back to PrimeVue later is trivial — just swap the import.
 */
import { defineStore } from "pinia"
import { ref } from "vue"

export type ToastSeverity = "success" | "error" | "info" | "warn"

export interface ToastItem {
  id: number
  severity: ToastSeverity
  summary: string
  detail?: string
  life: number
}

export const useToastStore = defineStore("toast", () => {
  const items = ref<ToastItem[]>([])
  let nextId = 1

  function show(
    severity: ToastSeverity,
    summary: string,
    detail?: string,
    life = 4000,
  ): number {
    const id = nextId++
    items.value.push({ id, severity, summary, detail, life })
    if (life > 0) {
      window.setTimeout(() => dismiss(id), life)
    }
    return id
  }

  function dismiss(id: number) {
    items.value = items.value.filter((t) => t.id !== id)
  }

  // Convenience wrappers with sensible defaults (errors live longer).
  const success = (summary: string, detail?: string) =>
    show("success", summary, detail, 3500)
  const error = (summary: string, detail?: string) =>
    show("error", summary, detail, 6000)
  const info = (summary: string, detail?: string) =>
    show("info", summary, detail, 4000)
  const warn = (summary: string, detail?: string) =>
    show("warn", summary, detail, 5000)

  return { items, show, dismiss, success, error, info, warn }
})
