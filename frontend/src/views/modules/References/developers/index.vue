<script setup lang="ts">
/**
 * Developers CRUD (references.Developer).
 *
 * Layout mirrors `views/modules/Administration/userManagement/index.vue`:
 * header + card-wrapped table + per-row ghost/danger buttons + a custom
 * div-overlay modal. PrimeVue Dialog substitution is tracked as tech debt
 * in SESSION_STATE.md.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"

import { developersApi } from "@/api/references"
import { usePermissionStore } from "@/store/permissions"
import type { Developer, DeveloperWrite, I18nText } from "@/types/models"

const { t, locale } = useI18n()
const permissions = usePermissionStore()

const items = ref<Developer[]>([])
const loading = ref(false)
const editing = ref<Developer | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

function emptyForm(): DeveloperWrite {
  return {
    name: emptyI18n(),
    director: "",
    address: "",
    email: "",
    phone: "",
    bank_name: "",
    bank_account: "",
    inn: "",
    nds: "",
    oked: "",
    extra: {},
    is_active: true,
  }
}

const form = reactive<DeveloperWrite>(emptyForm())

const canCreate = computed(() => permissions.check("references.developers.create"))
const canEdit = computed(() => permissions.check("references.developers.edit"))
const canDelete = computed(() => permissions.check("references.developers.delete"))

async function load() {
  loading.value = true
  try {
    const data = await developersApi.list({ limit: 200 })
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

function openEdit(item: Developer) {
  editing.value = item
  Object.assign(form, {
    name: { ...item.name },
    director: item.director,
    address: item.address,
    email: item.email,
    phone: item.phone,
    bank_name: item.bank_name,
    bank_account: item.bank_account,
    inn: item.inn,
    nds: item.nds,
    oked: item.oked,
    extra: { ...item.extra },
    is_active: item.is_active,
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  saveError.value = null
  try {
    if (editing.value) {
      await developersApi.update(editing.value.id, form)
    } else {
      await developersApi.create(form)
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

async function remove(item: Developer) {
  const nameLoc = item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
  if (!confirm(`${t("references.developers.confirm_delete")}: ${nameLoc}?`)) return
  await developersApi.destroy(item.id)
  await load()
}

function localizedName(item: Developer): string {
  return item.name[locale.value as "ru" | "uz" | "oz"] || `#${item.id}`
}

onMounted(load)
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
          {{ t("references.developers.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.developers.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.developers.new") }}
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
            <th>{{ t("references.columns.director") }}</th>
            <th>{{ t("references.columns.phone") }}</th>
            <th>{{ t("references.columns.inn") }}</th>
            <th>{{ t("references.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id">
            <td class="font-medium">{{ localizedName(i) }}</td>
            <td class="text-ym-muted">{{ i.director || "—" }}</td>
            <td class="font-mono text-[12.5px]">{{ i.phone || "—" }}</td>
            <td class="font-mono text-[12.5px]">{{ i.inn || "—" }}</td>
            <td>
              <span :class="i.is_active ? 'chip chip-success' : 'chip chip-ghost'">
                {{ i.is_active ? t("common.yes") : t("common.no") }}
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
      @click.self="showModal = false"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("references.developers.edit") : t("references.developers.new") }}
        </h2>

        <!-- Name (3 locales) -->
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

        <!-- Contacts section -->
        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-3">
          {{ t("references.developers.section_contacts") }}
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.director") }}
            </label>
            <input v-model="form.director" class="inp" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.phone") }}
            </label>
            <input v-model="form.phone" placeholder="+998901234567" class="inp font-mono" />
          </div>
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.address") }}
            </label>
            <input v-model="form.address" class="inp" />
          </div>
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.email") }}
            </label>
            <input v-model="form.email" type="email" class="inp" />
          </div>
        </div>

        <!-- Bank section -->
        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-3">
          {{ t("references.developers.section_bank") }}
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.bank_name") }}
            </label>
            <input v-model="form.bank_name" class="inp" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.bank_account") }}
            </label>
            <input v-model="form.bank_account" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.inn") }}
            </label>
            <input v-model="form.inn" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.nds") }}
            </label>
            <input v-model="form.nds" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.developers.fields.oked") }}
            </label>
            <input v-model="form.oked" class="inp font-mono" />
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm mt-5">
          <input v-model="form.is_active" type="checkbox" />
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
