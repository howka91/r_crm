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

import { clientStatusesApi } from "@/api/clients"
import { contractsApi } from "@/api/contracts"
import { projectsApi } from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import type {
  ClientStatus,
  Contract,
  ContractAction,
  PaymentChannel,
  Project,
} from "@/types/models"

type Scope = "unsigned" | "signed" | "edit_requests"

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()

const scope = computed<Scope>(() => (route.meta.scope as Scope) || "unsigned")

const items = ref<Contract[]>([])
const projects = ref<Project[]>([])
const statuses = ref<ClientStatus[]>([])
const loading = ref(false)

const search = ref("")
const projectFilter = ref<number | "">("")
const mortgageFilter = ref<"" | "yes" | "no">("")
const statusFilter = ref<number | "">("")
const paymentTypeFilter = ref<"" | PaymentChannel>("")

const PAYMENT_TYPE_META: Record<PaymentChannel, { icon: string; tone: string }> = {
  cash: { icon: "pi-wallet", tone: "chip-success" },
  bank: { icon: "pi-building-columns", tone: "chip-info" },
  barter: { icon: "pi-arrows-h", tone: "chip-warn" },
}

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

function formatMoney(value: string | null): string {
  if (value === null || value === undefined || value === "") return "—"
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(n)
}

function formatArea(value: string | null): string {
  if (!value) return "—"
  const n = Number(value)
  if (!Number.isFinite(n)) return value
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(n)
}

function statusLabel(s: ClientStatus): string {
  return s.name[locale.value as "ru" | "uz" | "oz"] || `#${s.id}`
}

function clientStatusName(item: Contract): string {
  if (!item.client_status_name) return ""
  return (
    item.client_status_name[locale.value as "ru" | "uz" | "oz"] || ""
  )
}

function truncate(s: string | null, n = 30): string {
  if (!s) return ""
  return s.length > n ? `${s.slice(0, n)}…` : s
}

async function loadProjects() {
  const resp = await projectsApi.list({ limit: 200 })
  projects.value = resp.results
}

async function loadStatuses() {
  const resp = await clientStatusesApi.list({ limit: 200 })
  statuses.value = resp.results
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
    if (statusFilter.value !== "") params.signer__client__status = statusFilter.value
    if (paymentTypeFilter.value !== "") params.payment_type = paymentTypeFilter.value

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
watch(
  [projectFilter, mortgageFilter, statusFilter, paymentTypeFilter],
  () => void load(),
)
watch(scope, () => void load())

onMounted(async () => {
  await Promise.all([loadProjects(), loadStatuses()])
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
      <select v-model="statusFilter" class="inp w-[200px]">
        <option value="">{{ t("contracts.filters.status_all") }}</option>
        <option v-for="s in statuses" :key="s.id" :value="s.id">
          {{ statusLabel(s) }}
        </option>
      </select>
      <select v-model="paymentTypeFilter" class="inp w-[180px]">
        <option value="">{{ t("contracts.filters.payment_type_all") }}</option>
        <option value="cash">{{ t("contracts.payment_type.cash") }}</option>
        <option value="bank">{{ t("contracts.payment_type.bank") }}</option>
        <option value="barter">{{ t("contracts.payment_type.barter") }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="items.length === 0"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("contracts.empty") }}
    </div>

    <div v-else class="card overflow-x-auto">
      <table class="tbl min-w-[1600px]">
        <thead>
          <tr>
            <th>{{ t("contracts.columns.number") }}</th>
            <th>{{ t("contracts.columns.client") }}</th>
            <th>{{ t("contracts.columns.client_phone") }}</th>
            <th>{{ t("contracts.columns.client_status") }}</th>
            <th>{{ t("contracts.columns.project") }}</th>
            <th>{{ t("contracts.columns.apartment") }}</th>
            <th class="text-right">{{ t("contracts.columns.area") }}</th>
            <th class="text-right">{{ t("contracts.columns.price_per_sqm") }}</th>
            <th>{{ t("contracts.columns.date") }}</th>
            <th class="text-right">{{ t("contracts.columns.total") }}</th>
            <th class="text-right">{{ t("contracts.columns.down_payment") }}</th>
            <th class="text-right">{{ t("contracts.columns.monthly_payment") }}</th>
            <th class="text-right">{{ t("contracts.columns.monthly_debt") }}</th>
            <th class="text-right">{{ t("contracts.columns.remaining_debt") }}</th>
            <th>{{ t("contracts.columns.payment_types") }}</th>
            <th>{{ t("contracts.columns.client_note") }}</th>
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
            <td class="whitespace-nowrap">
              {{ i.client_name || i.signer_name || "—" }}
            </td>
            <td class="font-mono text-[12.5px] whitespace-nowrap">
              {{ i.client_phone || "—" }}
            </td>
            <td>
              <span
                v-if="i.client_status_id && i.client_status_name"
                class="chip"
                :style="{
                  backgroundColor: (i.client_status_color || '#94a3b8') + '22',
                  color: i.client_status_color || undefined,
                  borderColor: (i.client_status_color || '#94a3b8') + '55',
                }"
              >
                {{ clientStatusName(i) }}
              </span>
              <span v-else class="text-ym-subtle">—</span>
            </td>
            <td>{{ projectTitleById(i.project) }}</td>
            <td class="font-mono text-[12.5px]">
              {{ i.apartment_number || "—" }}
            </td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatArea(i.apartment_area) }}
            </td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatMoney(i.apartment_price_per_sqm) }}
            </td>
            <td class="text-ym-muted whitespace-nowrap">{{ i.date }}</td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatMoney(i.total_amount) }}
            </td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatMoney(i.down_payment) }}
            </td>
            <td class="text-right font-mono text-[12.5px]">
              {{ formatMoney(i.monthly_payment) }}
            </td>
            <td
              class="text-right font-mono text-[12.5px]"
              :class="Number(i.monthly_debt) > 0 ? 'text-red-600 font-semibold' : ''"
            >
              {{ formatMoney(i.monthly_debt) }}
            </td>
            <td
              class="text-right font-mono text-[12.5px]"
              :class="Number(i.remaining_debt) > 0 ? 'text-orange-600' : ''"
            >
              {{ formatMoney(i.remaining_debt) }}
            </td>
            <td>
              <div class="flex gap-1 flex-wrap">
                <span
                  v-for="pt in i.payment_types_used"
                  :key="pt"
                  class="chip"
                  :class="PAYMENT_TYPE_META[pt].tone"
                  :title="t(`contracts.payment_type.${pt}`)"
                >
                  <i :class="['pi', PAYMENT_TYPE_META[pt].icon, 'text-[10px]']" />
                  {{ t(`contracts.payment_type.${pt}`) }}
                </span>
                <span
                  v-if="i.payment_types_used.length === 0"
                  class="text-ym-subtle"
                  >—</span
                >
              </div>
            </td>
            <td
              class="max-w-[200px]"
              :title="i.client_note || ''"
            >
              <span v-if="i.client_note" class="text-[12.5px]">{{
                truncate(i.client_note, 30)
              }}</span>
              <span v-else class="text-ym-subtle">—</span>
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
