/**
 * vue-i18n setup. Mirrors `yangi-mahalla-main/src/libs/i18n/` from the legacy
 * project, adapted to vue-i18n v10 (Vue 3, legacy: false) and the project's
 * three locales: ru / uz / oz.
 */
import { createI18n } from "vue-i18n"

import oz from "./locales/oz.json"
import ru from "./locales/ru.json"
import uz from "./locales/uz.json"

export type Locale = "ru" | "uz" | "oz"

export const LOCALES: Record<Locale, { label: string; native: string }> = {
  ru: { label: "Русский", native: "Русский" },
  uz: { label: "Oʻzbekcha", native: "Oʻzbekcha" },
  oz: { label: "Ўзбекча", native: "Ўзбекча" },
}

const STORAGE_KEY = "rcrm.locale"

function detectInitialLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === "ru" || stored === "uz" || stored === "oz") return stored
  return "ru"
}

export const i18n = createI18n({
  legacy: false,
  locale: detectInitialLocale(),
  fallbackLocale: "ru",
  messages: { ru, uz, oz },
  missingWarn: false,
  fallbackWarn: false,
})

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale === "oz" ? "uz-Cyrl" : locale
}
