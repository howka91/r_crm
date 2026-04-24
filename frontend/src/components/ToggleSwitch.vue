<!--
  ToggleSwitch — boolean v-model rendered as an iOS-style sliding track.

  The native checkbox stays in the DOM (hidden via `.ym-switch-input`) so
  label-for targeting, form submission and keyboard focus keep working.
  When `activeLabel` + `inactiveLabel` are supplied we render the current
  state next to the switch and the whole row is clickable.
-->
<script setup lang="ts">
const props = defineProps<{
  // `undefined` is accepted so optional boolean fields (e.g.
  // `StaffWritePayload.is_active?: boolean`) bind without extra
  // massaging; we coerce to a real boolean for the checked state.
  modelValue: boolean | undefined
  activeLabel?: string
  inactiveLabel?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void
}>()

function onChange(e: Event) {
  emit("update:modelValue", (e.target as HTMLInputElement).checked)
}
</script>

<template>
  <label
    class="inline-flex items-center gap-2.5 cursor-pointer select-none"
    :class="{ 'opacity-60 cursor-not-allowed': disabled }"
  >
    <span class="ym-switch">
      <input
        type="checkbox"
        class="ym-switch-input"
        :checked="!!modelValue"
        :disabled="disabled"
        @change="onChange"
      />
      <span class="ym-switch-track" aria-hidden="true" />
    </span>
    <span
      v-if="activeLabel || inactiveLabel"
      class="text-[13px]"
      :class="!!modelValue ? 'text-ym-text font-medium' : 'text-ym-muted'"
    >
      {{ !!modelValue ? activeLabel : inactiveLabel }}
    </span>
  </label>
</template>
