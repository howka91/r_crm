<script setup lang="ts">
/**
 * Contract creation wizard — 4 steps.
 *
 *   1. Project + Apartment
 *   2. Client (by search) + Signer (ClientContact of client)
 *   3. Calculation (optional) + Template + money + description
 *   4. Review + submit
 *
 * On submit the contract is created in `request` state (draft) without a
 * contract_number. The number is minted on the first `send-to-wait`
 * transition (see `apps/contracts/services/numbering.py`).
 */
import { AxiosError } from "axios"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import MoneyInput from "@/components/MoneyInput.vue"
import { contractTemplatesApi, contractsApi } from "@/api/contracts"
import { clientContactsApi, clientsApi } from "@/api/clients"
import {
  apartmentsApi,
  buildingsApi,
  calculationsApi,
  floorsApi,
  projectsApi,
  sectionsApi,
} from "@/api/objects"
import { useToastStore } from "@/store/toast"
import type {
  Apartment,
  Calculation,
  Client,
  ClientContact,
  ContractTemplate,
  ContractWrite,
  Project,
} from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()
const toastStore = useToastStore()

const step = ref<1 | 2 | 3 | 4>(1)
const creating = ref(false)
const createError = ref<string | null>(null)

// --- Step 1: project + apartment ----------------------------------------

const projects = ref<Project[]>([])
const apartments = ref<Apartment[]>([])
const selectedProject = ref<number | null>(null)
const selectedApartment = ref<number | null>(null)
const loadingApartments = ref(false)

async function loadProjects() {
  const resp = await projectsApi.list({ limit: 200 })
  projects.value = resp.results
}

// Load every Apartment inside a project by walking
// building → section → floor → apartment. It's the same traversal the
// Shaxmatka page does; we can't filter Apartment by project directly
// (Apartment.floor.section.building.project).
async function loadApartmentsForProject(projectId: number) {
  loadingApartments.value = true
  apartments.value = []
  try {
    const bs = await buildingsApi.list({ project: projectId, limit: 200 })
    const sectionResps = await Promise.all(
      bs.results.map((b) =>
        sectionsApi.list({ building: b.id, limit: 200 }),
      ),
    )
    const sections = sectionResps.flatMap((r) => r.results)
    const floorResps = await Promise.all(
      sections.map((s) => floorsApi.list({ section: s.id, limit: 500 })),
    )
    const floors = floorResps.flatMap((r) => r.results)
    const apartmentResps = await Promise.all(
      floors.map((f) => apartmentsApi.list({ floor: f.id, limit: 500 })),
    )
    apartments.value = apartmentResps
      .flatMap((r) => r.results)
      .sort((a, b) => a.number.localeCompare(b.number, "ru", { numeric: true }))
  } finally {
    loadingApartments.value = false
  }
}

watch(selectedProject, (pid) => {
  selectedApartment.value = null
  if (pid === null) {
    apartments.value = []
    return
  }
  void loadApartmentsForProject(pid)
})

const projectLabel = (p: Project) =>
  p.title[locale.value as "ru" | "uz" | "oz"] || `#${p.id}`

// --- Step 2: client + signer --------------------------------------------

const clientSearch = ref("")
const clientMatches = ref<Client[]>([])
const selectedClient = ref<Client | null>(null)
const contacts = ref<ClientContact[]>([])
const selectedSigner = ref<number | null>(null)

let clientSearchTimer: ReturnType<typeof setTimeout> | null = null

async function runClientSearch() {
  const q = clientSearch.value.trim()
  if (!q) {
    clientMatches.value = []
    return
  }
  const resp = await clientsApi.list({ search: q, limit: 20 })
  clientMatches.value = resp.results
}

watch(clientSearch, () => {
  if (clientSearchTimer) clearTimeout(clientSearchTimer)
  clientSearchTimer = setTimeout(runClientSearch, 300)
})

async function pickClient(c: Client) {
  selectedClient.value = c
  clientSearch.value = c.full_name
  clientMatches.value = []
  const resp = await clientContactsApi.list({ client: c.id, limit: 50 })
  contacts.value = resp.results
  // Prefer the primary signer if any.
  const chief = contacts.value.find((x) => x.is_chief)
  selectedSigner.value = chief?.id ?? contacts.value[0]?.id ?? null
}

// --- Step 3: calculation + template + money -----------------------------

const calculations = ref<Calculation[]>([])
const templates = ref<ContractTemplate[]>([])
const selectedCalculation = ref<number | null>(null)
const selectedTemplate = ref<number | null>(null)
const totalAmount = ref("")
const downPayment = ref("")
const isMortgage = ref(false)
const contractDate = ref<string>(new Date().toISOString().slice(0, 10))
const description = ref("")

async function loadCalculationsForApartment(aptId: number) {
  const resp = await calculationsApi.list({ apartment: aptId, limit: 50 })
  calculations.value = resp.results
}

async function loadTemplatesForProject(projectId: number | null) {
  const resp = await contractTemplatesApi.list({
    limit: 200,
    is_active: "true",
  })
  // Backend returns all templates the user can see; filter down to
  // either globals (project=null) or the exact project.
  templates.value = resp.results.filter(
    (tpl) => tpl.project === null || tpl.project === projectId,
  )
}

watch(selectedApartment, (aptId) => {
  calculations.value = []
  selectedCalculation.value = null
  if (aptId === null) return
  void loadCalculationsForApartment(aptId)
  const apt = apartments.value.find((x) => x.id === aptId)
  if (apt) {
    totalAmount.value = apt.total_price
  }
})

watch(selectedCalculation, (cid) => {
  if (cid === null) return
  const calc = calculations.value.find((x) => x.id === cid)
  if (!calc) return
  totalAmount.value = calc.new_total_price
  downPayment.value = calc.initial_fee
})

// --- Validation + navigation --------------------------------------------

const canNextStep = computed(() => {
  if (step.value === 1)
    return selectedProject.value !== null && selectedApartment.value !== null
  if (step.value === 2)
    return selectedClient.value !== null && selectedSigner.value !== null
  if (step.value === 3) return totalAmount.value !== ""
  return true
})

async function goNext() {
  if (!canNextStep.value) return
  if (step.value === 2) {
    await loadTemplatesForProject(selectedProject.value)
  }
  if (step.value < 4) {
    step.value = (step.value + 1) as 1 | 2 | 3 | 4
  }
}

function goPrev() {
  if (step.value > 1) {
    step.value = (step.value - 1) as 1 | 2 | 3 | 4
  }
}

async function submit() {
  if (
    selectedProject.value === null ||
    selectedApartment.value === null ||
    selectedSigner.value === null
  )
    return
  creating.value = true
  createError.value = null
  try {
    const payload: ContractWrite = {
      project: selectedProject.value,
      apartment: selectedApartment.value,
      calculation: selectedCalculation.value,
      signer: selectedSigner.value,
      author: null,
      template: selectedTemplate.value,
      contract_number: "",
      date: contractDate.value,
      send_date: null,
      related_person: "",
      description: description.value,
      total_amount: totalAmount.value || "0",
      down_payment: downPayment.value || "0",
      payment_methods: [],
      is_mortgage: isMortgage.value,
      requisite: {},
      document: {},
      is_active: true,
    }
    const created = await contractsApi.create(payload)
    toastStore.success(t("contracts.new"))
    router.replace({ name: "contracts-detail", params: { id: created.id } })
  } catch (e) {
    createError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  } finally {
    creating.value = false
  }
}

function formatMoney(value: string): string {
  if (!value) return "0"
  const n = Number(value)
  if (!Number.isFinite(n)) return value
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(n)
}

const stepLabels = computed(() => [
  t("contracts.wizard.step_project"),
  t("contracts.wizard.step_client"),
  t("contracts.wizard.step_money"),
  t("contracts.wizard.step_review"),
])

void loadProjects()
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5 px-1">
      <button
        class="btn btn-ghost btn-sm"
        @click="router.push({ name: 'contracts-unsigned' })"
      >
        <i class="pi pi-arrow-left text-[11px]" />
        {{ t("common.back") }}
      </button>
      <h1 class="text-[22px] font-semibold">
        {{ t("contracts.wizard.title") }}
      </h1>
    </div>

    <!-- Stepper -->
    <div class="flex items-center gap-2 mb-6 px-1 flex-wrap">
      <template v-for="(label, idx) in stepLabels" :key="idx">
        <div
          class="flex items-center gap-2 text-[12px]"
          :class="
            step === idx + 1
              ? 'text-ym-primary font-medium'
              : step > idx + 1
                ? 'text-ym-muted'
                : 'text-ym-subtle'
          "
        >
          <div
            class="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-mono border"
            :class="
              step === idx + 1
                ? 'bg-ym-primary text-white border-ym-primary'
                : step > idx + 1
                  ? 'bg-ym-primary-soft text-ym-primary border-ym-primary-soft'
                  : 'bg-ym-sunken text-ym-subtle border-ym-line-soft'
            "
          >
            {{ idx + 1 }}
          </div>
          <span>{{ label }}</span>
        </div>
        <div
          v-if="idx < stepLabels.length - 1"
          class="w-8 h-px bg-ym-line-soft"
        />
      </template>
    </div>

    <!-- Step 1 -->
    <section v-if="step === 1" class="card p-5 space-y-4">
      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.wizard.select_project") }}
        </label>
        <select v-model="selectedProject" class="inp">
          <option :value="null">—</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">
            {{ projectLabel(p) }}
          </option>
        </select>
      </div>
      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.wizard.select_apartment") }}
        </label>
        <div v-if="loadingApartments" class="text-ym-muted text-[12px]">
          {{ t("common.loading") }}
        </div>
        <select
          v-else
          v-model="selectedApartment"
          class="inp"
          :disabled="selectedProject === null"
        >
          <option :value="null">—</option>
          <option v-for="a in apartments" :key="a.id" :value="a.id">
            #{{ a.number }} · {{ a.rooms_count }}к · {{ a.area }}м² ·
            {{ a.status_display }}
          </option>
        </select>
      </div>
    </section>

    <!-- Step 2 -->
    <section v-else-if="step === 2" class="card p-5 space-y-4">
      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("clients.title") }}
        </label>
        <input
          v-model="clientSearch"
          class="inp"
          :placeholder="t('contracts.filters.search_placeholder')"
        />
        <div
          v-if="clientMatches.length > 0"
          class="mt-2 border border-ym-line-soft rounded-md max-h-[240px] overflow-auto art-scroll"
        >
          <button
            v-for="c in clientMatches"
            :key="c.id"
            type="button"
            class="w-full text-left px-3 py-2 hover:bg-ym-primary-soft/40 border-b border-ym-line-soft last:border-0"
            @click="pickClient(c)"
          >
            <div class="text-[13px] font-medium">{{ c.full_name }}</div>
            <div class="text-[11px] text-ym-muted mono">
              {{ c.inn || c.pin || "—" }} · {{ c.phones.join(", ") || "—" }}
            </div>
          </button>
        </div>
      </div>

      <div v-if="selectedClient">
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.wizard.select_signer") }}
        </label>
        <select v-model="selectedSigner" class="inp">
          <option :value="null">—</option>
          <option v-for="cc in contacts" :key="cc.id" :value="cc.id">
            {{ cc.full_name }}<span v-if="cc.is_chief"> ★</span>
            <span v-if="cc.role"> · {{ cc.role }}</span>
          </option>
        </select>
      </div>
      <div v-else class="text-[12px] text-ym-muted">
        {{ t("contracts.wizard.pick_client_first") }}
      </div>
    </section>

    <!-- Step 3 -->
    <section v-else-if="step === 3" class="card p-5 space-y-4">
      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.fields.calculation") }}
        </label>
        <select v-model="selectedCalculation" class="inp">
          <option :value="null">
            {{ t("contracts.fields.calculation_none") }}
          </option>
          <option v-for="c in calculations" :key="c.id" :value="c.id">
            {{ c.installment_months }} мес · {{ c.discount_percent }}% скидка ·
            {{ Number(c.new_total_price).toLocaleString("ru-RU") }}
          </option>
        </select>
        <div
          v-if="calculations.length === 0"
          class="mt-2 text-[11px] text-ym-muted"
        >
          {{ t("contracts.wizard.no_calculations") }}
        </div>
      </div>

      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.fields.template") }}
        </label>
        <select v-model="selectedTemplate" class="inp">
          <option :value="null">{{ t("contracts.fields.template_none") }}</option>
          <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">
            {{ tpl.title }}
          </option>
        </select>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("contracts.fields.total_amount") }}
          </label>
          <MoneyInput v-model="totalAmount" />
        </div>
        <div>
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("contracts.fields.down_payment") }}
          </label>
          <MoneyInput v-model="downPayment" />
        </div>
        <div>
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("contracts.fields.date") }}
          </label>
          <input v-model="contractDate" type="date" class="inp font-mono" />
        </div>
        <div>
          <label class="flex items-center gap-2 text-sm mt-6">
            <input v-model="isMortgage" type="checkbox" />
            <span>{{ t("contracts.fields.is_mortgage") }}</span>
          </label>
        </div>
      </div>

      <div>
        <label class="block text-[12px] font-medium mb-1.5">
          {{ t("contracts.fields.description") }}
        </label>
        <textarea v-model="description" class="inp" rows="3" />
      </div>
    </section>

    <!-- Step 4 (review) -->
    <section v-else-if="step === 4" class="card p-5">
      <dl class="grid grid-cols-2 gap-3 text-[13px]">
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.project") }}</dt>
          <dd class="mt-0.5 font-medium">
            {{
              selectedProject
                ? projectLabel(projects.find((p) => p.id === selectedProject)!)
                : "—"
            }}
          </dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.apartment") }}</dt>
          <dd class="mt-0.5 font-mono">
            {{
              apartments.find((a) => a.id === selectedApartment)?.number || "—"
            }}
          </dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("clients.title") }}</dt>
          <dd class="mt-0.5 font-medium">
            {{ selectedClient?.full_name || "—" }}
          </dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.signer") }}</dt>
          <dd class="mt-0.5">
            {{
              contacts.find((c) => c.id === selectedSigner)?.full_name || "—"
            }}
          </dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.total_amount") }}</dt>
          <dd class="mt-0.5 font-mono">{{ formatMoney(totalAmount) }}</dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.down_payment") }}</dt>
          <dd class="mt-0.5 font-mono">{{ formatMoney(downPayment) }}</dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.template") }}</dt>
          <dd class="mt-0.5">
            {{
              templates.find((tpl) => tpl.id === selectedTemplate)?.title ||
              t("contracts.fields.template_none")
            }}
          </dd>
        </div>
        <div>
          <dt class="text-ym-muted">{{ t("contracts.fields.is_mortgage") }}</dt>
          <dd class="mt-0.5">
            {{ isMortgage ? t("common.yes") : t("common.no") }}
          </dd>
        </div>
      </dl>
      <div
        v-if="createError"
        class="mt-4 text-sm text-ym-danger break-all"
      >
        {{ createError }}
      </div>
    </section>

    <!-- Actions -->
    <div class="mt-5 flex justify-end gap-2 px-1">
      <button
        v-if="step > 1"
        class="btn btn-ghost"
        :disabled="creating"
        @click="goPrev"
      >
        <i class="pi pi-arrow-left text-[11px]" />
        {{ t("contracts.wizard.prev") }}
      </button>
      <button
        v-if="step < 4"
        class="btn btn-primary"
        :disabled="!canNextStep"
        @click="goNext"
      >
        {{ t("contracts.wizard.next") }}
        <i class="pi pi-arrow-right text-[11px]" />
      </button>
      <button
        v-else
        class="btn btn-primary"
        :disabled="creating"
        @click="submit"
      >
        <i class="pi pi-plus text-[11px]" />
        {{ t("contracts.wizard.create") }}
      </button>
    </div>
  </div>
</template>
