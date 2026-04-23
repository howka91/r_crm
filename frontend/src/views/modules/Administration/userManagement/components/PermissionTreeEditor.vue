<script setup lang="ts">
/**
 * Recursive tree-of-toggles editor with tri-state parent checkboxes and
 * collapsible subtrees.
 *
 * Checkbox state for each node:
 *   * leaf              → plain checked / unchecked
 *   * parent, all descendant leaves on       → checked
 *   * parent, all descendant leaves off      → unchecked
 *   * parent, mixed descendants              → indeterminate (filled square)
 *
 * Click cascades to every descendant. Clicking a mixed or unchecked parent
 * enables the whole subtree; clicking a fully-checked parent disables it.
 *
 * Implementation note:
 *   * We use `@change` (not `@click.prevent`) so the browser performs its
 *     own toggle first; our handler then reads the *previous* modelValue,
 *     computes the cascade target and emits. Vue re-renders `:checked` to
 *     reconcile. This "controlled checkbox" pattern is the idiomatic way
 *     to keep DOM and reactive state in sync — `@click.prevent` turned out
 *     to leave the DOM `.checked` property desynced under some label-click
 *     flows in Chromium.
 *   * `indeterminate` has no HTML attribute — only a DOM property. A
 *     lightweight custom directive (`v-indeterminate`) sets it imperatively
 *     on `mounted` and `updated`, which is what Vue template-ref callbacks
 *     don't reliably do (those only fire on mount / unmount).
 *
 * Expansion state is shared across levels via provide/inject
 * (`permTreeExpanded`). Root caller (roleView.vue) provides a Ref<Set>
 * so "Expand / Collapse all" reaches every depth.
 */
import { inject, provide, ref, type Directive, type Ref } from "vue"
import { useI18n } from "vue-i18n"

import type { PermissionNode } from "@/types/models"

/**
 * `v-indeterminate="boolean"` — reflects the value into
 * `input.indeterminate` on mount and every subsequent vnode patch.
 * Local to this component because nothing else needs it today.
 */
const vIndeterminate: Directive<HTMLInputElement, boolean> = {
  mounted(el, binding) {
    el.indeterminate = !!binding.value
  },
  updated(el, binding) {
    el.indeterminate = !!binding.value
  },
}

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

/** All keys in the subtree rooted at `node`, including `node.key`. */
function collectDescendants(node: PermissionNode): string[] {
  const out = [node.key]
  for (const child of node.children ?? []) out.push(...collectDescendants(child))
  return out
}

/** Leaf-only descendants — used to determine tri-state of parent. */
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
  let on = 0
  let off = 0
  for (const key of collectLeafDescendants(node)) {
    if (props.modelValue[key]) on++
    else off++
    if (on > 0 && off > 0) return "mixed"
  }
  return on > 0 ? "checked" : "unchecked"
}

function isChecked(node: PermissionNode): boolean {
  return nodeState(node) === "checked"
}

function isMixed(node: PermissionNode): boolean {
  return nodeState(node) === "mixed"
}

function toggleCheck(node: PermissionNode) {
  // Fully-checked → disable subtree. Mixed or unchecked → enable subtree.
  const target = nodeState(node) !== "checked"
  const next = { ...props.modelValue }
  for (const key of collectDescendants(node)) next[key] = target
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
            :checked="isChecked(node)"
            v-indeterminate="isMixed(node)"
            @change="toggleCheck(node)"
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
