<script setup lang="ts">
/**
 * InventoryPicker — modal that lets the user pick an apartment from a
 * visual floor × apartment grid.
 *
 * Used by the contract wizard in place of the native <select>. Managers
 * work off the inventory grid every day, so the same layout is used here
 * (building / section tabs, highest floor on top, status-tinted cells).
 *
 * Usage:
 *   <InventoryPicker
 *     v-model="open"
 *     :project-id="projectId"
 *     @pick="onApartmentPicked"
 *   />
 *
 * Only apartments with status "sold" are disabled. Free and
 * booked/formalized/escrow can still be selected — a manager may need
 * to issue a contract against a held apartment, and the final
 * validation happens on contract submit.
 */
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

import { projectsApi } from "@/api/objects"
import type {
  Apartment,
  ApartmentStatus,
  Building,
  Floor,
  Section,
} from "@/types/models"

const props = defineProps<{
  modelValue: boolean
  projectId: number | null
  /** Pre-selected apartment id — highlights that cell on open. */
  selectedId?: number | null
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void
  (e: "pick", apartment: Apartment): void
}>()

const { t } = useI18n()

const loading = ref(false)
const buildings = ref<Building[]>([])
const sections = ref<Section[]>([])
const floors = ref<Floor[]>([])
const apartments = ref<Apartment[]>([])

const selectedBuildingId = ref<number | null>(null)
const selectedSectionId = ref<number | null>(null)
const roomsFilter = ref<number | null>(null)

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    const tree = await projectsApi.inventory(props.projectId)
    buildings.value = tree.buildings
    sections.value = tree.sections
    floors.value = tree.floors
    apartments.value = tree.apartments

    if (!buildings.value.length) return

    // Pre-select tab: if an apartment is already chosen, navigate to
    // its building/section so its cell is visible on open. Otherwise
    // default to the first building + first section.
    if (props.selectedId) {
      const apt = apartments.value.find((a) => a.id === props.selectedId)
      if (apt) {
        const floor = floors.value.find((f) => f.id === apt.floor)
        const section = sections.value.find((s) => s.id === floor?.section)
        if (section) {
          selectedSectionId.value = section.id
          selectedBuildingId.value = section.building
          return
        }
      }
    }
    selectedBuildingId.value = buildings.value[0]?.id ?? null
    const firstSection = sections.value.find(
      (s) => s.building === selectedBuildingId.value,
    )
    selectedSectionId.value = firstSection?.id ?? null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    document.body.style.overflow = open ? "hidden" : ""
    if (open) void load()
  },
)

// --- Derived --------------------------------------------------------------

const sectionsOfCurrentBuilding = computed<Section[]>(() =>
  sections.value.filter((s) => s.building === selectedBuildingId.value),
)

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
  const firstSection = sections.value.find((s) => s.building === id)
  selectedSectionId.value = firstSection?.id ?? null
}

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

const legendStatuses: ApartmentStatus[] = [
  "free",
  "booked",
  "booked_vip",
  "formalized",
  "escrow",
  "sold",
]

function fmtPrice(v: string): string {
  const n = Number(v)
  if (Number.isNaN(n)) return v
  return new Intl.NumberFormat("ru-RU").format(n)
}

function pick(a: Apartment) {
  if (a.status === "sold") return
  emit("pick", a)
  emit("update:modelValue", false)
}

function close() {
  emit("update:modelValue", false)
}
</script>

<template>
  <Teleport to="body">
    <transition name="picker">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[180] bg-black/40 flex items-center justify-center p-4"
      >
        <div
          class="card w-full max-w-6xl max-h-[92vh] flex flex-col shadow-ym-modal"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between px-5 py-3.5 border-b border-ym-line-soft"
          >
            <div>
              <div
                class="text-[11px] uppercase tracking-[0.12em] font-mono text-ym-subtle mb-0.5"
              >
                {{ t("objects.tabs.inventory") }}
              </div>
              <h2 class="text-[17px] font-semibold leading-none">
                Выберите квартиру
              </h2>
            </div>
            <button
              type="button"
              class="btn btn-ghost btn-icon"
              :title="t('common.close')"
              @click="close"
            >
              <i class="pi pi-times text-[12px]" />
            </button>
          </div>

          <div class="flex-1 overflow-auto art-scroll p-5">
            <div v-if="loading" class="text-ym-muted">
              {{ t("common.loading") }}
            </div>
            <div
              v-else-if="!projectId"
              class="card p-8 text-center text-ym-muted"
            >
              {{ t("contracts.wizard.select_project") }}
            </div>
            <div
              v-else-if="!buildings.length"
              class="card p-8 text-center text-ym-muted"
            >
              {{ t("objects.inventory.no_data") }}
            </div>

            <template v-else>
              <!-- Building tabs -->
              <div class="flex flex-wrap items-center gap-4 mb-3">
                <div class="flex items-center gap-2">
                  <span
                    class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle"
                  >
                    {{ t("objects.inventory.select_building") }}
                  </span>
                  <div class="flex gap-1">
                    <button
                      v-for="b in buildings"
                      :key="b.id"
                      type="button"
                      class="chip"
                      :class="
                        b.id === selectedBuildingId
                          ? 'chip-primary'
                          : 'chip-ghost'
                      "
                      @click="selectBuilding(b.id)"
                    >
                      {{ b.number || b.id }}
                    </button>
                  </div>
                </div>
                <div
                  v-if="sectionsOfCurrentBuilding.length"
                  class="flex items-center gap-2"
                >
                  <span
                    class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle"
                  >
                    {{ t("objects.inventory.select_section") }}
                  </span>
                  <div class="flex gap-1 flex-wrap">
                    <button
                      v-for="s in sectionsOfCurrentBuilding"
                      :key="s.id"
                      type="button"
                      class="chip"
                      :class="
                        s.id === selectedSectionId
                          ? 'chip-primary'
                          : 'chip-ghost'
                      "
                      @click="selectedSectionId = s.id"
                    >
                      {{ s.number }}
                    </button>
                  </div>
                </div>
                <div
                  v-if="roomsOptions.length"
                  class="flex items-center gap-2 ml-auto"
                >
                  <span
                    class="text-[12px] uppercase tracking-wider font-mono text-ym-subtle"
                  >
                    {{ t("objects.inventory.filter_rooms") }}
                  </span>
                  <div class="flex gap-1">
                    <button
                      type="button"
                      class="chip"
                      :class="
                        roomsFilter === null ? 'chip-primary' : 'chip-ghost'
                      "
                      @click="roomsFilter = null"
                    >
                      {{ t("objects.inventory.filter_all") }}
                    </button>
                    <button
                      v-for="r in roomsOptions"
                      :key="r"
                      type="button"
                      class="chip"
                      :class="
                        roomsFilter === r ? 'chip-primary' : 'chip-ghost'
                      "
                      @click="roomsFilter = r"
                    >
                      {{ r }}к
                    </button>
                  </div>
                </div>
              </div>

              <!-- Legend -->
              <div class="flex flex-wrap gap-3 mb-4">
                <div
                  v-for="s in legendStatuses"
                  :key="s"
                  class="flex items-center gap-2 text-[12px] text-ym-muted"
                >
                  <span
                    :class="[
                      'inline-block w-3.5 h-3.5 rounded-sm',
                      cellClass(s),
                    ]"
                  />
                  {{ t(`objects.apartments.status.${s}`) }}
                </div>
              </div>

              <!-- Grid -->
              <div
                v-if="!selectedSectionId"
                class="card p-8 text-center text-ym-muted"
              >
                {{ t("objects.inventory.no_data") }}
              </div>
              <div v-else class="card overflow-x-auto art-scroll">
                <div class="min-w-fit">
                  <div
                    v-for="f in floorsOfSection"
                    :key="f.id"
                    class="flex items-stretch border-b last:border-b-0 border-ym-line-soft"
                  >
                    <div
                      class="flex-none w-14 flex items-center justify-center border-r border-ym-line-soft bg-ym-sunken/40 font-mono text-[13px] font-semibold text-ym-subtle"
                    >
                      {{ f.number }}
                    </div>
                    <div
                      v-if="!apartmentsOfFloor(f.id).length"
                      class="flex-1 flex items-center px-3 text-[11.5px] text-ym-muted italic py-2"
                    >
                      {{ t("objects.inventory.empty_floor") }}
                    </div>
                    <div v-else class="flex flex-wrap gap-1.5 p-2">
                      <button
                        v-for="a in apartmentsOfFloor(f.id)"
                        :key="a.id"
                        type="button"
                        :disabled="a.status === 'sold'"
                        :class="[
                          cellClass(a.status),
                          'w-[96px] h-[58px] rounded-md px-2 py-1 text-left transition',
                          a.status === 'sold'
                            ? 'opacity-60 cursor-not-allowed'
                            : 'hover:brightness-110 hover:shadow-ym-card',
                          selectedId === a.id
                            ? 'ring-2 ring-offset-1 ring-ym-primary'
                            : '',
                        ]"
                        @click="pick(a)"
                      >
                        <div
                          class="font-mono text-[13px] font-semibold leading-none"
                        >
                          {{ a.number }}
                        </div>
                        <div class="text-[10.5px] opacity-90 mt-0.5">
                          {{ a.rooms_count }}к · {{ a.area }}м²
                        </div>
                        <div
                          class="text-[10.5px] font-mono opacity-90 mt-0.5 truncate"
                        >
                          {{ fmtPrice(a.total_price) }}
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <div
            class="px-5 py-3 border-t border-ym-line-soft flex justify-between items-center text-[12px] text-ym-muted"
          >
            <span>
              Кликните по любой квартире, кроме «{{
                t("objects.apartments.status.sold")
              }}» — она будет выбрана и появится в карточке договора.
            </span>
            <button class="btn btn-ghost" @click="close">
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.picker-enter-active,
.picker-leave-active {
  transition: opacity 150ms ease;
}
.picker-enter-from,
.picker-leave-to {
  opacity: 0;
}
</style>
