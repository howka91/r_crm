/**
 * Prompt store — Promise-based replacement for the native `window.prompt`.
 *
 * Usage inside any component method:
 *
 *     const reason = await usePromptStore().ask({
 *       title: "Запросить правку",
 *       message: "Укажите причину:",
 *       placeholder: "Пример: несоответствие адреса",
 *       required: true,
 *     })
 *     if (reason === null) return  // user hit cancel / Esc
 *
 * Only one dialog is on screen at a time — calling `ask()` while another
 * is still open resolves the previous one with `null` (matches native
 * `prompt` when cancelled) before replacing the options.
 *
 * API mirrors the shape of `useConfirmStore` so the mental model is the
 * same across the app.
 */
import { defineStore } from "pinia"
import { ref } from "vue"

export interface PromptOptions {
  title?: string
  message?: string
  placeholder?: string
  /** Default value prefilled in the input. */
  defaultValue?: string
  okLabel?: string
  cancelLabel?: string
  /** If true, empty input blocks the OK button. */
  required?: boolean
  /** Render a `<textarea>` instead of an `<input>` (for long reasons). */
  multiline?: boolean
}

export const usePromptStore = defineStore("prompt", () => {
  const isOpen = ref(false)
  const options = ref<PromptOptions | null>(null)
  let resolver: ((value: string | null) => void) | null = null

  function ask(opts: PromptOptions): Promise<string | null> {
    if (resolver) {
      resolver(null)
      resolver = null
    }
    options.value = opts
    isOpen.value = true
    return new Promise<string | null>((resolve) => {
      resolver = resolve
    })
  }

  function resolve(value: string | null) {
    isOpen.value = false
    if (resolver) {
      resolver(value)
      resolver = null
    }
  }

  return { isOpen, options, ask, resolve }
})
