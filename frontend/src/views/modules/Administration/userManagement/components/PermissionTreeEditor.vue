<script setup lang="ts">
/**
 * Recursive tree-of-toggles editor with collapsible parent nodes.
 *
 * `modelValue` is a flat `{dotted_key: boolean}` dict. Flipping a parent
 * checkbox cascades to every descendant (select-all ergonomics). Clicking
 * a chevron expands/collapses the subtree — leaf rows have no chevron.
 *
 * Expansion state is shared across the whole recursion via provide/inject.
 * The top-level caller (`roleView.vue`) provides `permTreeExpanded` as a
 * `Ref<Set<string>>`, so it can implement "expand-all / collapse-all"
 * buttons by mutating the same Set. If nothing is provided, the component
 * still works — it just creates its own local Set via provide().
 */
import { inject, provide, ref, type Ref } from "vue"
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
const currentDepth = props.depth ?? 0

// Shared expansion state. First instance in the tree creates the Set and
// provides it; recursive children inherit the same reference via inject.
const EXPANDED_KEY = "permTreeExpanded"
const injected = inject<Ref<Set<string>> | null>(EXPANDED_KEY, null)
const expanded: Ref<Set<string>> = injected ?? ref<Set<string>>(new Set())
if (!injected) provide(EXPANDED_KEY, expanded)

function hasChildren(node: PermissionNode): boolean {
  return !!node.children && node.children.length > 0
}

function isExpanded(key: string): boolean {
  return expanded.value.has(key)
}

function toggleExpand(key: string) {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}

function isChecked(key: string): boolean {
  return !!props.modelValue[key]
}

function collectDescendants(node: PermissionNode): string[] {
  const out = [node.key]
  for (const child of node.children ?? []) out.push(...collectDescendants(child))
  return out
}

function toggleCheck(node: PermissionNode, event: Event) {
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
      <div class="flex items-center gap-1.5">
        <!-- Chevron (only for parents) -->
        <button
          v-if="hasChildren(node)"
          type="button"
          class="w-5 h-5 inline-flex items-center justify-center rounded text-ym-subtle hover:bg-ym-sunken hover:text-ym-text transition-colors"
          :aria-label="isExpanded(node.key) ? 'collapse' : 'expand'"
          @click="toggleExpand(node.key)"
        >
          <i
            :class="[
              'pi text-[10px] transition-transform',
              isExpanded(node.key) ? 'pi-chevron-down' : 'pi-chevron-right',
            ]"
          />
        </button>
        <!-- Spacer for leaf rows so checkboxes line up with siblings -->
        <span v-else class="w-5 h-5" aria-hidden="true" />

        <label class="inline-flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            :checked="isChecked(node.key)"
            @change="toggleCheck(node, $event)"
          />
          <span :class="{ 'font-medium': currentDepth <= 1 }">
            {{ label(node) }}
          </span>
          <span class="text-xs text-ym-subtle font-mono">{{ node.key }}</span>
        </label>
      </div>

      <PermissionTreeEditor
        v-if="hasChildren(node) && isExpanded(node.key)"
        :nodes="node.children!"
        :model-value="modelValue"
        :depth="currentDepth + 1"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </li>
  </ul>
</template>
