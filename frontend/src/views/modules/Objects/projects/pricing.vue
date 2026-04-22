<script setup lang="ts">
/**
 * Project pricing tab — PaymentPlans + DiscountRules CRUD.
 *
 * Sits behind `/objects/projects/:id/pricing` and shares its header with
 * `detail.vue` (same breadcrumbs, same tab strip). Each entity has its own
 * table with row-level edit/delete and a create button; a single modal
 * handles all 4 CRUD operations via a kind+editingId dispatch, mirroring
 * the pattern from `detail.vue`.
 *
 * Calculation + PriceHistory aren't managed from here:
 *   * Calculation is derived data (phase 3.4 pricing service writes it).
 *   * PriceHistory is read-only and shown next to the floor price edit UI
 *     when that lands in 3.4.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import {
  discountRulesApi,
  paymentPlansApi,
  projectsApi,
} from "@/api/objects"
import { lookupsApi } from "@/api/references"
import { usePermissionStore } from "@/store/permissions"
import type {
  DiscountRule,
  DiscountRuleWrite,
  I18nText,
  LookupItem,
  PaymentInPercentItem,
  PaymentPlan,
  PaymentPlanWrite,
  Project,
} from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const permissions = usePermissionStore()
const router = useRouter()

const projectId = computed(() => Number(props.id))

const project = ref<Project | null>(null)
const paymentPlans = ref<PaymentPlan[]>([])
const discountRules = ref<DiscountRule[]>([])
const paymentPercents = ref<PaymentInPercentItem[]>([])
const loading = ref(false)

const canViewPlans = computed(() => permissions.check("objects.payment_plans.view"))
const canCreatePlan = computed(() => permissions.check("objects.payment_plans.create"))
const canEditPlan = computed(() => permissions.check("objects.payment_plans.edit"))
const canDeletePlan = computed(() => permissions.check("objects.payment_plans.delete"))

const canViewRules = computed(() => permissions.check("objects.discounts.view"))
const canCreateRule = computed(() => permissions.check("objects.discounts.create"))
const canEditRule = computed(() => permissions.check("objects.discounts.edit"))
const canDeleteRule = computed(() => permissions.check("objects.discounts.delete"))

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

async function load() {
  loading.value = true
  try {
    const results = await Promise.all([
      projectsApi.retrieve(projectId.value),
      canViewPlans.value
        ? paymentPlansApi.list({ project: projectId.value, limit: 200 })
        : Promise.resolve({ results: [] as PaymentPlan[], count: 0, next: null, previous: null }),
      canViewRules.value
        ? discountRulesApi.list({ project: projectId.value, limit: 200 })
        : Promise.resolve({ results: [] as DiscountRule[], count: 0, next: null, previous: null }),
      lookupsApi["payment-in-percent"].list({ limit: 200 }),
    ])
    project.value = results[0]
    paymentPlans.value = results[1].results
    discountRules.value = results[2].results
    paymentPercents.value = results[3].results as PaymentInPercentItem[]
  } finally {
    loading.value = false
  }
}

// --- Modal dispatch ------------------------------------------------------

type ModalKind = "plan" | "rule"
interface ModalState {
  kind: ModalKind
  editingId: number | null
}
const showModal = ref(false)
const modalState = ref<ModalState | null>(null)
const saveError = ref<string | null>(null)

const planForm = reactive<PaymentPlanWrite>({
  project: 0,
  name: emptyI18n(),
  down_payment_percent: "0.00",
  installment_months: 0,
  sort: 0,
  is_active: true,
})

const ruleForm = reactive<DiscountRuleWrite>({
  project: 0,
  area_start: "0.00",
  area_end: "0.00",
  payment_percent: 0,
  discount_percent: "0.00",
  is_duplex: false,
  sort: 0,
  is_active: true,
})

function openPlanCreate() {
  modalState.value = { kind: "plan", editingId: null }
  Object.assign(planForm, {
    project: projectId.value,
    name: emptyI18n(),
    down_payment_percent: "0.00",
    installment_months: 0,
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openPlanEdit(p: PaymentPlan) {
  modalState.value = { kind: "plan", editingId: p.id }
  Object.assign(planForm, {
    project: p.project,
    name: { ...p.name },
    down_payment_percent: p.down_payment_percent,
    installment_months: p.installment_months,
    sort: p.sort,
    is_active: p.is_active,
  })
  saveError.value = null
  showModal.value = true
}

function openRuleCreate() {
  modalState.value = { kind: "rule", editingId: null }
  Object.assign(ruleForm, {
    project: projectId.value,
    area_start: "0.00",
    area_end: "0.00",
    payment_percent: paymentPercents.value[0]?.id || 0,
    discount_percent: "0.00",
    is_duplex: false,
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openRuleEdit(r: DiscountRule) {
  modalState.value = { kind: "rule", editingId: r.id }
  Object.assign(ruleForm, {
    project: r.project,
    area_start: r.area_start,
    area_end: r.area_end,
    payment_percent: r.payment_percent,
    discount_percent: r.discount_percent,
    is_duplex: r.is_duplex,
    sort: r.sort,
    is_active: r.is_active,
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  if (!modalState.value) return
  saveError.value = null
  const { kind, editingId } = modalState.value
  try {
    if (kind === "plan") {
      if (editingId) await paymentPlansApi.update(editingId, planForm)
      else await paymentPlansApi.create(planForm)
    } else {
      if (editingId) await discountRulesApi.update(editingId, ruleForm)
      else await discountRulesApi.create(ruleForm)
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function removePlan(p: PaymentPlan) {
  if (!confirm(`${t("objects.payment_plans.confirm_delete")}?`)) return
  try {
    await paymentPlansApi.destroy(p.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}
async function removeRule(r: DiscountRule) {
  if (!confirm(`${t("objects.discount_rules.confirm_delete")}?`)) return
  try {
    await discountRulesApi.destroy(r.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}

function localizedPlan(p: PaymentPlan): string {
  return p.name[locale.value as keyof I18nText] || `#${p.id}`
}
function localizedLookup(item: LookupItem | PaymentInPercentItem | undefined): string {
  if (!item) return "—"
  return item.name[locale.value as keyof I18nText] || `#${item.id}`
}
function paymentPercentName(id: number): string {
  const pp = paymentPercents.value.find((x) => x.id === id)
  if (!pp) return `#${id}`
  const base = localizedLookup(pp)
  return `${base} (${pp.percent}%)`
}

function projectTitle(): string {
  if (!project.value) return ""
  return project.value.title[locale.value as keyof I18nText] || `#${project.value.id}`
}
function developerName(): string {
  if (!project.value?.developer_name) return "—"
  return project.value.developer_name[locale.value as keyof I18nText] || "—"
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-3 mt-1 px-1">
      <div>
        <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle flex items-center gap-2">
          <button class="hover:text-ym-primary" @click="router.push('/objects')">
            {{ t("nav.objects") }}
          </button>
          <span>/</span>
          <button
            class="hover:text-ym-primary"
            @click="router.push(`/objects/projects/${projectId}`)"
          >
            {{ projectTitle() }}
          </button>
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("objects.tabs.pricing") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          <i class="pi pi-wrench text-[10px] mr-1.5" />
          {{ developerName() }}
        </div>
      </div>
    </div>

    <div class="flex gap-1 mb-5 border-b border-ym-line-soft">
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}`)"
      >
        {{ t("objects.tabs.structure") }}
      </button>
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-ym-primary text-ym-primary font-medium"
      >
        {{ t("objects.tabs.pricing") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else class="space-y-5">
      <!-- PaymentPlans -->
      <section>
        <div class="flex items-center justify-between mb-3 px-1">
          <h2 class="text-[15px] font-semibold">{{ t("objects.payment_plans.title") }}</h2>
          <button v-if="canCreatePlan" class="btn btn-soft btn-sm" @click="openPlanCreate">
            <i class="pi pi-plus text-[10px]" />
            {{ t("objects.payment_plans.new") }}
          </button>
        </div>
        <div
          v-if="!paymentPlans.length"
          class="card p-6 text-center text-ym-muted text-[13px]"
        >
          {{ t("objects.payment_plans.empty") }}
        </div>
        <div v-else class="card overflow-hidden">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t("objects.payment_plans.fields.name") }}</th>
                <th>{{ t("objects.payment_plans.fields.down_payment_percent") }}</th>
                <th>{{ t("objects.payment_plans.fields.installment_months") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in paymentPlans" :key="p.id">
                <td class="font-medium">{{ localizedPlan(p) }}</td>
                <td class="font-mono text-[12.5px]">{{ p.down_payment_percent }}%</td>
                <td class="font-mono text-[12.5px]">{{ p.installment_months }}</td>
                <td class="text-right whitespace-nowrap">
                  <button v-if="canEditPlan" class="btn btn-ghost btn-xs mr-1" @click="openPlanEdit(p)">
                    {{ t("common.edit") }}
                  </button>
                  <button v-if="canDeletePlan" class="btn btn-danger btn-xs" @click="removePlan(p)">
                    {{ t("common.delete") }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- DiscountRules -->
      <section>
        <div class="flex items-center justify-between mb-3 px-1">
          <h2 class="text-[15px] font-semibold">{{ t("objects.discount_rules.title") }}</h2>
          <button v-if="canCreateRule" class="btn btn-soft btn-sm" @click="openRuleCreate">
            <i class="pi pi-plus text-[10px]" />
            {{ t("objects.discount_rules.new") }}
          </button>
        </div>
        <div
          v-if="!discountRules.length"
          class="card p-6 text-center text-ym-muted text-[13px]"
        >
          {{ t("objects.discount_rules.empty") }}
        </div>
        <div v-else class="card overflow-hidden">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t("objects.discount_rules.fields.area_start") }}</th>
                <th>{{ t("objects.discount_rules.fields.area_end") }}</th>
                <th>{{ t("objects.discount_rules.fields.payment_percent") }}</th>
                <th>{{ t("objects.discount_rules.fields.discount_percent") }}</th>
                <th>{{ t("objects.discount_rules.fields.is_duplex") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in discountRules" :key="r.id">
                <td class="font-mono text-[12.5px]">{{ r.area_start }}</td>
                <td class="font-mono text-[12.5px]">{{ r.area_end }}</td>
                <td class="text-[12.5px]">{{ paymentPercentName(r.payment_percent) }}</td>
                <td class="font-mono text-[12.5px]">{{ r.discount_percent }}%</td>
                <td>
                  <span v-if="r.is_duplex" class="chip chip-primary">{{ t("common.yes") }}</span>
                  <span v-else class="chip chip-ghost">{{ t("common.no") }}</span>
                </td>
                <td class="text-right whitespace-nowrap">
                  <button v-if="canEditRule" class="btn btn-ghost btn-xs mr-1" @click="openRuleEdit(r)">
                    {{ t("common.edit") }}
                  </button>
                  <button v-if="canDeleteRule" class="btn btn-danger btn-xs" @click="removeRule(r)">
                    {{ t("common.delete") }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <!-- Modal -->
    <div
      v-if="showModal && modalState"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="showModal = false"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          <template v-if="modalState.kind === 'plan'">
            {{ modalState.editingId ? t("objects.payment_plans.edit") : t("objects.payment_plans.new") }}
          </template>
          <template v-else>
            {{ modalState.editingId ? t("objects.discount_rules.edit") : t("objects.discount_rules.new") }}
          </template>
        </h2>

        <template v-if="modalState.kind === 'plan'">
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.payment_plans.fields.name") }}
            </label>
            <div class="grid grid-cols-3 gap-2">
              <input v-model="planForm.name.ru" class="inp" placeholder="RU" />
              <input v-model="planForm.name.uz" class="inp" placeholder="UZ" />
              <input v-model="planForm.name.oz" class="inp" placeholder="ОЗ" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.payment_plans.fields.down_payment_percent") }}
              </label>
              <input v-model="planForm.down_payment_percent" class="inp font-mono" placeholder="30.00" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.payment_plans.fields.installment_months") }}
              </label>
              <input
                v-model.number="planForm.installment_months"
                type="number"
                min="0"
                class="inp font-mono"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.discount_rules.fields.area_start") }}
              </label>
              <input v-model="ruleForm.area_start" class="inp font-mono" placeholder="0.00" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.discount_rules.fields.area_end") }}
              </label>
              <input v-model="ruleForm.area_end" class="inp font-mono" placeholder="200.00" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.discount_rules.fields.payment_percent") }}
              </label>
              <select v-model.number="ruleForm.payment_percent" class="inp">
                <option v-for="pp in paymentPercents" :key="pp.id" :value="pp.id">
                  {{ pp.name[locale as keyof I18nText] || `#${pp.id}` }} ({{ pp.percent }}%)
                </option>
              </select>
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.discount_rules.fields.discount_percent") }}
              </label>
              <input v-model="ruleForm.discount_percent" class="inp font-mono" placeholder="5.00" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm mt-4">
            <input v-model="ruleForm.is_duplex" type="checkbox" />
            <span>{{ t("objects.discount_rules.fields.is_duplex") }}</span>
          </label>
        </template>

        <label class="flex items-center gap-2 text-sm mt-5">
          <input
            v-if="modalState.kind === 'plan'"
            v-model="planForm.is_active"
            type="checkbox"
          />
          <input v-else v-model="ruleForm.is_active" type="checkbox" />
          <span>{{ t("common.yes") }} / {{ t("common.no") }}</span>
        </label>

        <div v-if="saveError" class="mt-3 text-sm text-ym-danger break-all">
          {{ saveError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showModal = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="save">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
