<script setup lang="ts">
/**
 * Clients list.
 *
 * Table with entity / status / manager / search filters; click a row →
 * detail page. Create modal is minimal (just entity + name) — everything
 * else is edited on the detail page.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { staffApi } from "@/api/administration"
import {
  clientGroupsApi,
  clientStatusesApi,
  clientsApi,
} from "@/api/clients"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type {
  Client,
  ClientEntity,
  ClientGender,
  ClientGroup,
  ClientStatus,
  ClientWrite,
  I18nText,
  Staff,
} from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const items = ref<Client[]>([])
const statuses = ref<ClientStatus[]>([])
const groups = ref<ClientGroup[]>([])
const managers = ref<Staff[]>([])
const loading = ref(false)

const filters = reactive<{
  entity: ClientEntity | ""
  status: number | null
  manager: string | ""
  search: string
}>({
  entity: "",
  status: null,
  manager: "",
  search: "",
})

const canCreate = computed(() => permissions.check("clients.create"))
const canDelete = computed(() => permissions.check("clients.delete"))

function toastApiError(e: unknown) {
  if (e instanceof AxiosError && e.response?.data) {
    const body = e.response.data
    toast.error(
      t("errors.unknown"),
      typeof body === "object" ? JSON.stringify(body) : String(body),
    )
  } else {
    toast.error(t("errors.unknown"))
  }
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { limit: 200 }
    if (filters.entity) params.entity = filters.entity
    if (filters.status) params.status = filters.status
    if (filters.manager) params.manager = filters.manager
    if (filters.search.trim()) params.search = filters.search.trim()
    const data = await clientsApi.list(params)
    items.value = data.results
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [s, g, st] = await Promise.all([
    clientStatusesApi.list({ limit: 200 }),
    clientGroupsApi.list({ limit: 200 }),
    staffApi.list({ limit: 500 }),
  ])
  statuses.value = s.results
  groups.value = g.results
  managers.value = st.results
  await load()
})

// Debounced reload on filter change.
let reloadTimer: number | null = null
watch(filters, () => {
  if (reloadTimer) window.clearTimeout(reloadTimer)
  reloadTimer = window.setTimeout(() => {
    reloadTimer = null
    load()
  }, 300)
}, { deep: true })

// --- Create modal --------------------------------------------------------

const showCreate = ref(false)
const createError = ref<string | null>(null)

function emptyForm(): ClientWrite {
  return {
    entity: "phys",
    gender: "" as ClientGender,
    full_name: "",
    phones: [],
    emails: [],
    inn: "",
    oked: "",
    pin: "",
    birth_date: null,
    address: "",
    description: "",
    manager: null,
    status: null,
    groups: [],
    is_active: true,
  }
}
const form = reactive<ClientWrite>(emptyForm())
const phoneDraft = ref("")

function openCreate() {
  Object.assign(form, emptyForm())
  createError.value = null
  phoneDraft.value = ""
  showCreate.value = true
}

function addPhone() {
  const p = phoneDraft.value.trim()
  if (!p) return
  form.phones = [...form.phones, p]
  phoneDraft.value = ""
}
function removePhone(i: number) {
  form.phones = form.phones.filter((_, idx) => idx !== i)
}

async function saveCreate() {
  createError.value = null
  try {
    const payload: ClientWrite = {
      ...form,
      gender: form.entity === "jur" ? "" : form.gender,
    }
    const created = await clientsApi.create(payload)
    toast.success(t("clients.new"))
    showCreate.value = false
    router.push(`/clients/${created.id}`)
  } catch (e) {
    createError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

// --- Row actions ---------------------------------------------------------

async function remove(c: Client) {
  const ok = await confirmStore.ask({
    title: t("clients.confirm_delete"),
    message: c.full_name,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await clientsApi.destroy(c.id)
    toast.success(t("clients.confirm_delete"))
    await load()
  } catch (e) {
    toastApiError(e)
  }
}

function statusChipStyle(c: Client) {
  if (!c.status_name) return "chip chip-ghost"
  const status = statuses.value.find((s) => s.id === c.status)
  if (status?.color) {
    return `chip text-white`
  }
  return "chip chip-primary"
}
function statusChipColor(c: Client): string | undefined {
  const status = statuses.value.find((s) => s.id === c.status)
  return status?.color || undefined
}

function localizedStatus(c: Client): string {
  if (!c.status_name) return "—"
  return c.status_name[locale.value as keyof I18nText] || "—"
}

function firstPhone(c: Client): string {
  return c.phones[0] || "—"
}
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle">
          {{ t("nav.group_sales") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("clients.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("clients.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("clients.new") }}
      </button>
    </div>

    <!-- Filters -->
    <div class="card p-3 mb-4 flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-2">
        <button
          class="chip"
          :class="filters.entity === '' ? 'chip-primary' : 'chip-ghost'"
          @click="filters.entity = ''"
        >
          {{ t("objects.shaxmatka.filter_all") }}
        </button>
        <button
          class="chip"
          :class="filters.entity === 'phys' ? 'chip-primary' : 'chip-ghost'"
          @click="filters.entity = 'phys'"
        >
          {{ t("clients.entity_phys") }}
        </button>
        <button
          class="chip"
          :class="filters.entity === 'jur' ? 'chip-primary' : 'chip-ghost'"
          @click="filters.entity = 'jur'"
        >
          {{ t("clients.entity_jur") }}
        </button>
      </div>
      <select v-model.number="filters.status" class="inp inp-sm w-auto">
        <option :value="null">{{ t("clients.fields.status") }}: {{ t("objects.shaxmatka.filter_all") }}</option>
        <option v-for="s in statuses" :key="s.id" :value="s.id">
          {{ s.name[locale as keyof I18nText] || `#${s.id}` }}
        </option>
      </select>
      <select v-model="filters.manager" class="inp inp-sm w-auto">
        <option value="">{{ t("clients.fields.manager") }}: {{ t("objects.shaxmatka.filter_all") }}</option>
        <option v-for="m in managers" :key="m.id" :value="m.id">
          {{ m.full_name || m.email }}
        </option>
      </select>
      <input
        v-model="filters.search"
        class="inp inp-sm flex-1 min-w-[200px]"
        :placeholder="t('common.search') + '…'"
      />
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="items.length === 0"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("clients.empty") }}
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("clients.columns.name") }}</th>
            <th>{{ t("clients.columns.entity") }}</th>
            <th>{{ t("clients.columns.phone") }}</th>
            <th>{{ t("clients.columns.manager") }}</th>
            <th>{{ t("clients.columns.status") }}</th>
            <th class="text-center">{{ t("clients.columns.contacts") }}</th>
            <th class="text-center">{{ t("clients.columns.requisites") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in items"
            :key="c.id"
            class="cursor-pointer"
            @click="router.push(`/clients/${c.id}`)"
          >
            <td class="font-medium">{{ c.full_name }}</td>
            <td>
              <span class="chip chip-ghost">
                {{ c.entity === "phys" ? t("clients.entity_phys") : t("clients.entity_jur") }}
              </span>
            </td>
            <td class="font-mono text-[12.5px]">{{ firstPhone(c) }}</td>
            <td class="text-ym-muted">{{ c.manager_name || "—" }}</td>
            <td>
              <span
                :class="statusChipStyle(c)"
                :style="statusChipColor(c) ? `background:${statusChipColor(c)}` : undefined"
              >
                {{ localizedStatus(c) }}
              </span>
            </td>
            <td class="text-center font-mono">{{ c.contacts_count }}</td>
            <td class="text-center font-mono">{{ c.requisites_count }}</td>
            <td class="text-right whitespace-nowrap" @click.stop>
              <button
                v-if="canDelete"
                class="btn btn-danger btn-xs"
                @click="remove(c)"
              >
                {{ t("common.delete") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <div
      v-if="showCreate"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="showCreate = false"
    >
      <div class="card w-full max-w-xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">{{ t("clients.new") }}</h2>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.entity") }}
          </label>
          <div class="flex gap-2">
            <button
              class="chip"
              :class="form.entity === 'phys' ? 'chip-primary' : 'chip-ghost'"
              @click="form.entity = 'phys'"
            >
              {{ t("clients.entity_phys") }}
            </button>
            <button
              class="chip"
              :class="form.entity === 'jur' ? 'chip-primary' : 'chip-ghost'"
              @click="form.entity = 'jur'"
            >
              {{ t("clients.entity_jur") }}
            </button>
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.full_name") }}
          </label>
          <input v-model="form.full_name" class="inp" />
        </div>

        <div v-if="form.entity === 'phys'" class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.gender") }}
          </label>
          <div class="flex gap-2">
            <button
              class="chip"
              :class="form.gender === '' ? 'chip-primary' : 'chip-ghost'"
              @click="form.gender = ''"
            >
              —
            </button>
            <button
              class="chip"
              :class="form.gender === 'male' ? 'chip-primary' : 'chip-ghost'"
              @click="form.gender = 'male'"
            >
              {{ t("clients.gender_male") }}
            </button>
            <button
              class="chip"
              :class="form.gender === 'female' ? 'chip-primary' : 'chip-ghost'"
              @click="form.gender = 'female'"
            >
              {{ t("clients.gender_female") }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 mb-4">
          <div v-if="form.entity === 'phys'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.pin") }}
            </label>
            <input v-model="form.pin" class="inp font-mono" />
          </div>
          <div v-else>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.inn") }}
            </label>
            <input v-model="form.inn" class="inp font-mono" />
          </div>
          <div v-if="form.entity === 'phys'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.birth_date") }}
            </label>
            <input v-model="form.birth_date" type="date" class="inp" />
          </div>
          <div v-else>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.oked") }}
            </label>
            <input v-model="form.oked" class="inp font-mono" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.phones") }}
          </label>
          <div class="flex gap-2 mb-1.5">
            <input
              v-model="phoneDraft"
              class="inp flex-1 font-mono"
              placeholder="+998..."
              @keyup.enter="addPhone"
            />
            <button class="btn btn-soft btn-sm" @click="addPhone">
              <i class="pi pi-plus text-[10px]" />
            </button>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(p, i) in form.phones"
              :key="`${p}-${i}`"
              class="chip chip-ghost"
            >
              <span class="font-mono">{{ p }}</span>
              <button class="ml-1 text-ym-subtle" @click="removePhone(i)">
                <i class="pi pi-times text-[9px]" />
              </button>
            </span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.status") }}
            </label>
            <select v-model.number="form.status" class="inp">
              <option :value="null">—</option>
              <option v-for="s in statuses" :key="s.id" :value="s.id">
                {{ s.name[locale as keyof I18nText] || `#${s.id}` }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.manager") }}
            </label>
            <select v-model="form.manager" class="inp">
              <option :value="null">—</option>
              <option v-for="m in managers" :key="m.id" :value="m.id">
                {{ m.full_name || m.email }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="createError" class="mt-3 text-sm text-ym-danger break-all">
          {{ createError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showCreate = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="saveCreate">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
