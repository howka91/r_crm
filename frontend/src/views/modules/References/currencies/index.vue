<script setup lang="ts">
/**
 * Currencies CRUD (references.Currency).
 *
 * Simplest of the rich entities: ISO 4217 code (uppercased on save server-side),
 * symbol, multilingual name, rate-to-UZS decimal.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"

import { currenciesApi } from "@/api/references"
import { usePermissionStore } from "@/store/permissions"
import type { Currency, CurrencyWrite, I18nText } from "@/types/models"

const { t, locale } = useI18n()
const permissions = usePermissionStore()

const items = ref<Currency[]>([])
const loading = ref(false)
const editing = ref<Currency | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

function emptyForm(): CurrencyWrite {
  return {
    code: "",
    symbol: "",
    name: emptyI18n(),
    rate: "1.0000",
    is_active: true,
  }
}

const form = reactive<CurrencyWrite>(emptyForm())

const canCreate = computed(() => permissions.check("references.currencies.create"))
const canEdit = computed(() => permissions.check("references.currencies.edit"))
const canDelete = computed(() => permissions.check("references.currencies.delete"))

async function load() {
  loading.value = true
  try {
    const data = await currenciesApi.list({ limit: 200 })
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

function openEdit(item: Currency) {
  editing.value = item
  Object.assign(form, {
    code: item.code,
    symbol: item.symbol,
    name: { ...item.name },
    rate: item.rate,
    is_active: item.is_active,
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  saveError.value = null
  try {
    if (editing.value) {
      await currenciesApi.update(editing.value.id, form)
    } else {
      await currenciesApi.create(form)
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

async function remove(item: Currency) {
  if (!confirm(`${t("references.currencies.confirm_delete")}: ${item.code}?`)) return
  await currenciesApi.destroy(item.id)
  await load()
}

function localizedName(item: Currency): string {
  return item.name[locale.value as "ru" | "uz" | "oz"] || item.code
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
          {{ t("references.currencies.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.currencies.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.currencies.new") }}
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
            <th>{{ t("references.columns.code") }}</th>
            <th>{{ t("references.columns.symbol") }}</th>
            <th>{{ t("references.columns.name") }}</th>
            <th>{{ t("references.columns.rate") }}</th>
            <th>{{ t("references.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id">
            <td class="font-mono text-[12.5px] text-ym-primary font-semibold">{{ i.code }}</td>
            <td class="font-mono">{{ i.symbol || "—" }}</td>
            <td class="font-medium">{{ localizedName(i) }}</td>
            <td class="font-mono">{{ i.rate }}</td>
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
      <div class="card w-full max-w-md p-6 shadow-ym-modal">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("references.currencies.edit") : t("references.currencies.new") }}
        </h2>

        <div class="space-y-3 text-sm">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("references.currencies.fields.code") }}
              </label>
              <input
                v-model="form.code"
                class="inp font-mono uppercase"
                maxlength="3"
                placeholder="USD"
              />
            </div>
            <div>
              <label class="block text-[12px] font-medium mb-1.5">
                {{ t("references.currencies.fields.symbol") }}
              </label>
              <input v-model="form.symbol" class="inp font-mono" maxlength="4" placeholder="$" />
            </div>
          </div>

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

          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.currencies.fields.rate") }}
            </label>
            <input v-model="form.rate" class="inp font-mono" placeholder="12500.0000" />
          </div>

          <label class="flex items-center gap-2">
            <input v-model="form.is_active" type="checkbox" />
            <span>{{ t("common.yes") }} / {{ t("common.no") }}</span>
          </label>
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
