<script setup lang="ts">
/**
 * Recursive tree-of-toggles editor.
 *
 * `modelValue` is a flat `{dotted_key: boolean}` dict. Each tree node renders a
 * checkbox; flipping a parent cascades to all descendants (off disables children,
 * on turns them on too — standard "select all" ergonomics).
 *
 * Lives under `views/modules/Administration/userManagement/components/`
 * because it's module-specific — matches the Vuexy convention of keeping a
 * screen's helpers next to it. Promote out of `modules/` only when a second
 * module reuses it.
 */
import { computed } from "vue"
import { useI18n } from "vue-i18n"

import type { PermissionNode } from "@/types/models"

const props = defineProps<{
  nodes: PermissionNode[]
  modelValue: Record<string, boolean>
  depth?: number
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: Record<string, boolean>): void
}>()

const { locale } = useI18n()
const currentDepth = computed(() => props.depth ?? 0)

function isChecked(key: string): boolean {
  return !!props.modelValue[key]
}

function collectDescendants(node: PermissionNode): string[] {
  const out = [node.key]
  for (const child of node.children ?? []) out.push(...collectDescendants(child))
  return out
}

function toggle(node: PermissionNode, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  const next = { ...props.modelValue }
  for (const key of collectDescendants(node)) next[key] = checked
  emit("update:modelValue", next)
}

function label(node: PermissionNode): string {
  const loc = locale.value as "ru" | "uz" | "oz"
  return node.label[loc] || node.label.ru
}
</script>

<template>
  <ul
    :class="
      currentDepth === 0
        ? 'space-y-1'
        : 'pl-5 space-y-1 mt-1 border-l border-ym-line-soft'
    "
  >
    <li v-for="node in nodes" :key="node.key">
      <label class="inline-flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          :checked="isChecked(node.key)"
          @change="toggle(node, $event)"
        />
        <span :class="{ 'font-medium': currentDepth <= 1 }">
          {{ label(node) }}
        </span>
        <span class="text-xs text-ym-subtle font-mono">{{ node.key }}</span>
      </label>
      <PermissionTreeEditor
        v-if="node.children?.length"
        :nodes="node.children"
        :model-value="modelValue"
        :depth="currentDepth + 1"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </li>
  </ul>
</template>
