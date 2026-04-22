<script setup lang="ts">
/**
 * Split-screen login — brand panel (2/3) + form (1/3).
 *
 * Reproduces `design_handoff_smart_rc/ds-screens.jsx#Login`:
 *  - Left (≥lg): deep-green gradient, two radial glows, rotated ghost shaxmatka
 *    overlay, logo with lime-accent tile, brand heading, footer.
 *  - Right: eyebrow + H1 "С возвращением", email + password (with eye icon),
 *    remember-me, primary submit, language chips at the bottom.
 *
 * Mobile / <lg: brand panel hidden, compact logo row shown inside the form.
 */
import { AxiosError } from "axios"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import { LOCALES, setLocale, type Locale } from "@/libs/i18n"
import { useAuthStore } from "@/store/auth"

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref("")
const password = ref("")
const remember = ref(false)
const showPassword = ref(false)
const error = ref<string | null>(null)

const localeCodes = Object.keys(LOCALES) as Locale[]

async function handleSubmit() {
  error.value = null
  try {
    await auth.login(email.value, password.value)
    const next = typeof route.query.next === "string" ? route.query.next : "/"
    await router.push(next)
  } catch (e) {
    if (e instanceof AxiosError && e.response?.status === 401) {
      error.value = t("auth.invalid_credentials")
    } else {
      error.value = t("errors.unknown")
    }
  }
}

/**
 * Ghost shaxmatka: 12×8 = 96 cells rotated behind the brand heading,
 * statuses cycle through free/booked/sold/action at 50% alpha.
 */
const ghostCells = computed(() => {
  const statuses = ["free", "booked", "sold", "free", "action", "free", "sold", "booked"]
  const colors: Record<string, string> = {
    free: "oklch(0.64 0.14 155 / .5)",
    booked: "oklch(0.74 0.15 75 / .5)",
    sold: "oklch(0.58 0.19 22 / .5)",
    action: "oklch(0.68 0.13 225 / .5)",
  }
  return Array.from({ length: 96 }, (_, i) => colors[statuses[i % 8]!]!)
})
</script>

<template>
  <div class="w-full min-h-screen flex bg-ym-bg">
    <!-- Brand panel (hidden on <lg) -->
    <div
      class="hidden lg:block flex-[2] relative overflow-hidden bg-ym-login-brand"
    >
      <!-- Radial glow overlay -->
      <div class="absolute inset-0 bg-ym-login-glow" />

      <!-- Ghost shaxmatka -->
      <div class="absolute inset-0 flex items-center justify-center opacity-30">
        <div
          class="grid grid-cols-8 gap-2 -rotate-[10deg] w-[90%]"
          aria-hidden="true"
        >
          <div
            v-for="(c, i) in ghostCells"
            :key="i"
            class="h-6 rounded-[4px]"
            :style="{ background: c }"
          />
        </div>
      </div>

      <!-- Content: logo (top), heading (middle), footer -->
      <div class="relative h-full flex flex-col justify-between p-12 text-white">
        <div class="flex items-center gap-2.5">
          <div
            class="w-10 h-10 rounded-[11px] flex items-center justify-center text-[14px] font-bold bg-ym-primary-accent tracking-[-0.06em]"
            style="color: oklch(0.22 0.08 155)"
          >
            YM
          </div>
          <div>
            <div class="text-[16px] font-semibold tracking-[-0.015em]">
              {{ t("app.name") }}
            </div>
            <div class="text-[11px] font-mono opacity-70">
              {{ t("app.product") }} · {{ t("app.version") }}
            </div>
          </div>
        </div>

        <div>
          <div
            class="text-[11px] uppercase tracking-[0.2em] font-mono opacity-70 mb-4"
          >
            {{ t("auth.brand_eyebrow") }}
          </div>
          <div
            class="text-[40px] font-semibold leading-[1.05] mb-4 tracking-[-0.03em]"
          >
            {{ t("auth.brand_heading_line1") }}<br />{{
              t("auth.brand_heading_line2")
            }}
          </div>
          <div class="text-[14px] opacity-75 max-w-md">
            {{ t("auth.brand_description") }}
          </div>
        </div>

        <div class="flex items-center gap-5 text-[12px] font-mono opacity-60">
          <span>{{ t("auth.copyright") }}</span>
          <span class="ml-auto">v {{ t("app.version") }}</span>
        </div>
      </div>
    </div>

    <!-- Form panel -->
    <div class="flex-1 flex items-center justify-center p-10">
      <div class="w-full max-w-[380px]">
        <!-- Compact logo (only on <lg) -->
        <div class="flex items-center gap-2.5 mb-10 lg:hidden">
          <div
            class="w-9 h-9 rounded-md flex items-center justify-center text-[14px] font-bold bg-ym-primary text-ym-primary-accent tracking-[-0.06em]"
          >
            YM
          </div>
          <div class="text-[15px] font-semibold">{{ t("app.name") }}</div>
        </div>

        <div
          class="text-[11px] uppercase tracking-[0.14em] font-mono mb-2 text-ym-subtle"
        >
          {{ t("auth.eyebrow") }}
        </div>
        <h1 class="text-[30px] font-semibold leading-tight mb-2 tracking-[-0.025em]">
          {{ t("auth.welcome_back") }}
        </h1>
        <div class="text-[14px] mb-8 text-ym-muted">
          {{ t("auth.enter_credentials") }}
        </div>

        <form class="space-y-4" @submit.prevent="handleSubmit">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("auth.email") }}
            </label>
            <input
              v-model="email"
              type="email"
              required
              autocomplete="email"
              class="inp"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-[12px] font-medium">
                {{ t("auth.password") }}
              </label>
              <a class="text-[12px] text-ym-primary hover:underline cursor-pointer">
                {{ t("auth.forgot") }}
              </a>
            </div>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                class="inp pr-10"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-ym-subtle hover:text-ym-text transition-colors"
                :aria-label="showPassword ? 'hide' : 'show'"
                @click="showPassword = !showPassword"
              >
                <i
                  :class="['pi', showPassword ? 'pi-eye-slash' : 'pi-eye', 'text-[12px]']"
                />
              </button>
            </div>
          </div>

          <label class="flex items-center gap-2 text-[13px] text-ym-muted">
            <input v-model="remember" type="checkbox" />
            {{ t("auth.remember_me") }}
          </label>

          <div v-if="error" class="text-[13px] text-ym-danger">{{ error }}</div>

          <button
            type="submit"
            :disabled="auth.loading"
            class="btn btn-primary w-full justify-center"
            style="padding: 11px 14px"
          >
            {{ t("auth.sign_in") }} →
          </button>
        </form>

        <!-- Language switcher -->
        <div
          class="mt-10 flex items-center gap-2 text-[12px] font-mono text-ym-subtle"
        >
          <span>{{ t("auth.language") }}:</span>
          <button
            v-for="code in localeCodes"
            :key="code"
            type="button"
            :class="['chip uppercase', code === locale ? 'chip-primary' : 'chip-ghost']"
            @click="setLocale(code)"
          >
            {{ code }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
