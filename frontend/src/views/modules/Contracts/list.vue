<script setup lang="ts">
/**
 * Contracts list — shared view for three route names:
 *   contracts-unsigned        → is_signed=false
 *   contracts-signed          → is_signed=true
 *   contracts-edit-requests   → action=edit
 *
 * The `scope` is read from `route.meta.scope`, which is set in
 * `router/contracts.ts`. All three use the same rendering; only the
 * backend filter changes.
 */
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import { contractsApi } from "@/api/contracts"
import { projectsApi } from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import type { Contract, ContractAction, Project } from "@/types/models"

type Scope = "unsigned" | "signed" | "edit_requests"

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()

const scope = computed<Scope>(() => (route.meta.scope as Scope) || "unsigned")

const items = ref<Contract[]>([])
const projects = ref<Project[]>([])
const loading = ref(false)

const search = ref("")
const projectFilter = ref<number | "">("")
const mortgageFilter = ref<"" | "yes" | "no">("")

const canCreate = computed(() => permissions.check("contracts.unsigned.create"))

const titleKey = computed(() => `contracts.tabs_titles.${scope.value}`)
const subtitleKey = computed(() => `contracts.tabs_subtitles.${scope.value}`)

function projectLabel(p: Project): string {
  return p.title[locale.value as "ru" | "uz" | "oz"] || `#${p.id}`
}

function projectTitleById(id: number): string {
  const p = projects.value.find((x) => x.id === id)
  return p ? projectLabel(p) : `#${id}`
}

function actionChipClass(a: ContractAction): string {
  switch (a) {
    case "sign_in":
      return "chip chip-success"
    case "approve":
      return "chip chip-primary"
    case "wait":
      return "chip chip-info"
    case "edit":
      return "chip chip-warn"
    default:
      return "chip chip-ghost"
  }
}

function formatMoney(value: string): string {
  const n = Number(value)
  if (!Number.isFinite(n)) return value
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(n)
}

async function loadProjects() {
  const resp = await projectsApi.list({ limit: 200 })
  projects.value = resp.results
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { limit: 200, ordering: "-date" }
    if (scope.value === "signed") params.is_signed = "true"
    else if (scope.value === "unsigned") params.is_signed = "false"
    else if (scope.value === "edit_requests") params.action = "edit"

    if (projectFilter.value !== "") params.project = projectFilter.value
    if (search.value.trim()) params.search = search.value.trim()
    if (mortgageFilter.value === "yes") params.is_mortgage = "true"
    else if (mortgageFilter.value === "no") params.is_mortgage = "false"

    const data = await contractsApi.list(params)
    items.value = data.results
  } finally {
    loading.value = false
  }
}

function open(item: Contract) {
  router.push({ name: "contracts-detail", params: { id: item.id } })
}

function create() {
  router.push({ name: "contracts-new" })
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})
watch([projectFilter, mortgageFilter], () => void load())
watch(scope, () => void load())

onMounted(async () => {
  await loadProjects()
  await load()
})
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle"
        >
          {{ t("nav.group_contracts") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t(titleKey) }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t(subtitleKey) }}
        </div>
      </div>
      <button
        v-if="canCreate && scope === 'unsigned'"
        class="btn btn-primary"
        @click="create"
      >
        <i class="pi pi-plus text-[11px]" />
        {{ t("contracts.new") }}
      </button>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <div class="relative flex-1 min-w-[240px]">
        <i
          class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-ym-subtle text-[12px]"
        />
        <input
          v-model="search"
          class="inp pl-9"
          :placeholder="t('contracts.filters.search_placeholder')"
        />
      </div>
      <select v-model="projectFilter" class="inp w-[200px]">
        <option value="">{{ t("contracts.filters.project_all") }}</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">
          {{ projectLabel(p) }}
        </option>
      </select>
      <select v-model="mortgageFilter" class="inp w-[160px]">
        <option value="">{{ t("contracts.filters.mortgage_all") }}</option>
        <option value="yes">{{ t("contracts.filters.mortgage_yes") }}</option>
        <option value="no">{{ t("contracts.filters.mortgage_no") }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="items.length === 0"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("contracts.empty") }}
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("contracts.columns.number") }}</th>
            <th>{{ t("contracts.columns.project") }}</th>
            <th>{{ t("contracts.columns.apartment") }}</th>
            <th>{{ t("contracts.columns.client") }}</th>
            <th>{{ t("contracts.columns.date") }}</th>
            <th class="text-right">{{ t("contracts.columns.total") }}</th>
            <th>{{ t("contracts.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="i in items"
            :key="i.id"
            class="cursor-pointer"
            @click="open(i)"
          >
            <td class="font-mono text-[12.5px]">
              <span v-if="i.contract_number">{{ i.contract_number }}</span>
              <span v-else class="text-ym-subtle italic">{{
                t("contracts.number_draft")
              }}</span>
            </td>
            <td>{{ projectTitleById(i.project) }}</td>
            <td class="font-mono text-[12.5px]">{{ i.apartment_number || "—" }}</td>
            <td>{{ i.client_name || i.signer_name || "—" }}</td>
            <td class="text-ym-muted">{{ i.date }}</td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatMoney(i.total_amount) }}
            </td>
            <td>
              <span :class="actionChipClass(i.action)">
                {{ t(`contracts.action.${i.action}`) }}
              </span>
            </td>
            <td class="text-right whitespace-nowrap">
              <button class="btn btn-ghost btn-sm" @click.stop="open(i)">
                {{ t("common.edit") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
