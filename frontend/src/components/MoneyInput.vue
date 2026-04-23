<!--
  MoneyInput — numeric input with thousands separators for readability.

  Stores the clean Decimal string in v-model (e.g. "1250000.50") but
  displays it grouped with narrow-no-break spaces ("1 250 000,50"). Works
  with any `inp`-styled input and forwards arbitrary HTML attrs.
-->
<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{
  modelValue: string
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
}>()

// Narrow no-break space — screen readers ignore it, visually groups cleanly.
const SEP = "\u202F"

function formatForDisplay(raw: string): string {
  if (!raw) return ""
  // Split int + fraction on whichever separator the user used.
  const normalized = raw.replace(",", ".").trim()
  const parts = normalized.split(".")
  const intPart = parts[0] ?? ""
  const fracPart = parts[1]
  if (!intPart && !fracPart) return ""
  const sign = intPart.startsWith("-") ? "-" : ""
  const digits = (sign ? intPart.slice(1) : intPart).replace(/[^0-9]/g, "")
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, SEP)
  if (fracPart === undefined) return sign + grouped
  return sign + grouped + "," + fracPart.replace(/[^0-9]/g, "")
}

function parseFromDisplay(display: string): string {
  if (!display) return ""
  // Strip every non-digit except the fraction separator and leading minus.
  const trimmed = display.trim().replace(/[^\d,.\-]/g, "")
  const sign = trimmed.startsWith("-") ? "-" : ""
  const body = sign ? trimmed.slice(1) : trimmed
  // Pick the *last* . or , as the decimal separator so "1,250,000.50"
  // and "1 250 000,50" both collapse to "1250000.50".
  const dotIdx = body.lastIndexOf(".")
  const commaIdx = body.lastIndexOf(",")
  const fracIdx = Math.max(dotIdx, commaIdx)
  let intRaw: string
  let fracRaw = ""
  if (fracIdx === -1) {
    intRaw = body
  } else {
    intRaw = body.slice(0, fracIdx)
    fracRaw = body.slice(fracIdx + 1)
  }
  const intClean = intRaw.replace(/[^\d]/g, "")
  const fracClean = fracRaw.replace(/[^\d]/g, "")
  if (!intClean && !fracClean) return ""
  return sign + (intClean || "0") + (fracClean ? "." + fracClean : "")
}

const display = computed(() => formatForDisplay(props.modelValue))

function onInput(e: Event) {
  const value = (e.target as HTMLInputElement).value
  emit("update:modelValue", parseFromDisplay(value))
}
</script>

<template>
  <input
    class="inp font-mono"
    inputmode="decimal"
    :value="display"
    :placeholder="placeholder"
    :disabled="disabled"
    @input="onInput"
  />
</template>
