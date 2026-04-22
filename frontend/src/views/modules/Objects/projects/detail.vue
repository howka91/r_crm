<script setup lang="ts">
/**
 * Project detail — nested drill-down for Buildings → Sections → Floors.
 *
 * We load all children for the project up front (one request each) — in practice
 * no project has more than a few hundred apartments total, so 3 round-trips on
 * mount is fine. Apartment (phase 3.2) will change this to lazy-load per floor.
 *
 * A single modal handles create/edit for all 3 child entity types. Entity kind
 * and parent id are encoded in `modalState` so the template can render the
 * right form body.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { buildingsApi, floorsApi, projectsApi, sectionsApi } from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import type {
  Building,
  BuildingWrite,
  Floor,
  FloorWrite,
  I18nText,
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
const loading = ref(false)
const expanded = ref<{ buildings: Set<number>; sections: Set<number> }>({
  buildings: new Set(),
  sections: new Set(),
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
      // Load sections for every building via a single request (filter by
      // `building__in` would be ideal — we approximate by loading all and
      // filtering client-side since totals are small).
      const ss = await sectionsApi.list({ limit: 500 })
      sections.value = ss.results.filter((s) =>
        buildings.value.some((b) => b.id === s.building),
      )
      const fs = await floorsApi.list({ limit: 1000 })
      floors.value = fs.results.filter((f) =>
        sections.value.some((s) => s.id === f.section),
      )
    } else {
      sections.value = []
      floors.value = []
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

function toggleBuilding(id: number) {
  if (expanded.value.buildings.has(id)) expanded.value.buildings.delete(id)
  else expanded.value.buildings.add(id)
}
function toggleSection(id: number) {
  if (expanded.value.sections.has(id)) expanded.value.sections.delete(id)
  else expanded.value.sections.add(id)
}

// --- Modal state ---------------------------------------------------------

type ModalKind = "building" | "section" | "floor"
interface ModalState {
  kind: ModalKind
  /** Parent id (project for buildings, building for sections, section for floors). */
  parentId: number
  /** If editing — the current item id; null if creating. */
  editingId: number | null
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

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
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

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="!buildings.length" class="card p-8 text-center text-ym-muted">
      {{ t("objects.buildings.empty") }}
    </div>

    <div v-else class="space-y-3">
      <div v-for="b in buildings" :key="b.id" class="card overflow-hidden">
        <div class="flex items-center gap-3 px-5 py-4 border-b border-ym-line-soft">
          <button
            class="btn btn-ghost btn-icon btn-xs"
            @click="toggleBuilding(b.id)"
          >
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
              <button
                class="btn btn-ghost btn-icon btn-xs"
                @click="toggleSection(s.id)"
              >
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
                <button
                  v-if="canCreateFloor"
                  class="btn btn-soft btn-xs"
                  @click="openFloorCreate(s.id)"
                >
                  <i class="pi pi-plus text-[10px]" />
                  {{ t("objects.floors.new") }}
                </button>
                <button
                  v-if="canEditSection"
                  class="btn btn-ghost btn-xs"
                  @click="openSectionEdit(s)"
                >
                  {{ t("common.edit") }}
                </button>
                <button
                  v-if="canDeleteSection"
                  class="btn btn-danger btn-xs"
                  @click="removeSection(s)"
                >
                  {{ t("common.delete") }}
                </button>
              </div>
            </div>

            <div v-if="expanded.sections.has(s.id)" class="pl-16 pr-5 pb-3 bg-ym-bg/40">
              <div v-if="!floorsFor(s.id).length" class="text-[12px] text-ym-muted py-2">
                {{ t("objects.floors.empty") }}
              </div>
              <table v-else class="tbl">
                <thead>
                  <tr>
                    <th>{{ t("objects.columns.number") }}</th>
                    <th>{{ t("objects.columns.price_per_sqm") }}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="f in floorsFor(s.id)" :key="f.id">
                    <td class="font-mono">{{ f.number }}</td>
                    <td class="font-mono text-[12.5px]">{{ fmtPrice(f.price_per_sqm) }}</td>
                    <td class="text-right whitespace-nowrap">
                      <button
                        v-if="canEditFloor"
                        class="btn btn-ghost btn-xs mr-1"
                        @click="openFloorEdit(f)"
                      >
                        {{ t("common.edit") }}
                      </button>
                      <button
                        v-if="canDeleteFloor"
                        class="btn btn-danger btn-xs"
                        @click="removeFloor(f)"
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

    <!-- Modal (building / section / floor create+edit) -->
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
          <template v-else>
            {{ modalState.editingId ? t("objects.floors.edit") : t("objects.floors.new") }}
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

        <label class="flex items-center gap-2 text-sm mt-5">
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
            v-else
            v-model="floorForm.is_active"
            type="checkbox"
          />
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
