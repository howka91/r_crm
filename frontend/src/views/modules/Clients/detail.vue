<script setup lang="ts">
/**
 * Client detail screen — four tabs (Контакты / Реквизиты / Заметки /
 * Договоры stub).
 *
 * Header shows the most important facts (status, manager, entity) so the
 * user never has to switch to an "Overview" tab. Inline edit of the client
 * card is via the "Редактировать" button → full-form modal (same fields as
 * the list-screen create modal plus address/description).
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { staffApi } from "@/api/administration"
import {
  clientContactsApi,
  clientGroupsApi,
  clientRequisitesApi,
  clientStatusesApi,
  clientsApi,
} from "@/api/clients"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type {
  Client,
  ClientContact,
  ClientContactWrite,
  ClientGender,
  ClientGroup,
  ClientStatus,
  ClientWrite,
  I18nText,
  Requisite,
  RequisiteType,
  RequisiteWrite,
  Staff,
} from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const clientId = computed(() => Number(props.id))

const client = ref<Client | null>(null)
const contacts = ref<ClientContact[]>([])
const requisites = ref<Requisite[]>([])
const statuses = ref<ClientStatus[]>([])
const groups = ref<ClientGroup[]>([])
const managers = ref<Staff[]>([])
const loading = ref(false)

const activeTab = ref<"contacts" | "requisites" | "notes" | "contracts">(
  "contacts",
)

// Notes local draft — only saved when user presses Save.
const notesDraft = ref("")
const notesSaving = ref(false)

const canEditClient = computed(() => permissions.check("clients.edit"))
const canDeleteClient = computed(() => permissions.check("clients.delete"))
const canEditContacts = computed(() =>
  permissions.check("clients.contacts.edit"),
)
const canCreateContacts = computed(() =>
  permissions.check("clients.contacts.create"),
)
const canDeleteContacts = computed(() =>
  permissions.check("clients.contacts.delete"),
)
const canEditRequisites = computed(() =>
  permissions.check("clients.requisites.edit"),
)
const canCreateRequisites = computed(() =>
  permissions.check("clients.requisites.create"),
)
const canDeleteRequisites = computed(() =>
  permissions.check("clients.requisites.delete"),
)

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
    const results = await Promise.all([
      clientsApi.retrieve(clientId.value),
      clientContactsApi.list({ client: clientId.value, limit: 200 }),
      clientRequisitesApi.list({ client: clientId.value, limit: 200 }),
      statuses.value.length
        ? Promise.resolve({ results: statuses.value })
        : clientStatusesApi.list({ limit: 200 }),
      groups.value.length
        ? Promise.resolve({ results: groups.value })
        : clientGroupsApi.list({ limit: 200 }),
      managers.value.length
        ? Promise.resolve({ results: managers.value })
        : staffApi.list({ limit: 500 }),
    ])
    client.value = results[0]
    contacts.value = results[1].results
    requisites.value = results[2].results
    if (!statuses.value.length) statuses.value = results[3].results as ClientStatus[]
    if (!groups.value.length) groups.value = results[4].results as ClientGroup[]
    if (!managers.value.length) managers.value = results[5].results as Staff[]

    notesDraft.value = client.value?.description || ""
  } finally {
    loading.value = false
  }
}

onMounted(load)

function localizedStatus(): string {
  if (!client.value?.status_name) return "—"
  return client.value.status_name[locale.value as keyof I18nText] || "—"
}
function statusColor(): string | undefined {
  if (!client.value?.status) return undefined
  return statuses.value.find((s) => s.id === client.value?.status)?.color
}
function groupName(id: number): string {
  const g = groups.value.find((x) => x.id === id)
  if (!g) return `#${id}`
  return g.name[locale.value as keyof I18nText] || `#${g.id}`
}

// --- Edit client ---------------------------------------------------------

const showEditClient = ref(false)
const editClientError = ref<string | null>(null)
const clientForm = reactive<ClientWrite>({
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
})
const clientPhoneDraft = ref("")
const clientEmailDraft = ref("")

function openEditClient() {
  if (!client.value) return
  Object.assign(clientForm, {
    entity: client.value.entity,
    gender: client.value.gender,
    full_name: client.value.full_name,
    phones: [...client.value.phones],
    emails: [...client.value.emails],
    inn: client.value.inn,
    oked: client.value.oked,
    pin: client.value.pin,
    birth_date: client.value.birth_date,
    address: client.value.address,
    description: client.value.description,
    manager: client.value.manager,
    status: client.value.status,
    groups: [...client.value.groups],
    is_active: client.value.is_active,
  })
  clientPhoneDraft.value = ""
  clientEmailDraft.value = ""
  editClientError.value = null
  showEditClient.value = true
}

function addClientPhone() {
  const v = clientPhoneDraft.value.trim()
  if (!v) return
  clientForm.phones = [...clientForm.phones, v]
  clientPhoneDraft.value = ""
}
function removeClientPhone(i: number) {
  clientForm.phones = clientForm.phones.filter((_, idx) => idx !== i)
}
function addClientEmail() {
  const v = clientEmailDraft.value.trim()
  if (!v) return
  clientForm.emails = [...clientForm.emails, v]
  clientEmailDraft.value = ""
}
function removeClientEmail(i: number) {
  clientForm.emails = clientForm.emails.filter((_, idx) => idx !== i)
}
function toggleGroup(id: number) {
  if (clientForm.groups.includes(id)) {
    clientForm.groups = clientForm.groups.filter((x) => x !== id)
  } else {
    clientForm.groups = [...clientForm.groups, id]
  }
}

async function saveClient() {
  editClientError.value = null
  try {
    const payload = {
      ...clientForm,
      gender: clientForm.entity === "jur" ? "" : clientForm.gender,
    }
    await clientsApi.update(clientId.value, payload)
    toast.success(t("clients.edit"))
    showEditClient.value = false
    await load()
  } catch (e) {
    editClientError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function removeClient() {
  if (!client.value) return
  const ok = await confirmStore.ask({
    title: t("clients.confirm_delete"),
    message: client.value.full_name,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await clientsApi.destroy(clientId.value)
    toast.success(t("clients.confirm_delete"))
    router.push("/clients")
  } catch (e) {
    toastApiError(e)
  }
}

// --- Contacts tab --------------------------------------------------------

const showContactModal = ref(false)
const contactError = ref<string | null>(null)
const editingContactId = ref<number | null>(null)

function emptyContact(): ClientContactWrite {
  return {
    client: clientId.value,
    full_name: "",
    role: "",
    is_chief: false,
    phones: [],
    email: "",
    passport: {},
    birth_date: null,
    inn: "",
    pin: "",
    is_active: true,
  }
}
const contactForm = reactive<ClientContactWrite>(emptyContact())
const contactPhoneDraft = ref("")

function openContactCreate() {
  editingContactId.value = null
  Object.assign(contactForm, emptyContact())
  contactPhoneDraft.value = ""
  contactError.value = null
  showContactModal.value = true
}
function openContactEdit(c: ClientContact) {
  editingContactId.value = c.id
  Object.assign(contactForm, {
    client: c.client,
    full_name: c.full_name,
    role: c.role,
    is_chief: c.is_chief,
    phones: [...c.phones],
    email: c.email,
    passport: { ...c.passport },
    birth_date: c.birth_date,
    inn: c.inn,
    pin: c.pin,
    is_active: c.is_active,
  })
  contactPhoneDraft.value = ""
  contactError.value = null
  showContactModal.value = true
}
function addContactPhone() {
  const v = contactPhoneDraft.value.trim()
  if (!v) return
  contactForm.phones = [...contactForm.phones, v]
  contactPhoneDraft.value = ""
}
function removeContactPhone(i: number) {
  contactForm.phones = contactForm.phones.filter((_, idx) => idx !== i)
}

async function saveContact() {
  contactError.value = null
  try {
    if (editingContactId.value) {
      await clientContactsApi.update(editingContactId.value, contactForm)
    } else {
      await clientContactsApi.create(contactForm)
    }
    toast.success(
      editingContactId.value
        ? t("clients.contacts.edit")
        : t("clients.contacts.new"),
    )
    showContactModal.value = false
    await load()
  } catch (e) {
    contactError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function removeContact(c: ClientContact) {
  const ok = await confirmStore.ask({
    title: t("clients.contacts.confirm_delete"),
    message: c.full_name,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await clientContactsApi.destroy(c.id)
    toast.success(t("clients.contacts.confirm_delete"))
    await load()
  } catch (e) {
    toastApiError(e)
  }
}

// --- Requisites tab ------------------------------------------------------

const showRequisiteModal = ref(false)
const requisiteError = ref<string | null>(null)
const editingRequisiteId = ref<number | null>(null)

function emptyRequisite(): RequisiteWrite {
  return {
    client: clientId.value,
    type: "local",
    bank_requisite: {
      account: "",
      bank: "",
      mfo: "",
      currency: "",
    },
    is_active: true,
  }
}
const requisiteForm = reactive<RequisiteWrite>(emptyRequisite())

function openRequisiteCreate() {
  editingRequisiteId.value = null
  Object.assign(requisiteForm, emptyRequisite())
  requisiteError.value = null
  showRequisiteModal.value = true
}
function openRequisiteEdit(r: Requisite) {
  editingRequisiteId.value = r.id
  Object.assign(requisiteForm, {
    client: r.client,
    type: r.type,
    bank_requisite: {
      account: r.bank_requisite.account || "",
      bank: r.bank_requisite.bank || "",
      mfo: r.bank_requisite.mfo || "",
      currency: r.bank_requisite.currency || "",
    },
    is_active: r.is_active,
  })
  requisiteError.value = null
  showRequisiteModal.value = true
}

async function saveRequisite() {
  requisiteError.value = null
  try {
    if (editingRequisiteId.value) {
      await clientRequisitesApi.update(editingRequisiteId.value, requisiteForm)
    } else {
      await clientRequisitesApi.create(requisiteForm)
    }
    toast.success(
      editingRequisiteId.value
        ? t("clients.requisites.edit")
        : t("clients.requisites.new"),
    )
    showRequisiteModal.value = false
    await load()
  } catch (e) {
    requisiteError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  }
}

async function removeRequisite(r: Requisite) {
  const label = `${r.type === "internal" ? t("clients.requisites.type_internal") : t("clients.requisites.type_local")} · ${r.bank_requisite.bank || "—"}`
  const ok = await confirmStore.ask({
    title: t("clients.requisites.confirm_delete"),
    message: label,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await clientRequisitesApi.destroy(r.id)
    toast.success(t("clients.requisites.confirm_delete"))
    await load()
  } catch (e) {
    toastApiError(e)
  }
}

function requisiteKindLabel(t_: RequisiteType): string {
  return t_ === "internal"
    ? t("clients.requisites.type_internal")
    : t("clients.requisites.type_local")
}

// --- Notes tab -----------------------------------------------------------

async function saveNotes() {
  notesSaving.value = true
  try {
    await clientsApi.update(clientId.value, { description: notesDraft.value })
    if (client.value) client.value.description = notesDraft.value
    toast.success(t("clients.notes.title"))
  } catch (e) {
    toastApiError(e)
  } finally {
    notesSaving.value = false
  }
}
</script>

<template>
  <div>
    <div v-if="loading && !client" class="text-ym-muted">
      {{ t("common.loading") }}
    </div>

    <template v-else-if="client">
      <!-- Header -->
      <div class="flex items-end justify-between mb-3 mt-1 px-1">
        <div class="flex-1 min-w-0">
          <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle flex items-center gap-2">
            <button class="hover:text-ym-primary" @click="router.push('/clients')">
              {{ t("clients.title") }}
            </button>
            <span>/</span>
            <span>
              {{ client.entity === "phys" ? t("clients.entity_phys") : t("clients.entity_jur") }}
            </span>
          </div>
          <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em] truncate">
            {{ client.full_name }}
          </h1>
          <div class="text-[13px] mt-2 text-ym-muted flex flex-wrap items-center gap-x-3 gap-y-1">
            <span v-if="client.status_name">
              <span
                class="chip text-white"
                :style="statusColor() ? `background:${statusColor()}` : undefined"
              >
                {{ localizedStatus() }}
              </span>
            </span>
            <span v-if="client.manager_name">
              <i class="pi pi-user text-[10px] mr-1" />
              {{ client.manager_name }}
            </span>
            <span v-if="client.phones.length" class="font-mono">
              <i class="pi pi-phone text-[10px] mr-1" />
              {{ client.phones[0] }}
            </span>
            <span v-if="client.emails.length" class="font-mono">
              <i class="pi pi-envelope text-[10px] mr-1" />
              {{ client.emails[0] }}
            </span>
          </div>
          <div
            v-if="client.groups.length"
            class="mt-2 flex flex-wrap gap-1"
          >
            <span v-for="g in client.groups" :key="g" class="chip chip-ghost">
              {{ groupName(g) }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <button v-if="canEditClient" class="btn btn-soft btn-sm" @click="openEditClient">
            {{ t("common.edit") }}
          </button>
          <button v-if="canDeleteClient" class="btn btn-danger btn-sm" @click="removeClient">
            {{ t("common.delete") }}
          </button>
        </div>
      </div>

      <!-- Tab strip -->
      <div class="flex gap-1 mb-5 border-b border-ym-line-soft">
        <button
          v-for="tab in ['contacts', 'requisites', 'notes', 'contracts'] as const"
          :key="tab"
          class="px-3 py-2 text-[13px] border-b-2 transition"
          :class="
            activeTab === tab
              ? 'border-ym-primary text-ym-primary font-medium'
              : 'border-transparent text-ym-muted hover:text-ym-text'
          "
          @click="activeTab = tab"
        >
          {{ t(`clients.tabs.${tab}`) }}
          <span v-if="tab === 'contacts'" class="ml-1 font-mono text-[11.5px]">
            ({{ contacts.length }})
          </span>
          <span v-else-if="tab === 'requisites'" class="ml-1 font-mono text-[11.5px]">
            ({{ requisites.length }})
          </span>
        </button>
      </div>

      <!-- Contacts tab -->
      <section v-if="activeTab === 'contacts'">
        <div class="flex items-center justify-between mb-3 px-1">
          <h2 class="text-[15px] font-semibold">{{ t("clients.contacts.title") }}</h2>
          <button
            v-if="canCreateContacts"
            class="btn btn-soft btn-sm"
            @click="openContactCreate"
          >
            <i class="pi pi-plus text-[10px]" />
            {{ t("clients.contacts.new") }}
          </button>
        </div>
        <div
          v-if="!contacts.length"
          class="card p-6 text-center text-ym-muted text-[13px]"
        >
          {{ t("clients.contacts.empty") }}
        </div>
        <div v-else class="card overflow-hidden">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t("clients.contacts.fields.full_name") }}</th>
                <th>{{ t("clients.contacts.fields.role") }}</th>
                <th>{{ t("clients.contacts.fields.phones") }}</th>
                <th>{{ t("clients.contacts.fields.email") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in contacts" :key="c.id">
                <td class="font-medium">
                  <span v-if="c.is_chief" class="chip chip-primary mr-2">
                    {{ t("clients.contacts.fields.is_chief") }}
                  </span>
                  {{ c.full_name }}
                </td>
                <td class="text-ym-muted">{{ c.role || "—" }}</td>
                <td class="font-mono text-[12.5px]">{{ c.phones[0] || "—" }}</td>
                <td class="font-mono text-[12.5px]">{{ c.email || "—" }}</td>
                <td class="text-right whitespace-nowrap">
                  <button
                    v-if="canEditContacts"
                    class="btn btn-ghost btn-xs mr-1"
                    @click="openContactEdit(c)"
                  >
                    {{ t("common.edit") }}
                  </button>
                  <button
                    v-if="canDeleteContacts"
                    class="btn btn-danger btn-xs"
                    @click="removeContact(c)"
                  >
                    {{ t("common.delete") }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Requisites tab -->
      <section v-else-if="activeTab === 'requisites'">
        <div class="flex items-center justify-between mb-3 px-1">
          <h2 class="text-[15px] font-semibold">{{ t("clients.requisites.title") }}</h2>
          <button
            v-if="canCreateRequisites"
            class="btn btn-soft btn-sm"
            @click="openRequisiteCreate"
          >
            <i class="pi pi-plus text-[10px]" />
            {{ t("clients.requisites.new") }}
          </button>
        </div>
        <div
          v-if="!requisites.length"
          class="card p-6 text-center text-ym-muted text-[13px]"
        >
          {{ t("clients.requisites.empty") }}
        </div>
        <div v-else class="card overflow-hidden">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t("clients.requisites.fields.type") }}</th>
                <th>{{ t("clients.requisites.fields.bank") }}</th>
                <th>{{ t("clients.requisites.fields.account") }}</th>
                <th>{{ t("clients.requisites.fields.mfo") }}</th>
                <th>{{ t("clients.requisites.fields.currency") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in requisites" :key="r.id">
                <td>
                  <span class="chip chip-ghost">{{ requisiteKindLabel(r.type) }}</span>
                </td>
                <td>{{ r.bank_requisite.bank || "—" }}</td>
                <td class="font-mono text-[12.5px]">{{ r.bank_requisite.account || "—" }}</td>
                <td class="font-mono text-[12.5px]">{{ r.bank_requisite.mfo || "—" }}</td>
                <td class="font-mono">{{ r.bank_requisite.currency || "—" }}</td>
                <td class="text-right whitespace-nowrap">
                  <button
                    v-if="canEditRequisites"
                    class="btn btn-ghost btn-xs mr-1"
                    @click="openRequisiteEdit(r)"
                  >
                    {{ t("common.edit") }}
                  </button>
                  <button
                    v-if="canDeleteRequisites"
                    class="btn btn-danger btn-xs"
                    @click="removeRequisite(r)"
                  >
                    {{ t("common.delete") }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Notes tab -->
      <section v-else-if="activeTab === 'notes'">
        <div class="card p-4">
          <textarea
            v-model="notesDraft"
            class="inp w-full min-h-[200px]"
            :placeholder="t('clients.notes.placeholder')"
            :disabled="!canEditClient"
          />
          <div class="mt-3 flex justify-end">
            <button
              v-if="canEditClient"
              class="btn btn-primary btn-sm"
              :disabled="notesSaving"
              @click="saveNotes"
            >
              {{ t("common.save") }}
            </button>
          </div>
        </div>
      </section>

      <!-- Contracts stub -->
      <section v-else-if="activeTab === 'contracts'">
        <div class="card p-8 text-center text-ym-muted text-[13px]">
          <i class="pi pi-info-circle text-[14px] mr-1" />
          {{ t("clients.contracts_stub") }}
        </div>
      </section>
    </template>

    <!-- Client edit modal -->
    <div
      v-if="showEditClient"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">{{ t("clients.edit") }}</h2>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.full_name") }}
          </label>
          <input v-model="clientForm.full_name" class="inp" />
        </div>

        <div class="grid grid-cols-2 gap-3 mb-4">
          <div v-if="clientForm.entity === 'phys'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.pin") }}
            </label>
            <input v-model="clientForm.pin" class="inp font-mono" />
          </div>
          <div v-if="clientForm.entity === 'jur'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.inn") }}
            </label>
            <input v-model="clientForm.inn" class="inp font-mono" />
          </div>
          <div v-if="clientForm.entity === 'jur'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.oked") }}
            </label>
            <input v-model="clientForm.oked" class="inp font-mono" />
          </div>
          <div v-if="clientForm.entity === 'phys'">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.fields.birth_date") }}
            </label>
            <input v-model="clientForm.birth_date" type="date" class="inp" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.address") }}
          </label>
          <input v-model="clientForm.address" class="inp" />
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.phones") }}
          </label>
          <div class="flex gap-2 mb-1.5">
            <input
              v-model="clientPhoneDraft"
              class="inp flex-1 font-mono"
              placeholder="+998..."
              @keyup.enter="addClientPhone"
            />
            <button class="btn btn-soft btn-sm" @click="addClientPhone">
              <i class="pi pi-plus text-[10px]" />
            </button>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(p, i) in clientForm.phones"
              :key="`${p}-${i}`"
              class="chip chip-ghost"
            >
              <span class="font-mono">{{ p }}</span>
              <button class="ml-1 text-ym-subtle" @click="removeClientPhone(i)">
                <i class="pi pi-times text-[9px]" />
              </button>
            </span>
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.emails") }}
          </label>
          <div class="flex gap-2 mb-1.5">
            <input
              v-model="clientEmailDraft"
              class="inp flex-1 font-mono"
              placeholder="email@example.com"
              @keyup.enter="addClientEmail"
            />
            <button class="btn btn-soft btn-sm" @click="addClientEmail">
              <i class="pi pi-plus text-[10px]" />
            </button>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(e, i) in clientForm.emails"
              :key="`${e}-${i}`"
              class="chip chip-ghost"
            >
              <span class="font-mono">{{ e }}</span>
              <button class="ml-1 text-ym-subtle" @click="removeClientEmail(i)">
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
            <select v-model.number="clientForm.status" class="inp">
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
            <select v-model="clientForm.manager" class="inp">
              <option :value="null">—</option>
              <option v-for="m in managers" :key="m.id" :value="m.id">
                {{ m.full_name || m.email }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="groups.length" class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.fields.groups") }}
          </label>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="g in groups"
              :key="g.id"
              class="chip"
              :class="clientForm.groups.includes(g.id) ? 'chip-primary' : 'chip-ghost'"
              @click="toggleGroup(g.id)"
            >
              {{ g.name[locale as keyof I18nText] || `#${g.id}` }}
            </button>
          </div>
        </div>

        <div v-if="editClientError" class="mt-3 text-sm text-ym-danger break-all">
          {{ editClientError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showEditClient = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="saveClient">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Contact modal -->
    <div
      v-if="showContactModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{ editingContactId ? t("clients.contacts.edit") : t("clients.contacts.new") }}
        </h2>

        <div class="grid grid-cols-2 gap-3 mb-4">
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.full_name") }}
            </label>
            <input v-model="contactForm.full_name" class="inp" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.role") }}
            </label>
            <input v-model="contactForm.role" class="inp" />
          </div>
          <div>
            <label class="flex items-center gap-2 text-sm mt-7">
              <input v-model="contactForm.is_chief" type="checkbox" />
              <span>{{ t("clients.contacts.fields.is_chief") }}</span>
            </label>
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.email") }}
            </label>
            <input v-model="contactForm.email" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.birth_date") }}
            </label>
            <input v-model="contactForm.birth_date" type="date" class="inp" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.pin") }}
            </label>
            <input v-model="contactForm.pin" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.contacts.fields.inn") }}
            </label>
            <input v-model="contactForm.inn" class="inp font-mono" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.contacts.fields.phones") }}
          </label>
          <div class="flex gap-2 mb-1.5">
            <input
              v-model="contactPhoneDraft"
              class="inp flex-1 font-mono"
              placeholder="+998..."
              @keyup.enter="addContactPhone"
            />
            <button class="btn btn-soft btn-sm" @click="addContactPhone">
              <i class="pi pi-plus text-[10px]" />
            </button>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(p, i) in contactForm.phones"
              :key="`${p}-${i}`"
              class="chip chip-ghost"
            >
              <span class="font-mono">{{ p }}</span>
              <button class="ml-1 text-ym-subtle" @click="removeContactPhone(i)">
                <i class="pi pi-times text-[9px]" />
              </button>
            </span>
          </div>
        </div>

        <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mt-5 mb-3">
          {{ t("clients.contacts.fields.passport_series") }} /
          {{ t("clients.contacts.fields.passport_number") }}
        </div>
        <div class="grid grid-cols-2 gap-3 mb-4">
          <input
            v-model="contactForm.passport.series"
            class="inp font-mono"
            :placeholder="t('clients.contacts.fields.passport_series')"
          />
          <input
            v-model="contactForm.passport.number"
            class="inp font-mono"
            :placeholder="t('clients.contacts.fields.passport_number')"
          />
          <input
            v-model="contactForm.passport.issued_date"
            type="date"
            class="inp"
            :placeholder="t('clients.contacts.fields.passport_issued_date')"
          />
          <input
            v-model="contactForm.passport.issued_by"
            class="inp"
            :placeholder="t('clients.contacts.fields.passport_issued_by')"
          />
          <div class="col-span-2">
            <input
              v-model="contactForm.passport.registration_address"
              class="inp"
              :placeholder="t('clients.contacts.fields.passport_registration_address')"
            />
          </div>
        </div>

        <div v-if="contactError" class="mt-3 text-sm text-ym-danger break-all">
          {{ contactError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showContactModal = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="saveContact">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Requisite modal -->
    <div
      v-if="showRequisiteModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div class="card w-full max-w-xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{
            editingRequisiteId
              ? t("clients.requisites.edit")
              : t("clients.requisites.new")
          }}
        </h2>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("clients.requisites.fields.type") }}
          </label>
          <div class="flex gap-2">
            <button
              class="chip"
              :class="requisiteForm.type === 'local' ? 'chip-primary' : 'chip-ghost'"
              @click="requisiteForm.type = 'local'"
            >
              {{ t("clients.requisites.type_local") }}
            </button>
            <button
              class="chip"
              :class="requisiteForm.type === 'internal' ? 'chip-primary' : 'chip-ghost'"
              @click="requisiteForm.type = 'internal'"
            >
              {{ t("clients.requisites.type_internal") }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.requisites.fields.bank") }}
            </label>
            <input v-model="requisiteForm.bank_requisite.bank" class="inp" />
          </div>
          <div class="col-span-2">
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.requisites.fields.account") }}
            </label>
            <input v-model="requisiteForm.bank_requisite.account" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.requisites.fields.mfo") }}
            </label>
            <input v-model="requisiteForm.bank_requisite.mfo" class="inp font-mono" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("clients.requisites.fields.currency") }}
            </label>
            <input
              v-model="requisiteForm.bank_requisite.currency"
              class="inp font-mono"
              placeholder="UZS"
            />
          </div>
        </div>

        <div v-if="requisiteError" class="mt-3 text-sm text-ym-danger break-all">
          {{ requisiteError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showRequisiteModal = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="saveRequisite">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
