<script setup lang="ts">
/**
 * SalesOffices CRUD (references.SalesOffice).
 *
 * Same pattern as Developers. Lat/lon and work hours are optional; backend
 * validates coord ranges. Photo upload (multipart) is deferred until a
 * dedicated file-upload utility lands — for now we expose the field in
 * read-only form if already set.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"

import ToggleSwitch from "@/components/ToggleSwitch.vue"
import { salesOfficesApi } from "@/api/references"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import type { I18nText, SalesOffice, SalesOfficeWrite } from "@/types/models"

const { t, locale } = useI18n()
const permissions = usePermissionStore()
const confirmStore = useConfirmStore()

const items = ref<SalesOffice[]>([])
const loading = ref(false)
const editing = ref<SalesOffice | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

function emptyForm(): SalesOfficeWrite {
  return {
    name: emptyI18n(),
    address: "",
    latitude: null,
    longitude: null,
    work_start: null,
    work_end: null,
    phone: "",
    is_active: true,
  }
}

const form = reactive<SalesOfficeWrite>(emptyForm())

const canCreate = computed(() => permissions.check("references.offices.create"))
const canEdit = computed(() => permissions.check("references.offices.edit"))
const canDelete = computed(() => permissions.check("references.offices.delete"))

async function load() {
  loading.value = true
  try {
    const data = await salesOfficesApi.list({ limit: 200 })
    items.value = data.results
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

function openEdit(item: SalesOffice) {
  editing.value = item
  Object.assign(form, {
    name: { ...item.name },
    address: item.address,
    latitude: item.latitude,
    longitude: item.longitude,
    work_start: item.work_start,
    work_end: item.work_end,
    phone: item.phone,
    is_active: item.is_active,
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  saveError.value = null
  // Trim empty lat/lon to null so backend doesn't reject empty strings.
  const payload: SalesOfficeWrite = {
    ...form,
    latitude: form.latitude === "" ? null : form.latitude,
    longitude: form.longitude === "" ? null : form.longitude,
    work_start: form.work_start || null,
    work_end: form.work_end || null,
  }
  try {
    if (editing.value) {
      await salesOfficesApi.update(editing.value.id, payload)
    } else {
      await salesOfficesApi.create(payload)
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

async function remove(item: SalesOffice) {
  const nameLoc = item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
  const ok = await confirmStore.ask({
    title: t("references.sales_offices.confirm_delete"),
    message: nameLoc,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  await salesOfficesApi.destroy(item.id)
  await load()
}

function localizedName(item: SalesOffice): string {
  return item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
}

function fmtCoords(item: SalesOffice): string {
  if (item.latitude == null || item.longitude == null) return "—"
  return `${item.latitude}, ${item.longitude}`
}

function fmtWorkHours(item: SalesOffice): string {
  if (!item.work_start || !item.work_end) return "—"
  // "HH:MM:SS" → "HH:MM"
  return `${item.work_start.slice(0, 5)}–${item.work_end.slice(0, 5)}`
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle">
          {{ t("nav.references") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("references.sales_offices.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.sales_offices.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.sales_offices.new") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="items.length === 0" class="card p-8 text-center text-ym-muted">
      {{ t("common.no_data") }}
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("references.columns.name") }}</th>
            <th>{{ t("references.columns.address") }}</th>
            <th>{{ t("references.columns.coords") }}</th>
            <th>{{ t("references.columns.work_hours") }}</th>
            <th>{{ t("references.columns.phone") }}</th>
            <th>{{ t("references.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id">
            <td class="font-medium">{{ localizedName(i) }}</td>
            <td class="text-ym-muted">{{ i.address || "—" }}</td>
            <td class="font-mono text-[12.5px]">{{ fmtCoords(i) }}</td>
            <td class="font-mono text-[12.5px]">{{ fmtWorkHours(i) }}</td>
            <td class="font-mono text-[12.5px]">{{ i.phone || "—" }}</td>
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

    <!-- Modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("references.sales_offices.edit") : t("references.sales_offices.new") }}
        </h2>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("references.columns.name") }}
          </label>
          <div class="grid grid-cols-3 gap-2">
            <input v-model="form.name.ru" class="inp" placeholder="RU" />
            <input v-model="form.name.uz" class="inp" placeholder="UZ" />
            <input v-model="form.name.oz" class="inp" placeholder="ОЗ" />
          </div>
        </div>

        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-3">
          {{ t("references.sales_offices.section_location") }}
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.address") }}
            </label>
            <input v-model="form.address" class="inp" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.latitude") }}
            </label>
            <input v-model="form.latitude" class="inp font-mono" placeholder="41.3111" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.longitude") }}
            </label>
            <input v-model="form.longitude" class="inp font-mono" placeholder="69.2797" />
          </div>
        </div>

        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-3">
          {{ t("references.sales_offices.section_work") }}
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.phone") }}
            </label>
            <input v-model="form.phone" placeholder="+998712345678" class="inp font-mono" />
          </div>
          <div></div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.work_start") }}
            </label>
            <input v-model="form.work_start" type="time" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.sales_offices.fields.work_end") }}
            </label>
            <input v-model="form.work_end" type="time" class="inp font-mono" />
          </div>
        </div>

        <div class="mt-5">
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
