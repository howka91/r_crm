<script setup lang="ts">
/**
 * Lookups universal screen — one page for all 13 LookupModel-based references.
 *
 * Left sidebar: type selector (chips) — sticky within the page. Right: list
 * + inline add/edit form. Extras (color/region/percent) are rendered
 * conditionally based on the selected type's metadata.
 *
 * The selected type is encoded in the query string (`?type=room-type`) so
 * links deep-link correctly and language switches don't reset state.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import ToggleSwitch from "@/components/ToggleSwitch.vue"
import { lookupsApi, lookupTypes } from "@/api/references"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import type {
  BadgeItem,
  I18nText,
  LocationItem,
  LookupItem,
  LookupTypeSlug,
  PaymentInPercentItem,
} from "@/types/models"

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()
const confirmStore = useConfirmStore()

const items = ref<LookupItem[]>([])
const regions = ref<LookupItem[]>([])
const loading = ref(false)
const editing = ref<LookupItem | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

const selectedType = computed<LookupTypeSlug>(() => {
  const q = route.query.type
  const cand = typeof q === "string" ? q : lookupTypes[0]!.slug
  return (lookupTypes.find((lt) => lt.slug === cand)?.slug ?? lookupTypes[0]!.slug)
})

const selectedMeta = computed(
  () => lookupTypes.find((lt) => lt.slug === selectedType.value)!,
)

const canCreate = computed(() => permissions.check("references.lookups.create"))
const canEdit = computed(() => permissions.check("references.lookups.edit"))
const canDelete = computed(() => permissions.check("references.lookups.delete"))

interface LookupForm {
  name: I18nText
  sort: number
  is_active: boolean
  color: string
  percent: string
  region: number | null
}

function emptyForm(): LookupForm {
  return {
    name: { ru: "", uz: "", oz: "" },
    sort: 0,
    is_active: true,
    color: "",
    percent: "0.00",
    region: null,
  }
}

const form = reactive<LookupForm>(emptyForm())

function setType(slug: LookupTypeSlug) {
  if (slug === selectedType.value) return
  router.replace({ query: { ...route.query, type: slug } })
}

async function load() {
  loading.value = true
  try {
    const data = await lookupsApi[selectedType.value].list({ limit: 500 })
    items.value = data.results
    // Location needs a region picker — prefetch regions on demand.
    if (selectedType.value === "location") {
      const rr = await lookupsApi.region.list({ limit: 500 })
      regions.value = rr.results
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, emptyForm())
  saveError.value = null
  showModal.value = true
}

function openEdit(item: LookupItem) {
  editing.value = item
  const f: LookupForm = {
    name: { ...item.name },
    sort: item.sort,
    is_active: item.is_active,
    color: "",
    percent: "0.00",
    region: null,
  }
  if (selectedMeta.value.extras.includes("color")) {
    f.color = (item as BadgeItem).color ?? ""
  }
  if (selectedMeta.value.extras.includes("percent")) {
    f.percent = (item as PaymentInPercentItem).percent ?? "0.00"
  }
  if (selectedMeta.value.extras.includes("region")) {
    f.region = (item as LocationItem).region ?? null
  }
  Object.assign(form, f)
  saveError.value = null
  showModal.value = true
}

function buildPayload(): Record<string, unknown> {
  const p: Record<string, unknown> = {
    name: form.name,
    sort: form.sort,
    is_active: form.is_active,
  }
  if (selectedMeta.value.extras.includes("color")) p.color = form.color
  if (selectedMeta.value.extras.includes("percent")) p.percent = form.percent
  if (selectedMeta.value.extras.includes("region")) p.region = form.region
  return p
}

async function save() {
  saveError.value = null
  const api = lookupsApi[selectedType.value]
  try {
    if (editing.value) {
      await api.update(editing.value.id, buildPayload())
    } else {
      await api.create(buildPayload())
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

async function remove(item: LookupItem) {
  const nameLoc = item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
  const ok = await confirmStore.ask({
    title: t("references.lookups.confirm_delete"),
    message: nameLoc,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  await lookupsApi[selectedType.value].destroy(item.id)
  await load()
}

function localizedName(item: LookupItem): string {
  return item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
}

function regionName(id: number | null): string {
  if (id == null) return "—"
  const r = regions.value.find((x) => x.id === id)
  return r ? localizedName(r) : `#${id}`
}

onMounted(load)
watch(selectedType, load)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle">
          {{ t("nav.references") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("references.lookups.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.lookups.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.lookups.new_item") }}
      </button>
    </div>

    <div class="grid grid-cols-[260px_1fr] gap-4">
      <!-- Type selector -->
      <aside class="card p-3 self-start">
        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle px-2 mb-2">
          {{ t("references.lookups.select_type") }}
        </div>
        <div class="flex flex-col gap-1">
          <button
            v-for="lt in lookupTypes"
            :key="lt.slug"
            type="button"
            :class="[
              'text-left text-[13px] px-3 py-2 rounded-md transition-colors cursor-pointer',
              selectedType === lt.slug
                ? 'bg-ym-primary-soft text-ym-primary-h font-medium'
                : 'text-ym-muted hover:bg-ym-sunken hover:text-ym-text',
            ]"
            @click="setType(lt.slug)"
          >
            {{ t(`references.lookups.types.${lt.labelKey}`) }}
          </button>
        </div>
      </aside>

      <!-- Data column -->
      <section>
        <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

        <div v-else-if="items.length === 0" class="card p-8 text-center text-ym-muted">
          {{ t("references.lookups.empty") }}
        </div>

        <div v-else class="card overflow-hidden">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t("references.columns.name") }}</th>
                <th v-if="selectedMeta.extras.includes('color')">
                  {{ t("references.columns.color") }}
                </th>
                <th v-if="selectedMeta.extras.includes('percent')">
                  {{ t("references.columns.percent") }}
                </th>
                <th v-if="selectedMeta.extras.includes('region')">
                  {{ t("references.columns.region") }}
                </th>
                <th>{{ t("references.columns.sort") }}</th>
                <th>{{ t("references.columns.status") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in items" :key="i.id">
                <td class="font-medium">{{ localizedName(i) }}</td>
                <td v-if="selectedMeta.extras.includes('color')">
                  <span class="inline-flex items-center gap-2">
                    <span
                      class="w-4 h-4 rounded border border-ym-line"
                      :style="{ background: (i as BadgeItem).color || 'transparent' }"
                    />
                    <span class="font-mono text-[12.5px]">{{ (i as BadgeItem).color || "—" }}</span>
                  </span>
                </td>
                <td v-if="selectedMeta.extras.includes('percent')" class="font-mono">
                  {{ (i as PaymentInPercentItem).percent }}%
                </td>
                <td v-if="selectedMeta.extras.includes('region')" class="text-ym-muted">
                  {{ regionName((i as LocationItem).region) }}
                </td>
                <td class="font-mono text-ym-subtle">{{ i.sort }}</td>
                <td>
                  <span :class="i.is_active ? 'chip chip-success' : 'chip chip-ghost'">
                    {{ i.is_active ? t("common.active") : t("common.inactive") }}
                  </span>
                </td>
                <td class="text-right whitespace-nowrap">
                  <button v-if="canEdit" class="btn btn-ghost btn-sm mr-2" @click="openEdit(i)">
                    {{ t("common.edit") }}
                  </button>
                  <button v-if="canDelete" class="btn btn-danger btn-sm" @click="remove(i)">
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
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div class="card w-full max-w-md p-6 shadow-ym-modal">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("references.lookups.edit_item") : t("references.lookups.new_item") }}
          <span class="text-ym-muted font-normal ml-2">
            · {{ t(`references.lookups.types.${selectedMeta.labelKey}`) }}
          </span>
        </h2>

        <div class="space-y-3 text-sm">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.columns.name") }}
            </label>
            <div class="grid grid-cols-3 gap-2">
              <input v-model="form.name.ru" class="inp" placeholder="RU" />
              <input v-model="form.name.uz" class="inp" placeholder="UZ" />
              <input v-model="form.name.oz" class="inp" placeholder="ОЗ" />
            </div>
          </div>

          <div v-if="selectedMeta.extras.includes('color')">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.columns.color") }}
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model="form.color"
                type="color"
                class="w-10 h-10 rounded-md border border-ym-line cursor-pointer bg-transparent"
              />
              <input v-model="form.color" class="inp font-mono" placeholder="#22C55E" />
            </div>
          </div>

          <div v-if="selectedMeta.extras.includes('percent')">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.columns.percent") }}
            </label>
            <input v-model="form.percent" class="inp font-mono" placeholder="30.00" />
          </div>

          <div v-if="selectedMeta.extras.includes('region')">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.columns.region") }}
            </label>
            <select v-model="form.region" class="inp">
              <option :value="null">—</option>
              <option v-for="r in regions" :key="r.id" :value="r.id">
                {{ localizedName(r) }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.columns.sort") }}
            </label>
            <input v-model.number="form.sort" type="number" class="inp font-mono w-32" />
          </div>

          <ToggleSwitch
            v-model="form.is_active"
            :active-label="t('common.active')"
            :inactive-label="t('common.inactive')"
          />
        </div>

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
