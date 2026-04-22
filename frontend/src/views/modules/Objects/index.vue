<script setup lang="ts">
/**
 * Projects list — top-level Objects view.
 *
 * Card grid instead of a table because Project is a primary entity the user
 * navigates into (unlike References which are flat lookups). Each card is a
 * RouterLink to `/objects/projects/:id`.
 *
 * Create/edit modal is a div-overlay like Developers/SalesOffices screens —
 * PrimeVue Dialog migration tracked as tech debt in SESSION_STATE.md.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

import { projectsApi } from "@/api/objects"
import { developersApi } from "@/api/references"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type { Developer, I18nText, Project, ProjectWrite } from "@/types/models"

const { t, locale } = useI18n()
const permissions = usePermissionStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const items = ref<Project[]>([])
const developers = ref<Developer[]>([])
const loading = ref(false)
const editing = ref<Project | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

function emptyForm(): ProjectWrite {
  return {
    developer: 0,
    title: emptyI18n(),
    address: "",
    description: emptyI18n(),
    banks: [],
    sort: 0,
    is_active: true,
  }
}

const form = reactive<ProjectWrite>(emptyForm())

const canCreate = computed(() => permissions.check("objects.projects.create"))
const canEdit = computed(() => permissions.check("objects.projects.edit"))
const canDelete = computed(() => permissions.check("objects.projects.delete"))

async function load() {
  loading.value = true
  try {
    const [projects, devs] = await Promise.all([
      projectsApi.list({ limit: 200 }),
      developersApi.list({ limit: 200 }),
    ])
    items.value = projects.results
    developers.value = devs.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, emptyForm())
  if (developers.value.length) {
    form.developer = developers.value[0]!.id
  }
  saveError.value = null
  showModal.value = true
}

function openEdit(item: Project) {
  editing.value = item
  Object.assign(form, {
    developer: item.developer,
    title: { ...item.title },
    address: item.address,
    description: { ...item.description },
    banks: [...item.banks],
    sort: item.sort,
    is_active: item.is_active,
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  saveError.value = null
  try {
    if (editing.value) {
      await projectsApi.update(editing.value.id, form)
    } else {
      await projectsApi.create(form)
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

async function remove(item: Project) {
  const nameLoc = localizedTitle(item)
  const ok = await confirmStore.ask({
    title: t("objects.projects.confirm_delete"),
    message: nameLoc,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await projectsApi.destroy(item.id)
    toast.success(t("objects.projects.confirm_delete"))
    await load()
  } catch (e) {
    if (e instanceof AxiosError && e.response?.data) {
      toast.error(
        t("errors.unknown"),
        typeof e.response.data === "object"
          ? JSON.stringify(e.response.data)
          : String(e.response.data),
      )
    } else {
      toast.error(t("errors.unknown"))
    }
  }
}

function localizedTitle(item: Project): string {
  return item.title[locale.value as keyof I18nText] || `#${item.id}`
}

function developerName(item: Project): string {
  if (!item.developer_name) return "—"
  return item.developer_name[locale.value as keyof I18nText] || "—"
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle">
          {{ t("nav.objects") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("objects.projects.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("objects.projects.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("objects.projects.new") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="items.length === 0" class="card p-8 text-center text-ym-muted">
      {{ t("objects.projects.empty") }}
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="i in items"
        :key="i.id"
        class="card card-hover p-5 flex flex-col gap-3"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="text-[15px] font-semibold truncate">{{ localizedTitle(i) }}</div>
            <div class="text-[12.5px] text-ym-muted mt-1 truncate">{{ i.address || "—" }}</div>
          </div>
          <span class="chip chip-ghost whitespace-nowrap">
            <i class="pi pi-wrench text-[10px] mr-1" />
            {{ developerName(i) }}
          </span>
        </div>

        <div class="flex items-center gap-2 text-[12px] text-ym-muted">
          <i class="pi pi-building text-[11px]" />
          <span>{{ t("objects.columns.buildings_count") }}: <strong class="text-ym-text">{{ i.buildings_count }}</strong></span>
        </div>

        <div class="mt-auto pt-2 flex items-center justify-between gap-2">
          <RouterLink
            :to="`/objects/projects/${i.id}`"
            class="text-[12px] text-ym-primary font-medium flex items-center gap-1 no-underline"
          >
            <span>{{ t("objects.projects.open") }}</span>
            <i class="pi pi-arrow-right text-[10px]" />
          </RouterLink>
          <div class="flex items-center gap-1">
            <button v-if="canEdit" class="btn btn-ghost btn-xs" @click="openEdit(i)">
              {{ t("common.edit") }}
            </button>
            <button v-if="canDelete" class="btn btn-danger btn-xs" @click="remove(i)">
              {{ t("common.delete") }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create / edit modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="showModal = false"
    >
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[90vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("objects.projects.edit") : t("objects.projects.new") }}
        </h2>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("objects.projects.fields.developer") }}
          </label>
          <select v-model.number="form.developer" class="inp">
            <option v-for="d in developers" :key="d.id" :value="d.id">
              {{ d.name[locale as keyof I18nText] || `#${d.id}` }}
            </option>
          </select>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("objects.projects.fields.title") }}
          </label>
          <div class="grid grid-cols-3 gap-2">
            <input v-model="form.title.ru" class="inp" placeholder="RU" />
            <input v-model="form.title.uz" class="inp" placeholder="UZ" />
            <input v-model="form.title.oz" class="inp" placeholder="ОЗ" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("objects.projects.fields.address") }}
          </label>
          <input v-model="form.address" class="inp" />
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("objects.projects.fields.description") }}
          </label>
          <div class="grid grid-cols-3 gap-2">
            <textarea v-model="form.description.ru" class="inp" rows="2" placeholder="RU" />
            <textarea v-model="form.description.uz" class="inp" rows="2" placeholder="UZ" />
            <textarea v-model="form.description.oz" class="inp" rows="2" placeholder="ОЗ" />
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm mt-4">
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
