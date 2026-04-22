/**
 * Confirm store — Promise-based replacement for the native `window.confirm`.
 *
 * Usage inside any component method:
 *
 *     const ok = await useConfirmStore().ask({
 *       title: "Удалить этаж",
 *       message: "На этаже 12 квартир. Продолжить?",
 *       severity: "danger",
 *     })
 *     if (!ok) return
 *
 * Only one dialog is on screen at a time — calling `ask()` while another is
 * still open resolves the previous one with `false` (so callers never hang)
 * and replaces the options with the new request. That keeps the state
 * machine trivial for our use case (sequential destructive confirms).
 */
import { defineStore } from "pinia"
import { ref } from "vue"

export interface ConfirmOptions {
  title?: string
  message: string
  okLabel?: string
  cancelLabel?: string
  severity?: "default" | "danger"
}

export const useConfirmStore = defineStore("confirm", () => {
  const isOpen = ref(false)
  const options = ref<ConfirmOptions | null>(null)
  let resolver: ((ok: boolean) => void) | null = null

  function ask(opts: ConfirmOptions): Promise<boolean> {
    // If one is already open, resolve it false before replacing.
    if (resolver) {
      resolver(false)
      resolver = null
    }
    options.value = opts
    isOpen.value = true
    return new Promise<boolean>((resolve) => {
      resolver = resolve
    })
  }

  function resolve(ok: boolean) {
    isOpen.value = false
    if (resolver) {
      resolver(ok)
      resolver = null
    }
  }

  return { isOpen, options, ask, resolve }
})
