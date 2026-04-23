<script setup lang="ts">
/**
 * Shaxmatka — visual floor × apartment grid.
 *
 * One row per floor (highest at the top); each cell is an apartment tinted
 * by status. Click a cell → side drawer with full apartment detail,
 * calculations, status history, and action buttons.
 *
 * Data load pattern mirrors `detail.vue`: everything for the project up
 * front. When fondmoney grows past ~2k apartments per project the
 * apartments list should move to paginated / lazy-per-floor, but that's
 * premature until we see real volumes.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import {
  apartmentsApi,
  apartmentStatusLogsApi,
  buildingsApi,
  calculationsApi,
  floorsApi,
  projectsApi,
  sectionsApi,
} from "@/api/objects"
import { lookupsApi } from "@/api/references"
import { usePermissionStore } from "@/store/permissions"
import { usePromptStore } from "@/store/prompt"
import type {
  Apartment,
  ApartmentStatus,
  ApartmentStatusLog,
  Building,
  Calculation,
  Floor,
  I18nText,
  PaymentInPercentItem,
  Project,
  Section,
} from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const permissions = usePermissionStore()
const promptStore = usePromptStore()
const router = useRouter()

const projectId = computed(() => Number(props.id))

const project = ref<Project | null>(null)
const buildings = ref<Building[]>([])
const sections = ref<Section[]>([])
const floors = ref<Floor[]>([])
const apartments = ref<Apartment[]>([])
const paymentPercents = ref<PaymentInPercentItem[]>([])
const loading = ref(false)

const selectedBuildingId = ref<number | null>(null)
const selectedSectionId = ref<number | null>(null)
const roomsFilter = ref<number | null>(null)

const canBook = computed(() => permissions.check("objects.apartments.book"))
const canChangeStatus = computed(() => permissions.check("objects.apartments.change_status"))
const canRecalc = computed(() => permissions.check("objects.apartments.edit"))

async function load() {
  loading.value = true
  try {
    project.value = await projectsApi.retrieve(projectId.value)
    const bs = await buildingsApi.list({ project: projectId.value, limit: 200 })
    buildings.value = bs.results
    if (!buildings.value.length) {
      sections.value = []
      floors.value = []
      apartments.value = []
      return
    }
    const [ss, fs, apts, pps] = await Promise.all([
      sectionsApi.list({ limit: 500 }),
      floorsApi.list({ limit: 1000 }),
      apartmentsApi.list({ limit: 5000 }),
      lookupsApi["payment-in-percent"].list({ limit: 200 }),
    ])
    const buildingIds = new Set(buildings.value.map((b) => b.id))
    sections.value = ss.results.filter((s) => buildingIds.has(s.building))
    const sectionIds = new Set(sections.value.map((s) => s.id))
    floors.value = fs.results.filter((f) => sectionIds.has(f.section))
    const floorIds = new Set(floors.value.map((f) => f.id))
    apartments.value = apts.results.filter((a) => floorIds.has(a.floor))
    paymentPercents.value = pps.results as PaymentInPercentItem[]

    if (selectedBuildingId.value == null) {
      selectedBuildingId.value = buildings.value[0]?.id ?? null
    }
    // Prefer first section of selected building.
    const firstOfSelected = sections.value.find(
      (s) => s.building === selectedBuildingId.value,
    )
    if (selectedSectionId.value == null || !firstOfSelected) {
      selectedSectionId.value = firstOfSelected?.id ?? null
    }
  } finally {
    loading.value = false
  }
}

// --- Derived --------------------------------------------------------------

const currentBuilding = computed<Building | null>(
  () => buildings.value.find((b) => b.id === selectedBuildingId.value) ?? null,
)
const sectionsOfCurrentBuilding = computed<Section[]>(() =>
  sections.value.filter((s) => s.building === selectedBuildingId.value),
)
const currentSection = computed<Section | null>(
  () => sections.value.find((s) => s.id === selectedSectionId.value) ?? null,
)

/** Floors of the current section sorted high → low (number desc). */
const floorsOfSection = computed<Floor[]>(() =>
  floors.value
    .filter((f) => f.section === selectedSectionId.value)
    .slice()
    .sort((a, b) => b.number - a.number),
)

function apartmentsOfFloor(floorId: number): Apartment[] {
  const all = apartments.value.filter((a) => a.floor === floorId)
  if (roomsFilter.value == null) return all
  const want = roomsFilter.value
  return all.filter((a) =>
    want >= 4 ? a.rooms_count >= 4 : a.rooms_count === want,
  )
}

/** Distinct room counts present in the current section — drives the filter chips. */
const roomsOptions = computed<number[]>(() => {
  const set = new Set<number>()
  floorsOfSection.value.forEach((f) => {
    apartments.value
      .filter((a) => a.floor === f.id)
      .forEach((a) => set.add(a.rooms_count))
  })
  return Array.from(set).sort((a, b) => a - b)
})

function selectBuilding(id: number) {
  selectedBuildingId.value = id
  // Pick first section of new building.
  const firstSection = sections.value.find((s) => s.building === id)
  selectedSectionId.value = firstSection?.id ?? null
}

// --- Apartment drawer ----------------------------------------------------

const drawerApt = ref<Apartment | null>(null)
const drawerCalcs = ref<Calculation[]>([])
const drawerLogs = ref<ApartmentStatusLog[]>([])
const drawerLoading = ref(false)
const drawerError = ref<string | null>(null)

async function openApartment(a: Apartment) {
  drawerApt.value = a
  drawerError.value = null
  drawerLoading.value = true
  try {
    const [calcs, logs] = await Promise.all([
      calculationsApi.list({ apartment: a.id, limit: 50 }),
      apartmentStatusLogsApi.list({ apartment: a.id, limit: 10 }),
    ])
    drawerCalcs.value = calcs.results
    drawerLogs.value = logs.results
  } finally {
    drawerLoading.value = false
  }
}

function closeDrawer() {
  drawerApt.value = null
  drawerCalcs.value = []
  drawerLogs.value = []
  drawerError.value = null
}

async function reloadDrawer() {
  if (!drawerApt.value) return
  const fresh = await apartmentsApi.retrieve(drawerApt.value.id)
  drawerApt.value = fresh
  // update the list entry so the grid cell colour refreshes
  const idx = apartments.value.findIndex((x) => x.id === fresh.id)
  if (idx >= 0) apartments.value[idx] = fresh
  const [calcs, logs] = await Promise.all([
    calculationsApi.list({ apartment: fresh.id, limit: 50 }),
    apartmentStatusLogsApi.list({ apartment: fresh.id, limit: 10 }),
  ])
  drawerCalcs.value = calcs.results
  drawerLogs.value = logs.results
}

// --- Drawer actions -------------------------------------------------------

const showBookSub = ref(false)
const bookSubForm = reactive({ duration_days: 7, comment: "", vip: false })

function openBookSub() {
  if (!drawerApt.value) return
  bookSubForm.duration_days = 7
  bookSubForm.comment = ""
  bookSubForm.vip = false
  showBookSub.value = true
  drawerError.value = null
}

async function doBook() {
  if (!drawerApt.value) return
  drawerError.value = null
  try {
    await apartmentsApi.book(
      drawerApt.value.id,
      bookSubForm.duration_days,
      bookSubForm.comment,
      bookSubForm.vip,
    )
    showBookSub.value = false
    await reloadDrawer()
  } catch (e) {
    drawerError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function doRelease() {
  if (!drawerApt.value) return
  const comment = await promptStore.ask({
    title: t("objects.apartments.release"),
    message: t("objects.apartments.comment") + " (опц.)",
    multiline: true,
    required: false,
  })
  if (comment === null) return
  try {
    await apartmentsApi.release(drawerApt.value.id, comment)
    await reloadDrawer()
  } catch (e) {
    drawerError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function doRecalc() {
  if (!drawerApt.value) return
  drawerError.value = null
  try {
    await apartmentsApi.recalc(drawerApt.value.id)
    await reloadDrawer()
  } catch (e) {
    drawerError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

// --- Formatting / helpers ------------------------------------------------

function projectTitle(): string {
  if (!project.value) return ""
  return project.value.title[locale.value as keyof I18nText] || `#${project.value.id}`
}
function localizedTitle(item: { title?: I18nText } | null): string {
  if (!item?.title) return ""
  return item.title[locale.value as keyof I18nText] || ""
}
function paymentPercentLabel(id: number): string {
  const pp = paymentPercents.value.find((x) => x.id === id)
  if (!pp) return `#${id}`
  const name = pp.name[locale.value as keyof I18nText] || ""
  return name ? `${name} (${pp.percent}%)` : `${pp.percent}%`
}
function fmtPrice(v: string): string {
  const n = Number(v)
  if (Number.isNaN(n)) return v
  return new Intl.NumberFormat("ru-RU").format(n)
}

/** Background color for a grid cell based on apartment status. */
function cellClass(s: ApartmentStatus): string {
  switch (s) {
    case "free":
      return "bg-ym-success text-white"
    case "booked":
      return "bg-ym-warning text-white"
    case "booked_vip":
      return "bg-ym-primary text-white"
    case "formalized":
    case "escrow":
      return "bg-ym-info text-white"
    case "sold":
      return "bg-neutral-400 text-white"
  }
}

/** Statuses shown in the legend row, in workflow order. */
const legendStatuses: ApartmentStatus[] = [
  "free",
  "booked",
  "booked_vip",
  "formalized",
  "escrow",
  "sold",
]

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
          {{ t("objects.shaxmatka.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("objects.shaxmatka.subtitle") }}
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
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}/pricing`)"
      >
        {{ t("objects.tabs.pricing") }}
      </button>
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-ym-primary text-ym-primary font-medium"
      >
        {{ t("objects.tabs.shaxmatka") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="!buildings.length" class="card p-8 text-center text-ym-muted">
      {{ t("objects.buildings.empty") }}
    </div>

    <div v-else>
      <!-- Controls row -->
      <div class="flex flex-wrap items-center gap-4 mb-4">
        <!-- Building -->
        <div class="flex items-center gap-2">
          <span class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle">
            {{ t("objects.shaxmatka.select_building") }}
          </span>
          <div class="flex gap-1">
            <button
              v-for="b in buildings"
              :key="b.id"
              class="chip"
              :class="b.id === selectedBuildingId ? 'chip-primary' : 'chip-ghost'"
              @click="selectBuilding(b.id)"
            >
              {{ localizedTitle(b) || `#${b.id}` }}
            </button>
          </div>
        </div>
        <!-- Section -->
        <div v-if="sectionsOfCurrentBuilding.length" class="flex items-center gap-2">
          <span class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle">
            {{ t("objects.shaxmatka.select_section") }}
          </span>
          <div class="flex gap-1">
            <button
              v-for="s in sectionsOfCurrentBuilding"
              :key="s.id"
              class="chip"
              :class="s.id === selectedSectionId ? 'chip-primary' : 'chip-ghost'"
              @click="selectedSectionId = s.id"
            >
              {{ localizedTitle(s) || `№${s.number}` }}
            </button>
          </div>
        </div>
        <!-- Rooms filter -->
        <div v-if="roomsOptions.length > 1" class="flex items-center gap-2 ml-auto">
          <span class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle">
            {{ t("objects.shaxmatka.filter_rooms") }}
          </span>
          <button
            class="chip"
            :class="roomsFilter === null ? 'chip-primary' : 'chip-ghost'"
            @click="roomsFilter = null"
          >
            {{ t("objects.shaxmatka.filter_all") }}
          </button>
          <button
            v-for="r in roomsOptions"
            :key="r"
            class="chip"
            :class="roomsFilter === r ? 'chip-primary' : 'chip-ghost'"
            @click="roomsFilter = r"
          >
            {{ r }}
          </button>
        </div>
      </div>

      <!-- Legend -->
      <div class="card p-3 mb-4 flex flex-wrap items-center gap-4">
        <span class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle mr-2">
          {{ t("objects.shaxmatka.legend") }}
        </span>
        <div v-for="s in legendStatuses" :key="s" class="flex items-center gap-2 text-[12.5px]">
          <span :class="['inline-block w-4 h-4 rounded-sm', cellClass(s)]" />
          <span>{{ t(`objects.apartments.status.${s}`) }}</span>
        </div>
      </div>

      <!-- Grid -->
      <div
        v-if="!currentSection"
        class="card p-8 text-center text-ym-muted"
      >
        {{ t("objects.shaxmatka.no_data") }}
      </div>
      <div v-else class="card overflow-x-auto art-scroll">
        <div class="min-w-fit">
          <div
            v-for="f in floorsOfSection"
            :key="f.id"
            class="flex items-stretch border-b last:border-b-0 border-ym-line-soft"
          >
            <!-- Floor number label -->
            <div
              class="flex-none w-16 flex items-center justify-center border-r border-ym-line-soft bg-ym-sunken/40 font-mono text-[13px] font-semibold text-ym-subtle"
            >
              {{ f.number }}
            </div>
            <!-- Apartment cells -->
            <div
              v-if="!apartmentsOfFloor(f.id).length"
              class="flex-1 flex items-center px-3 text-[11.5px] text-ym-muted italic py-2"
            >
              {{ t("objects.shaxmatka.empty_floor") }}
            </div>
            <div v-else class="flex flex-wrap gap-1.5 p-2">
              <button
                v-for="a in apartmentsOfFloor(f.id)"
                :key="a.id"
                :class="[
                  cellClass(a.status),
                  'w-[96px] h-[58px] rounded-md px-2 py-1 text-left',
                  'hover:brightness-110 hover:shadow-ym-card transition',
                  drawerApt && drawerApt.id === a.id ? 'ring-2 ring-offset-1 ring-ym-primary' : '',
                ]"
                @click="openApartment(a)"
              >
                <div class="font-mono text-[13px] font-semibold leading-none">{{ a.number }}</div>
                <div class="text-[10.5px] opacity-90 mt-0.5">
                  {{ a.rooms_count }}к · {{ a.area }}м²
                </div>
                <div class="text-[10.5px] font-mono opacity-90 mt-0.5 truncate">
                  {{ fmtPrice(a.total_price) }}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Apartment drawer -->
    <div
      v-if="drawerApt"
      class="fixed inset-0 z-50 flex"
      @keydown.esc="closeDrawer"
    >
      <div class="flex-1 bg-black/40" @click="closeDrawer" />
      <div class="w-full sm:w-[560px] bg-ym-surface shadow-ym-modal h-full overflow-y-auto art-scroll flex flex-col">
        <div class="p-5 border-b border-ym-line-soft flex items-start justify-between">
          <div>
            <div class="text-[11px] uppercase tracking-[0.12em] font-mono text-ym-subtle">
              {{ t("objects.shaxmatka.apt_details") }}
            </div>
            <h2 class="text-[20px] font-semibold leading-none tracking-[-0.02em] mt-1">
              #{{ drawerApt.number }}
            </h2>
            <div class="mt-2">
              <span :class="cellClass(drawerApt.status)" class="px-2 py-0.5 text-[12px] rounded">
                {{ t(`objects.apartments.status.${drawerApt.status}`) }}
              </span>
              <span v-if="drawerApt.booking_expires_at" class="ml-2 text-[12px] text-ym-muted">
                · {{ t("objects.apartments.booking_expires_at") }}:
                {{ new Date(drawerApt.booking_expires_at).toLocaleDateString() }}
              </span>
            </div>
          </div>
          <button class="btn btn-ghost btn-icon btn-sm" @click="closeDrawer">
            <i class="pi pi-times text-[11px]" />
          </button>
        </div>

        <div class="p-5 space-y-5 flex-1">
          <!-- Basic facts -->
          <div class="grid grid-cols-2 gap-3 text-[13px]">
            <div>
              <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle">
                {{ t("objects.shaxmatka.apt_rooms") }}
              </div>
              <div class="font-mono">{{ drawerApt.rooms_count }}</div>
            </div>
            <div>
              <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle">
                {{ t("objects.shaxmatka.apt_area") }}
              </div>
              <div class="font-mono">{{ drawerApt.area }} м²</div>
            </div>
            <div>
              <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle">
                {{ t("objects.shaxmatka.apt_total_price") }}
              </div>
              <div class="font-mono">{{ fmtPrice(drawerApt.total_price) }} UZS</div>
            </div>
            <div v-if="Number(drawerApt.surcharge) > 0">
              <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle">
                {{ t("objects.shaxmatka.apt_surcharge") }}
              </div>
              <div class="font-mono">{{ fmtPrice(drawerApt.surcharge) }} UZS</div>
            </div>
          </div>

          <div v-if="drawerApt.is_duplex || drawerApt.is_studio || drawerApt.is_euro_planning" class="flex gap-2">
            <span v-if="drawerApt.is_studio" class="chip chip-ghost">
              {{ t("objects.apartments.fields.is_studio") }}
            </span>
            <span v-if="drawerApt.is_duplex" class="chip chip-ghost">
              {{ t("objects.apartments.fields.is_duplex") }}
            </span>
            <span v-if="drawerApt.is_euro_planning" class="chip chip-ghost">
              {{ t("objects.apartments.fields.is_euro_planning") }}
            </span>
          </div>

          <!-- Calculations -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-[13px] font-semibold">
                {{ t("objects.shaxmatka.calculations_title") }}
              </h3>
              <button
                v-if="canRecalc"
                class="btn btn-soft btn-xs"
                @click="doRecalc"
              >
                <i class="pi pi-refresh text-[10px]" />
                {{ t("objects.shaxmatka.recalc") }}
              </button>
            </div>
            <div
              v-if="drawerLoading && !drawerCalcs.length"
              class="text-[12px] text-ym-muted"
            >
              {{ t("common.loading") }}
            </div>
            <div
              v-else-if="!drawerCalcs.length"
              class="text-[12px] text-ym-muted"
            >
              {{ t("objects.shaxmatka.calculations_empty") }}
            </div>
            <table v-else class="tbl">
              <thead>
                <tr>
                  <th>{{ t("objects.shaxmatka.calc_percent") }}</th>
                  <th>{{ t("objects.shaxmatka.calc_discount") }}</th>
                  <th>{{ t("objects.shaxmatka.calc_price_sqm") }}</th>
                  <th>{{ t("objects.shaxmatka.calc_total") }}</th>
                  <th>{{ t("objects.shaxmatka.calc_initial") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in drawerCalcs" :key="c.id">
                  <td class="text-[12px]">{{ paymentPercentLabel(c.payment_percent) }}</td>
                  <td class="font-mono text-[12px]">{{ c.discount_percent }}%</td>
                  <td class="font-mono text-[12px]">{{ fmtPrice(c.new_price_per_sqm) }}</td>
                  <td class="font-mono text-[12px]">{{ fmtPrice(c.new_total_price) }}</td>
                  <td class="font-mono text-[12px]">{{ fmtPrice(c.initial_fee) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Status log -->
          <div>
            <h3 class="text-[13px] font-semibold mb-2">
              {{ t("objects.shaxmatka.log_title") }}
            </h3>
            <div v-if="!drawerLogs.length" class="text-[12px] text-ym-muted">
              {{ t("objects.shaxmatka.log_empty") }}
            </div>
            <ul v-else class="space-y-1.5">
              <li
                v-for="log in drawerLogs"
                :key="log.id"
                class="text-[12px] flex items-start gap-2"
              >
                <span class="font-mono text-ym-subtle w-[110px] flex-none">
                  {{ new Date(log.created_at).toLocaleString() }}
                </span>
                <span>
                  <span class="font-mono text-ym-muted">{{ log.old_status || "∅" }}</span>
                  →
                  <span class="font-mono">{{ log.new_status }}</span>
                  <span v-if="log.changed_by_name" class="text-ym-muted ml-1">
                    · {{ log.changed_by_name }}
                  </span>
                  <div v-if="log.comment" class="text-ym-muted">
                    {{ log.comment }}
                  </div>
                </span>
              </li>
            </ul>
          </div>

          <div v-if="drawerError" class="text-[12px] text-ym-danger break-all">
            {{ drawerError }}
          </div>
        </div>

        <div class="p-5 border-t border-ym-line-soft flex gap-2 flex-wrap">
          <button
            v-if="drawerApt.status === 'free' && canBook"
            class="btn btn-primary btn-sm"
            @click="openBookSub"
          >
            <i class="pi pi-bookmark text-[11px]" />
            {{ t("objects.apartments.book") }}
          </button>
          <button
            v-if="(drawerApt.status === 'booked' || drawerApt.status === 'booked_vip') && canChangeStatus"
            class="btn btn-soft btn-sm"
            @click="doRelease"
          >
            {{ t("objects.apartments.release") }}
          </button>
          <button class="btn btn-ghost btn-sm ml-auto" @click="closeDrawer">
            {{ t("common.close") }}
          </button>
        </div>

        <!-- Book sub-modal (inside drawer) -->
        <div
          v-if="showBookSub"
          class="absolute inset-0 bg-black/40 flex items-center justify-center p-4"
          @click.self="showBookSub = false"
        >
          <div class="card w-full max-w-md p-5 shadow-ym-modal">
            <h3 class="text-base font-semibold mb-3">
              {{ t("objects.apartments.book_title") }}
            </h3>
            <div class="mb-3">
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.duration_days") }}
              </label>
              <input
                v-model.number="bookSubForm.duration_days"
                type="number"
                min="1"
                max="365"
                class="inp font-mono"
              />
            </div>
            <div class="mb-3">
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.comment") }}
              </label>
              <textarea v-model="bookSubForm.comment" class="inp" rows="2" />
            </div>
            <label
              v-if="permissions.check('objects.apartments.book_vip')"
              class="flex items-center gap-2 text-sm mb-3"
            >
              <input v-model="bookSubForm.vip" type="checkbox" />
              <span>{{ t("objects.apartments.vip_checkbox") }}</span>
            </label>
            <div class="flex justify-end gap-2">
              <button class="btn btn-ghost btn-sm" @click="showBookSub = false">
                {{ t("common.cancel") }}
              </button>
              <button class="btn btn-primary btn-sm" @click="doBook">
                {{ t("common.save") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
