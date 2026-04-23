<script setup lang="ts">
/**
 * Recursive tree-of-toggles editor with tri-state parent checkboxes and
 * collapsible subtrees.
 *
 * Checkbox state for each node:
 *   * leaf              → plain checked / unchecked
 *   * parent, all descendant leaves on       → checked
 *   * parent, all descendant leaves off      → unchecked
 *   * parent, mixed descendants              → indeterminate (HTML
 *     `input.indeterminate = true`, no attribute exists for it)
 *
 * Click on any node cascades to every descendant — standard "select all"
 * ergonomics. Clicking an indeterminate parent enables every descendant.
 *
 * Expansion state is shared across recursive levels via provide/inject
 * (`permTreeExpanded`). Root caller (roleView.vue) provides a Ref<Set>
 * so "Expand all / Collapse all" reaches every level.
 */
import { inject, onMounted, provide, ref, watch, type Ref } from "vue"
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

// --- Shared expansion state -------------------------------------------
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

// --- Tri-state logic --------------------------------------------------

/** Collect every descendant key (including the node itself). */
function collectDescendants(node: PermissionNode): string[] {
  const out = [node.key]
  for (const child of node.children ?? []) out.push(...collectDescendants(child))
  return out
}

/** Collect only leaf-descendant keys — used to decide parent tri-state. */
function collectLeafDescendants(node: PermissionNode): string[] {
  if (!hasChildren(node)) return [node.key]
  const out: string[] = []
  for (const child of node.children ?? []) out.push(...collectLeafDescendants(child))
  return out
}

type TriState = "checked" | "unchecked" | "mixed"

function nodeState(node: PermissionNode): TriState {
  if (!hasChildren(node)) {
    return props.modelValue[node.key] ? "checked" : "unchecked"
  }
  const leaves = collectLeafDescendants(node)
  let on = 0
  let off = 0
  for (const key of leaves) {
    if (props.modelValue[key]) on++
    else off++
    // Early exit once we've seen both states.
    if (on > 0 && off > 0) return "mixed"
  }
  return on > 0 ? "checked" : "unchecked"
}

function toggleCheck(node: PermissionNode) {
  // Flip to the opposite of the majority: mixed or unchecked → enable all,
  // fully-checked → disable all. Matches every tri-state UI I've seen.
  const target = nodeState(node) !== "checked"
  const next = { ...props.modelValue }
  for (const key of collectDescendants(node)) next[key] = target
  emit("update:modelValue", next)
}

function label(node: PermissionNode): string {
  const loc = locale.value as "ru" | "uz" | "oz"
  return node.label[loc] || node.label.ru
}

// --- Applying `indeterminate` -----------------------------------------
// HTML has no `indeterminate` attribute — it's a DOM property only. After
// the checkbox renders (and on every state change), imperatively set it.

const rootRef = ref<HTMLElement | null>(null)

function applyIndeterminate() {
  const root = rootRef.value
  if (!root) return
  for (const node of props.nodes) {
    const el = root.querySelector<HTMLInputElement>(
      `input[data-perm-key="${CSS.escape(node.key)}"]`,
    )
    if (!el) continue
    const state = nodeState(node)
    el.indeterminate = state === "mixed"
    el.checked = state === "checked"
  }
}

onMounted(applyIndeterminate)
watch(() => props.modelValue, applyIndeterminate, { deep: true })
watch(() => props.nodes, applyIndeterminate)
</script>

<template>
  <ul
    ref="rootRef"
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
            :data-perm-key="node.key"
            @click.prevent="toggleCheck(node)"
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
