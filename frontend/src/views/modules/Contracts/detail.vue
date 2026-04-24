<script setup lang="ts">
/**
 * Contract detail screen — tabs: overview / schedule / payments / document.
 *
 * The overview tab exposes workflow transitions (send-to-wait / approve /
 * sign / request-edit / generate-schedule / generate-pdf). Each button
 * is gated by the matching backend permission *and* the current `action`
 * value (the workflow gate — see `contracts.services.transitions`). An
 * illegal transition returns 409 from the backend; we surface the server
 * message as a toast.
 */
import { AxiosError } from "axios"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import MoneyInput from "@/components/MoneyInput.vue"
import {
  contractTemplatesApi,
  contractsApi,
  paymentSchedulesApi,
  paymentsApi,
} from "@/api/contracts"
import { projectsApi } from "@/api/objects"
import { useConfirmStore } from "@/store/confirm"
import { usePromptStore } from "@/store/prompt"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type {
  Contract,
  ContractAction,
  ContractTemplate,
  ContractWrite,
  Payment,
  PaymentSchedule,
  PaymentScheduleStatus,
  Project,
} from "@/types/models"

type Tab = "overview" | "schedule" | "payments" | "document"

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()
const confirmStore = useConfirmStore()
const promptStore = usePromptStore()
const toastStore = useToastStore()

const contractId = computed(() => Number(route.params.id))

const contract = ref<Contract | null>(null)
const schedules = ref<PaymentSchedule[]>([])
const payments = ref<Payment[]>([])
const templates = ref<ContractTemplate[]>([])
const projects = ref<Project[]>([])
const activeTab = ref<Tab>("overview")
const busy = ref(false)

// Local drafts for text/money inputs — bound to <input> v-model so
// keystrokes don't trigger PATCH on every character. Synced from
// `contract.value` whenever it reloads. Committed on blur via
// `commitField`, which PATCHes only when the draft differs.
const totalAmountDraft = ref("")
const downPaymentDraft = ref("")
const descriptionDraft = ref("")

watch(
  contract,
  (c) => {
    if (!c) return
    totalAmountDraft.value = c.total_amount || ""
    downPaymentDraft.value = c.down_payment || ""
    descriptionDraft.value = c.description || ""
  },
  { immediate: true },
)

// --- Permissions ---------------------------------------------------------

const canEdit = computed(() => permissions.check("contracts.unsigned.edit"))
const canSendToWait = computed(() =>
  permissions.check("contracts.unsigned.send_to_wait"),
)
const canApprove = computed(() =>
  permissions.check("contracts.unsigned.approve"),
)
const canSign = computed(() => permissions.check("contracts.unsigned.sign"))
const canRequestEdit = computed(() =>
  permissions.check("contracts.unsigned.request_edit"),
)
const canGenSchedule = computed(() =>
  permissions.check("contracts.unsigned.generate_schedule"),
)
const canGenPdf = computed(() =>
  permissions.check("contracts.unsigned.generate_pdf"),
)

// --- Workflow gating (mirrors backend _ALLOWED in services/transitions) --

const allowedTransitions: Record<ContractAction, Set<ContractAction>> = {
  request: new Set(["wait"]),
  wait: new Set(["approve", "edit"]),
  edit: new Set(["wait"]),
  approve: new Set(["sign_in"]),
  sign_in: new Set(),
}

function canTransitionTo(target: ContractAction): boolean {
  const c = contract.value
  if (!c) return false
  return allowedTransitions[c.action]?.has(target) ?? false
}

// --- Derived data --------------------------------------------------------

function projectTitle(id: number): string {
  const p = projects.value.find((x) => x.id === id)
  if (!p) return `#${id}`
  return p.title[locale.value as "ru" | "uz" | "oz"] || `#${id}`
}

function templateTitle(id: number | null): string {
  if (id === null) return t("contracts.fields.template_none")
  const tpl = templates.value.find((x) => x.id === id)
  return tpl ? tpl.title : `#${id}`
}

function formatMoney(value: string | null | undefined): string {
  if (!value) return "0"
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n)
}

function scheduleChipClass(status: PaymentScheduleStatus): string {
  switch (status) {
    case "paid":
      return "chip chip-success"
    case "partial":
      return "chip chip-warn"
    case "overdue":
      return "chip chip-danger"
    default:
      return "chip chip-ghost"
  }
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

// --- Loading -------------------------------------------------------------

async function loadContract() {
  contract.value = await contractsApi.retrieve(contractId.value)
}

async function loadSchedules() {
  const resp = await paymentSchedulesApi.list({
    contract: contractId.value,
    limit: 500,
    ordering: "due_date",
  })
  schedules.value = resp.results
}

async function loadPayments() {
  if (schedules.value.length === 0) {
    payments.value = []
    return
  }
  // PaymentViewSet.filterset_fields only supports exact `schedule` match,
  // so we fan out one request per schedule id. A contract has at most a
  // few dozen rows; the extra round trips are cheap and parallel.
  const resps = await Promise.all(
    schedules.value.map((s) =>
      paymentsApi.list({ schedule: s.id, limit: 100 }),
    ),
  )
  payments.value = resps
    .flatMap((r) => r.results)
    .sort((a, b) => b.paid_at.localeCompare(a.paid_at))
}

async function loadSidecars() {
  const [tplResp, projResp] = await Promise.all([
    contractTemplatesApi.list({ limit: 200, is_active: "true" }),
    projectsApi.list({ limit: 200 }),
  ])
  templates.value = tplResp.results
  projects.value = projResp.results
}

async function reloadAll() {
  busy.value = true
  try {
    await loadContract()
    await loadSchedules()
    await loadPayments()
  } finally {
    busy.value = false
  }
}

// --- Workflow transitions ------------------------------------------------

async function runTransition(fn: () => Promise<Contract>, successKey?: string) {
  if (!contract.value) return
  busy.value = true
  try {
    contract.value = await fn()
    if (successKey) toastStore.success(t(successKey))
    // Schedule/payments may not be affected, but keep them fresh anyway
    // so the "generate-schedule" case also drops the table in.
    await loadSchedules()
    await loadPayments()
  } catch (e) {
    const msg =
      e instanceof AxiosError && e.response?.data
        ? (e.response.data as { detail?: string }).detail ||
          JSON.stringify(e.response.data)
        : t("errors.unknown")
    toastStore.error(msg)
  } finally {
    busy.value = false
  }
}

function sendToWait() {
  if (!contract.value) return
  runTransition(() => contractsApi.sendToWait(contract.value!.id))
}

function approve() {
  if (!contract.value) return
  runTransition(() => contractsApi.approve(contract.value!.id))
}

async function sign() {
  if (!contract.value) return
  const ok = await confirmStore.ask({
    title: t("contracts.detail.action_sign"),
    message: t("contracts.detail.confirm_sign"),
    severity: "danger",
    okLabel: t("contracts.detail.action_sign"),
  })
  if (!ok) return
  runTransition(() => contractsApi.sign(contract.value!.id))
}

async function requestEdit() {
  if (!contract.value) return
  const reason = await promptStore.ask({
    title: t("contracts.detail.action_request_edit"),
    message: t("contracts.detail.confirm_request_edit"),
    placeholder: t("contracts.detail.request_edit_placeholder"),
    multiline: true,
    required: true,
    okLabel: t("contracts.detail.action_request_edit"),
  })
  if (reason === null) return
  runTransition(() =>
    contractsApi.requestEdit(contract.value!.id, reason.trim()),
  )
}

async function genSchedule() {
  // Unlike workflow transitions, `generate-schedule` returns only the
  // rebuilt rows (`{count, schedule}`) — NOT the Contract. We must not
  // push that into `contract.value` or the whole detail card blanks
  // out. Just refresh the schedule/payments tabs from their own fetch.
  if (!contract.value) return
  busy.value = true
  try {
    await contractsApi.generateSchedule(contract.value.id)
    toastStore.success(t("contracts.detail.action_generate_schedule"))
    await loadSchedules()
    await loadPayments()
  } catch (e) {
    const msg =
      e instanceof AxiosError && e.response?.data
        ? (e.response.data as { detail?: string }).detail ||
          JSON.stringify(e.response.data)
        : t("errors.unknown")
    toastStore.error(msg)
  } finally {
    busy.value = false
  }
}

async function genPdf() {
  if (!contract.value) return
  busy.value = true
  try {
    const { contract: updated } = await contractsApi.generatePdf(
      contract.value.id,
    )
    contract.value = updated
    toastStore.success(t("contracts.detail.pdf_ready"))
  } catch (e) {
    const msg =
      e instanceof AxiosError && e.response?.data
        ? (e.response.data as { detail?: string }).detail ||
          JSON.stringify(e.response.data)
        : t("errors.unknown")
    toastStore.error(msg)
  } finally {
    busy.value = false
  }
}

// --- Inline field editing ------------------------------------------------
//
// Signed contracts are immutable (backend also enforces this — 409 on any
// write). Otherwise users with `contracts.unsigned.edit` can change
// date / description / sum / down_payment / is_mortgage without a full
// round-trip to the wizard. Each field saves optimistically on commit
// (blur for text/money, change for date/checkbox); on server error we
// roll back and toast the reason.

const editable = computed(
  () => !!contract.value && !contract.value.is_signed && canEdit.value,
)

async function savePatch(patch: Partial<ContractWrite>, revert: () => void) {
  if (!contract.value) return
  try {
    const updated = await contractsApi.update(contract.value.id, patch)
    contract.value = updated
  } catch (e) {
    revert()
    toastStore.error(
      e instanceof AxiosError && e.response?.data
        ? (e.response.data as { detail?: string }).detail ||
            JSON.stringify(e.response.data)
        : t("errors.unknown"),
    )
  }
}

/** Commit a field only if the input actually changed — avoids a PATCH
 *  request on every tab-out. Rolls back the optimistic write on failure. */
function commitField<K extends keyof Contract>(field: K, value: Contract[K]) {
  if (!contract.value) return
  const prev = contract.value[field]
  if (prev === value) return
  contract.value[field] = value
  void savePatch({ [field]: value } as unknown as Partial<ContractWrite>, () => {
    if (contract.value) contract.value[field] = prev
  })
}

function onDateChange(e: Event) {
  const v = (e.target as HTMLInputElement).value
  commitField("date", v)
}

function onMortgageChange(e: Event) {
  const v = (e.target as HTMLInputElement).checked
  commitField("is_mortgage", v)
}

function onTotalAmountBlur() {
  if (!contract.value) return
  commitField("total_amount", totalAmountDraft.value)
}

function onDownPaymentBlur() {
  if (!contract.value) return
  commitField("down_payment", downPaymentDraft.value)
}

function onDescriptionBlur() {
  if (!contract.value) return
  commitField("description", descriptionDraft.value)
}

// --- Template assignment -------------------------------------------------

async function setTemplate(value: string) {
  if (!contract.value) return
  const id = value === "" ? null : Number(value)
  const prev = contract.value.template
  contract.value.template = id
  try {
    const updated = await contractsApi.update(contract.value.id, {
      template: id,
    })
    contract.value = updated
  } catch (e) {
    contract.value.template = prev
    toastStore.error(
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown"),
    )
  }
}

function back() {
  router.push({ name: "contracts-unsigned" })
}

onMounted(async () => {
  await loadSidecars()
  await reloadAll()
})
</script>

<template>
  <div v-if="!contract && busy" class="text-ym-muted">
    {{ t("common.loading") }}
  </div>

  <div v-else-if="contract">
    <!-- Header -->
    <div class="flex items-start justify-between mb-5 mt-1 px-1 gap-4">
      <div class="flex items-start gap-3 flex-1 min-w-0">
        <button class="btn btn-ghost btn-sm" @click="back">
          <i class="pi pi-arrow-left text-[11px]" />
          {{ t("contracts.detail.back") }}
        </button>
        <div class="flex-1 min-w-0">
          <div
            class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle"
          >
            {{ t("nav.group_contracts") }}
          </div>
          <div class="flex items-center gap-3 flex-wrap">
            <h1
              class="text-[22px] font-semibold leading-none tracking-[-0.02em] mono"
            >
              <span v-if="contract.contract_number">
                {{ contract.contract_number }}
              </span>
              <span v-else class="text-ym-subtle italic">{{
                t("contracts.number_draft")
              }}</span>
            </h1>
            <span :class="actionChipClass(contract.action)">
              {{ t(`contracts.action.${contract.action}`) }}
            </span>
            <span v-if="contract.is_mortgage" class="chip chip-info">
              {{ t("contracts.filters.mortgage_yes") }}
            </span>
          </div>
          <div class="text-[13px] mt-2 text-ym-muted">
            {{ projectTitle(contract.project) }} ·
            {{ contract.apartment_number || "—" }} ·
            {{ contract.client_name || contract.signer_name }}
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-5 border-b border-ym-line-soft">
      <button
        v-for="tab in (['overview', 'schedule', 'payments', 'document'] as const)"
        :key="tab"
        class="px-4 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors"
        :class="
          activeTab === tab
            ? 'border-ym-primary text-ym-primary'
            : 'border-transparent text-ym-muted hover:text-ym-text'
        "
        @click="activeTab = tab"
      >
        {{ t(`contracts.detail.tabs.${tab}`) }}
      </button>
    </div>

    <!-- Overview -->
    <section v-if="activeTab === 'overview'" class="grid grid-cols-12 gap-4">
      <!-- Workflow -->
      <div class="col-span-12 lg:col-span-8 card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-3"
        >
          {{ t("contracts.detail.section_workflow") }}
        </div>
        <div class="text-[12px] text-ym-muted mb-3">
          {{ t("contracts.detail.workflow_hint") }}
        </div>
        <!--
          Show only transitions that are legal from the current state —
          mirrors the backend `_ALLOWED` table. Primary style is reserved
          for the most likely next forward step; secondary "soft" marks
          lateral moves like request-edit.
        -->
        <div class="flex flex-wrap gap-2">
          <button
            v-if="canSendToWait && canTransitionTo('wait')"
            class="btn btn-primary btn-sm"
            :disabled="busy"
            @click="sendToWait"
          >
            <i class="pi pi-send text-[11px]" />
            {{ t("contracts.detail.action_send_to_wait") }}
          </button>
          <button
            v-if="canApprove && canTransitionTo('approve')"
            class="btn btn-primary btn-sm"
            :disabled="busy"
            @click="approve"
          >
            <i class="pi pi-check text-[11px]" />
            {{ t("contracts.detail.action_approve") }}
          </button>
          <button
            v-if="canSign && canTransitionTo('sign_in')"
            class="btn btn-primary btn-sm"
            :disabled="busy"
            @click="sign"
          >
            <i class="pi pi-verified text-[11px]" />
            {{ t("contracts.detail.action_sign") }}
          </button>
          <button
            v-if="canRequestEdit && canTransitionTo('edit')"
            class="btn btn-soft btn-sm"
            :disabled="busy"
            @click="requestEdit"
          >
            <i class="pi pi-pencil text-[11px]" />
            {{ t("contracts.detail.action_request_edit") }}
          </button>
          <span class="flex-1" />
          <button
            v-if="canGenSchedule && !contract.is_signed"
            class="btn btn-ghost btn-sm"
            :disabled="busy"
            @click="genSchedule"
          >
            <i class="pi pi-calendar text-[11px]" />
            {{ t("contracts.detail.action_generate_schedule") }}
          </button>
        </div>
        <div
          v-if="contract.is_signed"
          class="mt-3 text-[12px] text-ym-warning flex items-center gap-1.5"
        >
          <i class="pi pi-lock text-[11px]" />
          {{ t("contracts.detail.signed_immutable") }}
        </div>
      </div>

      <!-- Money -->
      <div class="col-span-12 lg:col-span-4 card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-3"
        >
          {{ t("contracts.detail.section_money") }}
        </div>
        <div v-if="editable" class="space-y-3 text-[13px]">
          <div>
            <label class="block text-[12px] text-ym-muted mb-1">
              {{ t("contracts.fields.total_amount") }}
            </label>
            <MoneyInput
              v-model="totalAmountDraft"
              @blur="onTotalAmountBlur"
            />
          </div>
          <div>
            <label class="block text-[12px] text-ym-muted mb-1">
              {{ t("contracts.fields.down_payment") }}
            </label>
            <MoneyInput
              v-model="downPaymentDraft"
              @blur="onDownPaymentBlur"
            />
          </div>
          <label class="flex items-center gap-2 text-[12.5px] pt-1">
            <input
              type="checkbox"
              :checked="contract.is_mortgage"
              @change="onMortgageChange"
            />
            <span>{{ t("contracts.fields.is_mortgage") }}</span>
          </label>
        </div>
        <div v-else class="space-y-2 text-[13px]">
          <div class="flex justify-between">
            <span class="text-ym-muted">{{
              t("contracts.fields.total_amount")
            }}</span>
            <span class="font-mono font-medium">
              {{ formatMoney(contract.total_amount) }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-ym-muted">{{
              t("contracts.fields.down_payment")
            }}</span>
            <span class="font-mono font-medium">
              {{ formatMoney(contract.down_payment) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Parties -->
      <div class="col-span-12 lg:col-span-8 card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-3"
        >
          {{ t("contracts.detail.section_parties") }}
        </div>
        <dl class="grid grid-cols-2 gap-3 text-[13px]">
          <div>
            <dt class="text-ym-muted">{{ t("contracts.fields.project") }}</dt>
            <dd class="mt-0.5 font-medium">
              {{ projectTitle(contract.project) }}
            </dd>
          </div>
          <div>
            <dt class="text-ym-muted">{{ t("contracts.fields.apartment") }}</dt>
            <dd class="mt-0.5 font-mono">
              {{ contract.apartment_number || "—" }}
            </dd>
          </div>
          <div>
            <dt class="text-ym-muted">{{ t("contracts.columns.client") }}</dt>
            <dd class="mt-0.5 font-medium">{{ contract.client_name || "—" }}</dd>
          </div>
          <div>
            <dt class="text-ym-muted">{{ t("contracts.fields.signer") }}</dt>
            <dd class="mt-0.5">{{ contract.signer_name || "—" }}</dd>
          </div>
          <div>
            <dt class="text-ym-muted">{{ t("contracts.fields.date") }}</dt>
            <dd class="mt-0.5 font-mono">
              <input
                v-if="editable"
                type="date"
                class="inp inp-sm font-mono"
                :value="contract.date"
                @change="onDateChange"
              />
              <template v-else>{{ contract.date }}</template>
            </dd>
          </div>
          <div>
            <dt class="text-ym-muted">{{ t("contracts.columns.author") }}</dt>
            <dd class="mt-0.5">{{ contract.author_name || "—" }}</dd>
          </div>
        </dl>
      </div>

      <!-- Template picker -->
      <div class="col-span-12 lg:col-span-4 card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-3"
        >
          {{ t("contracts.fields.template") }}
        </div>
        <select
          :value="contract.template === null ? '' : contract.template"
          class="inp"
          :disabled="contract.is_signed || !canEdit"
          @change="setTemplate(($event.target as HTMLSelectElement).value)"
        >
          <option value="">{{ t("contracts.fields.template_none") }}</option>
          <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">
            {{ tpl.title }}
          </option>
        </select>
        <div class="mt-3 text-[12px] text-ym-muted">
          {{ templateTitle(contract.template) }}
        </div>
      </div>

      <!-- Description -->
      <div
        v-if="contract.description || editable"
        class="col-span-12 card p-5"
      >
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-2"
        >
          {{ t("contracts.detail.section_description") }}
        </div>
        <textarea
          v-if="editable"
          v-model="descriptionDraft"
          class="inp"
          rows="3"
          :placeholder="t('contracts.fields.description')"
          @blur="onDescriptionBlur"
        />
        <p v-else class="text-[13px] whitespace-pre-line">
          {{ contract.description }}
        </p>
      </div>
    </section>

    <!-- Schedule -->
    <section v-else-if="activeTab === 'schedule'">
      <div
        v-if="schedules.length === 0"
        class="card p-8 text-center text-ym-muted"
      >
        {{ t("contracts.detail.schedule_empty") }}
      </div>
      <div v-else class="card overflow-hidden">
        <table class="tbl">
          <thead>
            <tr>
              <th>#</th>
              <th>{{ t("contracts.columns.date") }}</th>
              <th class="text-right">{{ t("contracts.columns.total") }}</th>
              <th class="text-right">Оплачено</th>
              <th class="text-right">Остаток</th>
              <th>{{ t("contracts.columns.status") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in schedules" :key="row.id">
              <td class="text-ym-muted font-mono text-[12.5px]">{{ idx + 1 }}</td>
              <td class="font-mono text-[12.5px]">{{ row.due_date }}</td>
              <td class="text-right font-mono text-[12.5px]">
                {{ formatMoney(row.amount) }}
              </td>
              <td class="text-right font-mono text-[12.5px]">
                {{ formatMoney(row.paid_amount) }}
              </td>
              <td class="text-right font-mono text-[12.5px]">
                {{ formatMoney(row.debt) }}
              </td>
              <td>
                <span :class="scheduleChipClass(row.status)">
                  {{ t(`contracts.schedule_status.${row.status}`) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Payments -->
    <section v-else-if="activeTab === 'payments'">
      <div
        v-if="payments.length === 0"
        class="card p-8 text-center text-ym-muted"
      >
        {{ t("contracts.detail.payments_empty") }}
      </div>
      <div v-else class="card overflow-hidden">
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t("contracts.columns.date") }}</th>
              <th class="text-right">{{ t("contracts.columns.total") }}</th>
              <th>Канал</th>
              <th>Кто</th>
              <th>№ ПКО</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in payments" :key="p.id">
              <td class="font-mono text-[12.5px]">{{ p.paid_at }}</td>
              <td class="text-right font-mono text-[12.5px]">
                {{ formatMoney(p.amount) }}
              </td>
              <td>
                <span class="chip chip-ghost">{{
                  t(`contracts.payment_type.${p.payment_type}`)
                }}</span>
              </td>
              <td>{{ p.recorded_by_name || "—" }}</td>
              <td class="font-mono text-[12.5px]">
                {{ p.receipt_number || "—" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Document -->
    <section v-else-if="activeTab === 'document'" class="card p-5">
      <div v-if="contract.file" class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <i class="pi pi-file-pdf text-2xl text-ym-danger" />
          <div>
            <div class="text-[13px] font-medium">
              {{ t("contracts.detail.pdf_ready") }}
            </div>
            <div class="text-[11px] text-ym-muted mono break-all">
              {{ contract.file }}
            </div>
          </div>
        </div>
        <a :href="contract.file" target="_blank" class="btn btn-primary btn-sm">
          <i class="pi pi-download text-[11px]" />
          {{ t("contracts.detail.pdf_download") }}
        </a>
      </div>
      <div v-else class="text-ym-muted text-[13px] mb-4">
        {{ t("contracts.detail.no_file") }}
      </div>

      <div
        v-if="!contract.template"
        class="mt-4 text-[12px] text-ym-warning bg-ym-warning-soft/50 border border-ym-line-soft rounded p-3"
      >
        <i class="pi pi-info-circle text-[11px] mr-1" />
        {{ t("contracts.detail.no_template") }}
      </div>

      <button
        v-if="canGenPdf"
        class="btn btn-primary mt-4"
        :disabled="busy || !contract.template"
        @click="genPdf"
      >
        <i class="pi pi-refresh text-[11px]" />
        {{ t("contracts.detail.action_generate_pdf") }}
      </button>
    </section>
  </div>
</template>
