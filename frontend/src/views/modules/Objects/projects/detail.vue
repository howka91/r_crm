<script setup lang="ts">
/**
 * Project detail — nested drill-down for Buildings → Sections → Floors →
 * Apartments.
 *
 * Phase 3.1 shipped the first three levels; phase 3.2 adds Apartments with
 * their status chip and the "change status" workflow. A single modal handles
 * create/edit for all child entity types plus the status-change dialog.
 *
 * For small projects (a few hundred apartments total) loading everything up
 * front is acceptable. When totals grow, lazy-loading per floor is easy —
 * the `apartmentsFor(floorId)` helper is already filtering client-side.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import {
  apartmentsApi,
  buildingsApi,
  floorsApi,
  priceHistoryApi,
  projectsApi,
  sectionsApi,
} from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import type {
  Apartment,
  ApartmentStatus,
  ApartmentWrite,
  Building,
  BuildingWrite,
  Floor,
  FloorWrite,
  I18nText,
  PriceHistory,
  Project,
  Section,
  SectionWrite,
} from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const permissions = usePermissionStore()
const router = useRouter()

const projectId = computed(() => Number(props.id))

const project = ref<Project | null>(null)
const buildings = ref<Building[]>([])
const sections = ref<Section[]>([])
const floors = ref<Floor[]>([])
const apartments = ref<Apartment[]>([])
const loading = ref(false)
const expanded = ref<{ buildings: Set<number>; sections: Set<number>; floors: Set<number> }>({
  buildings: new Set(),
  sections: new Set(),
  floors: new Set(),
})

const canCreateBuilding = computed(() => permissions.check("objects.buildings.create"))
const canEditBuilding = computed(() => permissions.check("objects.buildings.edit"))
const canDeleteBuilding = computed(() => permissions.check("objects.buildings.delete"))
const canCreateSection = computed(() => permissions.check("objects.sections.create"))
const canEditSection = computed(() => permissions.check("objects.sections.edit"))
const canDeleteSection = computed(() => permissions.check("objects.sections.delete"))
const canCreateFloor = computed(() => permissions.check("objects.floors.create"))
const canEditFloor = computed(() => permissions.check("objects.floors.edit"))
const canDeleteFloor = computed(() => permissions.check("objects.floors.delete"))
const canCreateApartment = computed(() =>
  permissions.check("objects.apartments.edit"),
)
const canEditApartment = computed(() =>
  permissions.check("objects.apartments.edit"),
)
const canDeleteApartment = computed(() =>
  permissions.check("objects.apartments.delete"),
)
const canChangeStatus = computed(() =>
  permissions.check("objects.apartments.change_status"),
)
const canChangeFloorPrice = computed(() =>
  permissions.check("objects.floors.edit_price"),
)
const canBook = computed(() => permissions.check("objects.apartments.book"))
const canBookVip = computed(() => permissions.check("objects.apartments.book_vip"))

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

async function load() {
  loading.value = true
  try {
    project.value = await projectsApi.retrieve(projectId.value)
    const bs = await buildingsApi.list({ project: projectId.value, limit: 200 })
    buildings.value = bs.results
    if (buildings.value.length) {
      const [ss, fs, apts] = await Promise.all([
        sectionsApi.list({ limit: 500 }),
        floorsApi.list({ limit: 1000 }),
        apartmentsApi.list({ limit: 5000 }),
      ])
      const buildingIds = new Set(buildings.value.map((b) => b.id))
      sections.value = ss.results.filter((s) => buildingIds.has(s.building))
      const sectionIds = new Set(sections.value.map((s) => s.id))
      floors.value = fs.results.filter((f) => sectionIds.has(f.section))
      const floorIds = new Set(floors.value.map((f) => f.id))
      apartments.value = apts.results.filter((a) => floorIds.has(a.floor))
    } else {
      sections.value = []
      floors.value = []
      apartments.value = []
    }
  } finally {
    loading.value = false
  }
}

// --- Derived groupings ----------------------------------------------------

function sectionsFor(buildingId: number): Section[] {
  return sections.value.filter((s) => s.building === buildingId)
}
function floorsFor(sectionId: number): Floor[] {
  return floors.value.filter((f) => f.section === sectionId)
}
function apartmentsFor(floorId: number): Apartment[] {
  return apartments.value.filter((a) => a.floor === floorId)
}

function toggleBuilding(id: number) {
  if (expanded.value.buildings.has(id)) expanded.value.buildings.delete(id)
  else expanded.value.buildings.add(id)
}
function toggleSection(id: number) {
  if (expanded.value.sections.has(id)) expanded.value.sections.delete(id)
  else expanded.value.sections.add(id)
}
function toggleFloor(id: number) {
  if (expanded.value.floors.has(id)) expanded.value.floors.delete(id)
  else expanded.value.floors.add(id)
}

// --- Modal state ---------------------------------------------------------

type ModalKind =
  | "building"
  | "section"
  | "floor"
  | "apartment"
  | "status"
  | "book"
  | "price"
  | "duplicate_section"
interface ModalState {
  kind: ModalKind
  parentId: number
  editingId: number | null
  /** For `status` / `book` modals: the apartment whose state we're changing. */
  targetApt?: Apartment
  /** For `price` modal: the floor whose price we're changing. */
  targetFloor?: Floor
  /** For `duplicate_section`: the building we're cloning INTO. */
  targetBuildingId?: number
}

const showModal = ref(false)
const modalState = ref<ModalState | null>(null)
const saveError = ref<string | null>(null)

const buildingForm = reactive<BuildingWrite>({
  project: 0,
  title: emptyI18n(),
  number: "",
  cadastral_number: "",
  date_of_issue: null,
  sort: 0,
  is_active: true,
})

const sectionForm = reactive<SectionWrite>({
  building: 0,
  title: emptyI18n(),
  number: 1,
  sort: 0,
  is_active: true,
})

const floorForm = reactive<FloorWrite>({
  section: 0,
  number: 1,
  price_per_sqm: "0.00",
  sort: 0,
  is_active: true,
})

const apartmentForm = reactive<ApartmentWrite>({
  floor: 0,
  number: "",
  rooms_count: 1,
  area: "0.00",
  total_bti_area: "0.00",
  total_price: "0.00",
  surcharge: "0.00",
  is_duplex: false,
  is_studio: false,
  is_euro_planning: false,
  decoration: null,
  output_window: null,
  occupied_by: null,
  characteristics: [],
  status: "free",
  sort: 0,
  is_active: true,
})

const statusForm = reactive<{ new_status: ApartmentStatus; comment: string }>({
  new_status: "booked",
  comment: "",
})

const bookForm = reactive<{ duration_days: number; comment: string; vip: boolean }>({
  duration_days: 7,
  comment: "",
  vip: false,
})

const priceForm = reactive<{ new_price: string; comment: string }>({
  new_price: "0.00",
  comment: "",
})

const priceHistory = ref<PriceHistory[]>([])
const cascadeResult = ref<string | null>(null)

// Duplicate-section modal state: holds catalog data (loaded lazily on first
// open) plus the currently picked source in the cascading dropdowns.
const allProjects = ref<Project[]>([])
const allBuildings = ref<Building[]>([])
const allSections = ref<Section[]>([])
const duplicateForm = reactive<{
  source_project_id: number | null
  source_building_id: number | null
  source_section_id: number | null
}>({
  source_project_id: null,
  source_building_id: null,
  source_section_id: null,
})
const duplicateResult = ref<string | null>(null)

function openBuildingCreate() {
  modalState.value = { kind: "building", parentId: projectId.value, editingId: null }
  Object.assign(buildingForm, {
    project: projectId.value,
    title: emptyI18n(),
    number: "",
    cadastral_number: "",
    date_of_issue: null,
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openBuildingEdit(b: Building) {
  modalState.value = { kind: "building", parentId: projectId.value, editingId: b.id }
  Object.assign(buildingForm, {
    project: b.project,
    title: { ...b.title },
    number: b.number,
    cadastral_number: b.cadastral_number,
    date_of_issue: b.date_of_issue,
    sort: b.sort,
    is_active: b.is_active,
  })
  saveError.value = null
  showModal.value = true
}

function openSectionCreate(buildingId: number) {
  modalState.value = { kind: "section", parentId: buildingId, editingId: null }
  const next = Math.max(0, ...sectionsFor(buildingId).map((s) => s.number)) + 1
  Object.assign(sectionForm, {
    building: buildingId,
    title: emptyI18n(),
    number: next,
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openSectionEdit(s: Section) {
  modalState.value = { kind: "section", parentId: s.building, editingId: s.id }
  Object.assign(sectionForm, {
    building: s.building,
    title: { ...s.title },
    number: s.number,
    sort: s.sort,
    is_active: s.is_active,
  })
  saveError.value = null
  showModal.value = true
}

function openFloorCreate(sectionId: number) {
  modalState.value = { kind: "floor", parentId: sectionId, editingId: null }
  const next = Math.max(0, ...floorsFor(sectionId).map((f) => f.number)) + 1
  Object.assign(floorForm, {
    section: sectionId,
    number: next,
    price_per_sqm: "0.00",
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openFloorEdit(f: Floor) {
  modalState.value = { kind: "floor", parentId: f.section, editingId: f.id }
  Object.assign(floorForm, {
    section: f.section,
    number: f.number,
    price_per_sqm: f.price_per_sqm,
    sort: f.sort,
    is_active: f.is_active,
  })
  saveError.value = null
  showModal.value = true
}

function openApartmentCreate(floorId: number) {
  modalState.value = { kind: "apartment", parentId: floorId, editingId: null }
  const existing = apartmentsFor(floorId)
  const maxNum = existing
    .map((a) => Number(a.number))
    .filter((n) => !Number.isNaN(n))
  const next = (maxNum.length ? Math.max(...maxNum) : 0) + 1
  Object.assign(apartmentForm, {
    floor: floorId,
    number: String(next),
    rooms_count: 1,
    area: "0.00",
    total_bti_area: "0.00",
    total_price: "0.00",
    surcharge: "0.00",
    is_duplex: false,
    is_studio: false,
    is_euro_planning: false,
    decoration: null,
    output_window: null,
    occupied_by: null,
    characteristics: [],
    status: "free",
    sort: 0,
    is_active: true,
  })
  saveError.value = null
  showModal.value = true
}
function openApartmentEdit(a: Apartment) {
  modalState.value = { kind: "apartment", parentId: a.floor, editingId: a.id }
  Object.assign(apartmentForm, {
    floor: a.floor,
    number: a.number,
    rooms_count: a.rooms_count,
    area: a.area,
    total_bti_area: a.total_bti_area,
    total_price: a.total_price,
    surcharge: a.surcharge,
    is_duplex: a.is_duplex,
    is_studio: a.is_studio,
    is_euro_planning: a.is_euro_planning,
    decoration: a.decoration,
    output_window: a.output_window,
    occupied_by: a.occupied_by,
    characteristics: [...a.characteristics],
    status: a.status,
    sort: a.sort,
    is_active: a.is_active,
  })
  saveError.value = null
  showModal.value = true
}

function openStatusModal(a: Apartment) {
  modalState.value = {
    kind: "status",
    parentId: a.floor,
    editingId: a.id,
    targetApt: a,
  }
  // Pick a reasonable default that's actually a legal transition.
  const first = allowedNextStatuses(a.status)[0]
  statusForm.new_status = first || "free"
  statusForm.comment = ""
  saveError.value = null
  showModal.value = true
}

function openBookModal(a: Apartment) {
  modalState.value = {
    kind: "book",
    parentId: a.floor,
    editingId: a.id,
    targetApt: a,
  }
  bookForm.duration_days = 7
  bookForm.comment = ""
  bookForm.vip = false
  saveError.value = null
  showModal.value = true
}

async function doRelease(a: Apartment) {
  const comment = prompt(t("objects.apartments.comment") + " (опц.)", "") || ""
  try {
    await apartmentsApi.release(a.id, comment)
    await load()
  } catch (e) {
    alert(
      e instanceof AxiosError
        ? JSON.stringify(e.response?.data)
        : t("errors.unknown"),
    )
  }
}

async function openDuplicateSectionModal(targetBuildingId: number) {
  modalState.value = {
    kind: "duplicate_section",
    parentId: targetBuildingId,
    editingId: null,
    targetBuildingId,
  }
  duplicateForm.source_project_id = null
  duplicateForm.source_building_id = null
  duplicateForm.source_section_id = null
  duplicateResult.value = null
  saveError.value = null
  // Load catalog once per session — projects / all buildings / all sections.
  if (!allProjects.value.length) {
    const [ps, bs, ss] = await Promise.all([
      projectsApi.list({ limit: 500 }),
      buildingsApi.list({ limit: 2000 }),
      sectionsApi.list({ limit: 5000 }),
    ])
    allProjects.value = ps.results
    allBuildings.value = bs.results
    allSections.value = ss.results
  }
  showModal.value = true
}

async function openPriceModal(f: Floor) {
  modalState.value = {
    kind: "price",
    parentId: f.section,
    editingId: f.id,
    targetFloor: f,
  }
  priceForm.new_price = f.price_per_sqm
  priceForm.comment = ""
  cascadeResult.value = null
  saveError.value = null
  // Fetch this floor's price history for the side panel. Best-effort —
  // permission may be denied for roles without floor view access.
  try {
    const data = await priceHistoryApi.list({ floor: f.id, limit: 20 })
    priceHistory.value = data.results
  } catch {
    priceHistory.value = []
  }
  showModal.value = true
}

// --- Duplicate-section cascade helpers ----------------------------------

const availableSourceBuildings = computed<Building[]>(() => {
  const pid = duplicateForm.source_project_id
  if (!pid) return []
  return allBuildings.value.filter((b) => b.project === pid)
})
const availableSourceSections = computed<Section[]>(() => {
  const bid = duplicateForm.source_building_id
  if (!bid) return []
  return allSections.value.filter((s) => s.building === bid)
})
function onSourceProjectChange() {
  duplicateForm.source_building_id = null
  duplicateForm.source_section_id = null
}
function onSourceBuildingChange() {
  duplicateForm.source_section_id = null
}

// Keep in sync with services/apartments.py#_ALLOWED_TRANSITIONS.
const TRANSITIONS: Record<ApartmentStatus, ApartmentStatus[]> = {
  free: ["booked", "booked_vip"],
  booked: ["free", "formalized"],
  booked_vip: ["free", "formalized"],
  formalized: ["free", "escrow"],
  escrow: ["formalized", "sold"],
  sold: ["free"],
}
function allowedNextStatuses(cur: ApartmentStatus): ApartmentStatus[] {
  return TRANSITIONS[cur] || []
}

async function save() {
  if (!modalState.value) return
  saveError.value = null
  const { kind, editingId } = modalState.value
  try {
    if (kind === "building") {
      if (editingId) await buildingsApi.update(editingId, buildingForm)
      else await buildingsApi.create(buildingForm)
    } else if (kind === "section") {
      if (editingId) await sectionsApi.update(editingId, sectionForm)
      else await sectionsApi.create(sectionForm)
    } else if (kind === "floor") {
      if (editingId) await floorsApi.update(editingId, floorForm)
      else await floorsApi.create(floorForm)
    } else if (kind === "apartment") {
      if (editingId) await apartmentsApi.update(editingId, apartmentForm)
      else await apartmentsApi.create(apartmentForm)
    } else if (kind === "status" && editingId) {
      await apartmentsApi.changeStatus(
        editingId,
        statusForm.new_status,
        statusForm.comment,
      )
    } else if (kind === "book" && editingId) {
      await apartmentsApi.book(
        editingId,
        bookForm.duration_days,
        bookForm.comment,
        bookForm.vip,
      )
    } else if (kind === "price" && editingId) {
      const stats = await floorsApi.changePrice(
        editingId,
        priceForm.new_price,
        priceForm.comment,
      )
      cascadeResult.value = t("objects.floors.cascade_done", {
        apts: stats.apartments_updated,
        calcs: stats.calculations_upserted,
      })
      await load()
      // Refresh history panel.
      const h = await priceHistoryApi.list({ floor: editingId, limit: 20 })
      priceHistory.value = h.results
      return  // keep the modal open so user sees the cascade result
    } else if (kind === "duplicate_section") {
      if (!duplicateForm.source_section_id || !modalState.value.targetBuildingId) {
        return
      }
      const res = await sectionsApi.duplicate(
        duplicateForm.source_section_id,
        modalState.value.targetBuildingId,
      )
      duplicateResult.value = t("objects.sections.duplicate_result", {
        floors: res.floors_created,
        apts: res.apartments_created,
      })
      await load()
      return  // keep modal open to show the result banner
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

async function removeBuilding(b: Building) {
  if (!confirm(`${t("objects.buildings.confirm_delete")}?`)) return
  try {
    await buildingsApi.destroy(b.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}
async function removeSection(s: Section) {
  if (!confirm(`${t("objects.sections.confirm_delete")}?`)) return
  try {
    await sectionsApi.destroy(s.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}
async function removeFloor(f: Floor) {
  if (!confirm(`${t("objects.floors.confirm_delete")}?`)) return
  try {
    await floorsApi.destroy(f.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}
async function removeApartment(a: Apartment) {
  if (!confirm(`${t("objects.apartments.confirm_delete")}?`)) return
  try {
    await apartmentsApi.destroy(a.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
  }
}

function localized(item: { title?: I18nText } | null): string {
  if (!item?.title) return ""
  return item.title[locale.value as keyof I18nText] || ""
}

function projectTitle(): string {
  if (!project.value) return ""
  return localized(project.value) || `#${project.value.id}`
}
function developerName(): string {
  if (!project.value?.developer_name) return "—"
  return project.value.developer_name[locale.value as keyof I18nText] || "—"
}

function fmtPrice(v: string): string {
  const n = Number(v)
  if (Number.isNaN(n)) return v
  return new Intl.NumberFormat("ru-RU").format(n) + " UZS"
}

/** Map apartment status → chip class. Kept close to the backend status set. */
function statusChipClass(s: ApartmentStatus): string {
  switch (s) {
    case "free":
      return "chip chip-success"
    case "booked":
      return "chip chip-warn"
    case "booked_vip":
      return "chip chip-primary"
    case "formalized":
    case "escrow":
      return "chip chip-info"
    case "sold":
      return "chip chip-ghost"
  }
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
          <span>{{ t("objects.projects.title") }}</span>
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ projectTitle() }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          <i class="pi pi-wrench text-[10px] mr-1.5" />
          {{ developerName() }}
          <span v-if="project?.address" class="mx-2">·</span>
          <span v-if="project?.address">{{ project.address }}</span>
        </div>
      </div>
      <button
        v-if="canCreateBuilding"
        class="btn btn-primary"
        @click="openBuildingCreate"
      >
        <i class="pi pi-plus text-[11px]" />
        {{ t("objects.buildings.new") }}
      </button>
    </div>

    <div class="flex gap-1 mb-5 border-b border-ym-line-soft">
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-ym-primary text-ym-primary font-medium"
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
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}/shaxmatka`)"
      >
        {{ t("objects.tabs.shaxmatka") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="!buildings.length" class="card p-8 text-center text-ym-muted">
      {{ t("objects.buildings.empty") }}
    </div>

    <div v-else class="space-y-3">
      <div v-for="b in buildings" :key="b.id" class="card overflow-hidden">
        <!-- Building row -->
        <div class="flex items-center gap-3 px-5 py-4 border-b border-ym-line-soft">
          <button class="btn btn-ghost btn-icon btn-xs" @click="toggleBuilding(b.id)">
            <i
              :class="[
                'pi',
                expanded.buildings.has(b.id) ? 'pi-chevron-down' : 'pi-chevron-right',
                'text-[11px]',
              ]"
            />
          </button>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ localized(b) || `#${b.id}` }}</span>
              <span v-if="b.number" class="chip chip-ghost">
                {{ t("objects.buildings.fields.number") }}: {{ b.number }}
              </span>
            </div>
            <div class="text-[12px] text-ym-muted mt-0.5">
              {{ t("objects.columns.sections_count") }}: {{ b.sections_count }}
            </div>
          </div>
          <div class="flex items-center gap-1">
            <button
              v-if="canCreateSection"
              class="btn btn-soft btn-xs"
              @click="openSectionCreate(b.id)"
            >
              <i class="pi pi-plus text-[10px]" />
              {{ t("objects.sections.new") }}
            </button>
            <button
              v-if="canCreateSection"
              class="btn btn-soft btn-xs"
              @click="openDuplicateSectionModal(b.id)"
            >
              <i class="pi pi-clone text-[10px]" />
              {{ t("objects.sections.duplicate") }}
            </button>
            <button
              v-if="canEditBuilding"
              class="btn btn-ghost btn-xs"
              @click="openBuildingEdit(b)"
            >
              {{ t("common.edit") }}
            </button>
            <button
              v-if="canDeleteBuilding"
              class="btn btn-danger btn-xs"
              @click="removeBuilding(b)"
            >
              {{ t("common.delete") }}
            </button>
          </div>
        </div>

        <!-- Sections inside a building -->
        <div v-if="expanded.buildings.has(b.id)" class="bg-ym-sunken/40">
          <div v-if="!sectionsFor(b.id).length" class="px-5 py-4 text-[12.5px] text-ym-muted">
            {{ t("objects.sections.empty") }}
          </div>

          <div
            v-for="s in sectionsFor(b.id)"
            :key="s.id"
            class="border-b last:border-b-0 border-ym-line-soft"
          >
            <div class="flex items-center gap-3 pl-10 pr-5 py-3">
              <button class="btn btn-ghost btn-icon btn-xs" @click="toggleSection(s.id)">
                <i
                  :class="[
                    'pi',
                    expanded.sections.has(s.id) ? 'pi-chevron-down' : 'pi-chevron-right',
                    'text-[11px]',
                  ]"
                />
              </button>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[13.5px]">
                  <i class="pi pi-sign-in text-[11px] text-ym-subtle" />
                  <span>{{ localized(s) || `${t("objects.sections.fields.number")} ${s.number}` }}</span>
                </div>
                <div class="text-[11.5px] text-ym-muted mt-0.5">
                  {{ t("objects.columns.floors_count") }}: {{ s.floors_count }}
                </div>
              </div>
              <div class="flex items-center gap-1">
                <button v-if="canCreateFloor" class="btn btn-soft btn-xs" @click="openFloorCreate(s.id)">
                  <i class="pi pi-plus text-[10px]" />
                  {{ t("objects.floors.new") }}
                </button>
                <button v-if="canEditSection" class="btn btn-ghost btn-xs" @click="openSectionEdit(s)">
                  {{ t("common.edit") }}
                </button>
                <button v-if="canDeleteSection" class="btn btn-danger btn-xs" @click="removeSection(s)">
                  {{ t("common.delete") }}
                </button>
              </div>
            </div>

            <!-- Floors inside a section -->
            <div v-if="expanded.sections.has(s.id)" class="pl-16 pr-5 pb-3 bg-ym-bg/40">
              <div v-if="!floorsFor(s.id).length" class="text-[12px] text-ym-muted py-2">
                {{ t("objects.floors.empty") }}
              </div>

              <div
                v-for="f in floorsFor(s.id)"
                :key="f.id"
                class="mb-1.5 last:mb-0 bg-white rounded-md border border-ym-line-soft overflow-hidden"
              >
                <div class="flex items-center gap-3 px-3 py-2">
                  <button class="btn btn-ghost btn-icon btn-xs" @click="toggleFloor(f.id)">
                    <i
                      :class="[
                        'pi',
                        expanded.floors.has(f.id) ? 'pi-chevron-down' : 'pi-chevron-right',
                        'text-[10px]',
                      ]"
                    />
                  </button>
                  <div class="flex-1 min-w-0 text-[12.5px] flex items-center gap-3">
                    <span class="font-mono">{{ t("objects.columns.number") }}: {{ f.number }}</span>
                    <span class="text-ym-muted">·</span>
                    <span class="font-mono text-ym-muted">{{ fmtPrice(f.price_per_sqm) }}</span>
                    <span class="text-ym-muted">·</span>
                    <span class="text-ym-muted">{{ t("objects.columns.apartments_count") }}: {{ f.apartments_count }}</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <button
                      v-if="canCreateApartment"
                      class="btn btn-soft btn-xs"
                      @click="openApartmentCreate(f.id)"
                    >
                      <i class="pi pi-plus text-[10px]" />
                      {{ t("objects.apartments.new") }}
                    </button>
                    <button
                      v-if="canChangeFloorPrice"
                      class="btn btn-soft btn-xs"
                      @click="openPriceModal(f)"
                    >
                      <i class="pi pi-dollar text-[10px]" />
                      {{ t("objects.floors.change_price") }}
                    </button>
                    <button v-if="canEditFloor" class="btn btn-ghost btn-xs" @click="openFloorEdit(f)">
                      {{ t("common.edit") }}
                    </button>
                    <button v-if="canDeleteFloor" class="btn btn-danger btn-xs" @click="removeFloor(f)">
                      {{ t("common.delete") }}
                    </button>
                  </div>
                </div>

                <!-- Apartments inside a floor -->
                <div v-if="expanded.floors.has(f.id)" class="border-t border-ym-line-soft bg-ym-sunken/30">
                  <div v-if="!apartmentsFor(f.id).length" class="px-5 py-3 text-[12px] text-ym-muted">
                    {{ t("objects.apartments.empty") }}
                  </div>
                  <table v-else class="tbl">
                    <thead>
                      <tr>
                        <th>{{ t("objects.columns.number") }}</th>
                        <th>{{ t("objects.columns.rooms") }}</th>
                        <th>{{ t("objects.columns.area") }}</th>
                        <th>{{ t("objects.columns.price") }}</th>
                        <th>{{ t("objects.columns.status") }}</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="a in apartmentsFor(f.id)" :key="a.id">
                        <td class="font-mono">{{ a.number }}</td>
                        <td class="font-mono">{{ a.rooms_count }}</td>
                        <td class="font-mono text-[12.5px]">{{ a.area }}</td>
                        <td class="font-mono text-[12.5px]">{{ fmtPrice(a.total_price) }}</td>
                        <td>
                          <span :class="statusChipClass(a.status)">
                            {{ t(`objects.apartments.status.${a.status}`) }}
                          </span>
                        </td>
                        <td class="text-right whitespace-nowrap">
                          <button
                            v-if="a.status === 'free' && canBook"
                            class="btn btn-primary btn-xs mr-1"
                            @click="openBookModal(a)"
                          >
                            <i class="pi pi-bookmark text-[10px]" />
                            {{ t("objects.apartments.book") }}
                          </button>
                          <button
                            v-if="
                              (a.status === 'booked' || a.status === 'booked_vip') &&
                                canChangeStatus
                            "
                            class="btn btn-soft btn-xs mr-1"
                            @click="doRelease(a)"
                          >
                            {{ t("objects.apartments.release") }}
                          </button>
                          <button
                            v-if="canChangeStatus"
                            class="btn btn-ghost btn-xs mr-1"
                            @click="openStatusModal(a)"
                          >
                            {{ t("objects.apartments.change_status") }}
                          </button>
                          <button
                            v-if="canEditApartment"
                            class="btn btn-ghost btn-xs mr-1"
                            @click="openApartmentEdit(a)"
                          >
                            {{ t("common.edit") }}
                          </button>
                          <button
                            v-if="canDeleteApartment"
                            class="btn btn-danger btn-xs"
                            @click="removeApartment(a)"
                          >
                            {{ t("common.delete") }}
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal dispatches by kind -->
    <div
      v-if="showModal && modalState"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="showModal = false"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          <template v-if="modalState.kind === 'building'">
            {{ modalState.editingId ? t("objects.buildings.edit") : t("objects.buildings.new") }}
          </template>
          <template v-else-if="modalState.kind === 'section'">
            {{ modalState.editingId ? t("objects.sections.edit") : t("objects.sections.new") }}
          </template>
          <template v-else-if="modalState.kind === 'floor'">
            {{ modalState.editingId ? t("objects.floors.edit") : t("objects.floors.new") }}
          </template>
          <template v-else-if="modalState.kind === 'apartment'">
            {{ modalState.editingId ? t("objects.apartments.edit") : t("objects.apartments.new") }}
          </template>
          <template v-else-if="modalState.kind === 'book'">
            {{ t("objects.apartments.book_title") }}
          </template>
          <template v-else-if="modalState.kind === 'price'">
            {{ t("objects.floors.price_change_title") }}
          </template>
          <template v-else-if="modalState.kind === 'duplicate_section'">
            {{ t("objects.sections.duplicate_title") }}
          </template>
          <template v-else>
            {{ t("objects.apartments.change_status") }}
          </template>
        </h2>

        <!-- Building form -->
        <template v-if="modalState.kind === 'building'">
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.buildings.fields.title") }}
            </label>
            <div class="grid grid-cols-3 gap-2">
              <input v-model="buildingForm.title.ru" class="inp" placeholder="RU" />
              <input v-model="buildingForm.title.uz" class="inp" placeholder="UZ" />
              <input v-model="buildingForm.title.oz" class="inp" placeholder="ОЗ" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.buildings.fields.number") }}
              </label>
              <input v-model="buildingForm.number" class="inp font-mono" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.buildings.fields.cadastral_number") }}
              </label>
              <input v-model="buildingForm.cadastral_number" class="inp font-mono" />
            </div>
            <div class="col-span-2">
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.buildings.fields.date_of_issue") }}
              </label>
              <input v-model="buildingForm.date_of_issue" type="date" class="inp" />
            </div>
          </div>
        </template>

        <!-- Section form -->
        <template v-else-if="modalState.kind === 'section'">
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.sections.fields.title") }}
            </label>
            <div class="grid grid-cols-3 gap-2">
              <input v-model="sectionForm.title.ru" class="inp" placeholder="RU" />
              <input v-model="sectionForm.title.uz" class="inp" placeholder="UZ" />
              <input v-model="sectionForm.title.oz" class="inp" placeholder="ОЗ" />
            </div>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.sections.fields.number") }}
            </label>
            <input v-model.number="sectionForm.number" type="number" min="1" class="inp font-mono" />
          </div>
        </template>

        <!-- Floor form -->
        <template v-else-if="modalState.kind === 'floor'">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.floors.fields.number") }}
              </label>
              <input v-model.number="floorForm.number" type="number" class="inp font-mono" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.floors.fields.price_per_sqm") }}
              </label>
              <input v-model="floorForm.price_per_sqm" class="inp font-mono" placeholder="15000000.00" />
            </div>
          </div>
        </template>

        <!-- Apartment form -->
        <template v-else-if="modalState.kind === 'apartment'">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.fields.number") }}
              </label>
              <input v-model="apartmentForm.number" class="inp font-mono" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.fields.rooms_count") }}
              </label>
              <input
                v-model.number="apartmentForm.rooms_count"
                type="number"
                min="0"
                class="inp font-mono"
              />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.fields.area") }}
              </label>
              <input v-model="apartmentForm.area" class="inp font-mono" placeholder="50.00" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.fields.total_price") }}
              </label>
              <input v-model="apartmentForm.total_price" class="inp font-mono" placeholder="750000000.00" />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.fields.surcharge") }}
              </label>
              <input v-model="apartmentForm.surcharge" class="inp font-mono" placeholder="0.00" />
            </div>
          </div>
          <div class="mt-4 flex gap-4 text-sm">
            <label class="flex items-center gap-2">
              <input v-model="apartmentForm.is_studio" type="checkbox" />
              <span>{{ t("objects.apartments.fields.is_studio") }}</span>
            </label>
            <label class="flex items-center gap-2">
              <input v-model="apartmentForm.is_duplex" type="checkbox" />
              <span>{{ t("objects.apartments.fields.is_duplex") }}</span>
            </label>
            <label class="flex items-center gap-2">
              <input v-model="apartmentForm.is_euro_planning" type="checkbox" />
              <span>{{ t("objects.apartments.fields.is_euro_planning") }}</span>
            </label>
          </div>
        </template>

        <!-- Status change form -->
        <template v-else-if="modalState.kind === 'status' && modalState.targetApt">
          <div class="mb-3 text-[13px] text-ym-muted">
            <span class="font-mono">#{{ modalState.targetApt.number }}</span>
            · {{ t("objects.columns.status") }}:
            <span :class="statusChipClass(modalState.targetApt.status)">
              {{ t(`objects.apartments.status.${modalState.targetApt.status}`) }}
            </span>
          </div>
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.apartments.new_status") }}
            </label>
            <select v-model="statusForm.new_status" class="inp">
              <option
                v-for="s in allowedNextStatuses(modalState.targetApt.status)"
                :key="s"
                :value="s"
              >
                {{ t(`objects.apartments.status.${s}`) }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.apartments.comment") }}
            </label>
            <textarea v-model="statusForm.comment" class="inp" rows="3" />
          </div>
        </template>

        <!-- Book apartment form -->
        <template v-else-if="modalState.kind === 'book' && modalState.targetApt">
          <div class="mb-3 text-[13px] text-ym-muted">
            <span class="font-mono">#{{ modalState.targetApt.number }}</span>
            · {{ modalState.targetApt.rooms_count }}
            {{ t("objects.columns.rooms") }}
            · {{ modalState.targetApt.area }} м²
          </div>
          <div class="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.apartments.duration_days") }}
              </label>
              <input
                v-model.number="bookForm.duration_days"
                type="number"
                min="1"
                max="365"
                class="inp font-mono"
              />
            </div>
            <div>
              <label v-if="canBookVip" class="flex items-center gap-2 text-sm mt-7">
                <input v-model="bookForm.vip" type="checkbox" />
                <span>{{ t("objects.apartments.vip_checkbox") }}</span>
              </label>
            </div>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.apartments.comment") }}
            </label>
            <textarea v-model="bookForm.comment" class="inp" rows="3" />
          </div>
        </template>

        <!-- Change floor price form -->
        <template v-else-if="modalState.kind === 'price' && modalState.targetFloor">
          <div class="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.floors.old_price") }}
              </label>
              <div class="inp font-mono bg-ym-sunken/40">
                {{ fmtPrice(modalState.targetFloor.price_per_sqm) }}
              </div>
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("objects.floors.new_price_label") }}
              </label>
              <input v-model="priceForm.new_price" class="inp font-mono" />
            </div>
          </div>
          <div class="mb-4 text-[12.5px] text-ym-muted">
            <i class="pi pi-info-circle text-[10px] mr-1" />
            {{ t("objects.floors.cascade_preview", { count: modalState.targetFloor.apartments_count }) }}
          </div>
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.apartments.comment") }}
            </label>
            <textarea v-model="priceForm.comment" class="inp" rows="2" />
          </div>
          <div v-if="cascadeResult" class="mb-4 text-[12.5px] text-ym-success bg-ym-success-soft px-3 py-2 rounded">
            <i class="pi pi-check text-[10px] mr-1" />
            {{ cascadeResult }}
          </div>

          <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-2">
            {{ t("objects.floors.price_history") }}
          </div>
          <div
            v-if="!priceHistory.length"
            class="text-[12px] text-ym-muted"
          >
            {{ t("objects.floors.price_history_empty") }}
          </div>
          <table v-else class="tbl">
            <thead>
              <tr>
                <th>{{ t("objects.floors.old_price") }}</th>
                <th>{{ t("objects.floors.new_price_label") }}</th>
                <th>{{ t("common.edit") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in priceHistory" :key="h.id">
                <td class="font-mono text-[12.5px]">{{ fmtPrice(h.old_price) }}</td>
                <td class="font-mono text-[12.5px]">{{ fmtPrice(h.new_price) }}</td>
                <td class="text-[12px] text-ym-muted">
                  {{ h.changed_by_name || "—" }}
                  · {{ new Date(h.created_at).toLocaleString() }}
                </td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- Duplicate section form -->
        <template v-else-if="modalState.kind === 'duplicate_section'">
          <div class="mb-3 text-[12.5px] text-ym-muted">
            {{ t("objects.sections.duplicate_desc") }}
          </div>
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.sections.source_project") }}
            </label>
            <select
              v-model.number="duplicateForm.source_project_id"
              class="inp"
              @change="onSourceProjectChange"
            >
              <option :value="null">—</option>
              <option v-for="p in allProjects" :key="p.id" :value="p.id">
                {{ p.title[locale as keyof I18nText] || `#${p.id}` }}
              </option>
            </select>
          </div>
          <div class="mb-4">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.sections.source_building") }}
            </label>
            <select
              v-model.number="duplicateForm.source_building_id"
              class="inp"
              :disabled="!duplicateForm.source_project_id"
              @change="onSourceBuildingChange"
            >
              <option :value="null">—</option>
              <option v-for="b in availableSourceBuildings" :key="b.id" :value="b.id">
                {{ b.title[locale as keyof I18nText] || `#${b.id}` }}
                <span v-if="b.number"> ({{ b.number }})</span>
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("objects.sections.source_section") }}
            </label>
            <select
              v-model.number="duplicateForm.source_section_id"
              class="inp"
              :disabled="!duplicateForm.source_building_id"
            >
              <option :value="null">—</option>
              <option v-for="s in availableSourceSections" :key="s.id" :value="s.id">
                №{{ s.number }}
                <span v-if="s.title[locale as keyof I18nText]">
                  — {{ s.title[locale as keyof I18nText] }}
                </span>
                · {{ t("objects.columns.floors_count") }}: {{ s.floors_count }}
              </option>
            </select>
          </div>
          <div
            v-if="duplicateResult"
            class="mt-4 text-[12.5px] text-ym-success bg-ym-success-soft px-3 py-2 rounded"
          >
            <i class="pi pi-check text-[10px] mr-1" />
            {{ duplicateResult }}
          </div>
        </template>

        <label
          v-if="!['status', 'book', 'price', 'duplicate_section'].includes(modalState.kind)"
          class="flex items-center gap-2 text-sm mt-5"
        >
          <input
            v-if="modalState.kind === 'building'"
            v-model="buildingForm.is_active"
            type="checkbox"
          />
          <input
            v-else-if="modalState.kind === 'section'"
            v-model="sectionForm.is_active"
            type="checkbox"
          />
          <input
            v-else-if="modalState.kind === 'floor'"
            v-model="floorForm.is_active"
            type="checkbox"
          />
          <input v-else v-model="apartmentForm.is_active" type="checkbox" />
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
