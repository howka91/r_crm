<script setup lang="ts">
/**
 * Planning catalog — list and CRUD for plannings scoped to one ЖК.
 *
 * Create/edit happens in a modal (mirrors `developers/index.vue`).
 * Image upload uses multipart (planningsApi.create/update take
 * FormData). A deleted planning cascades `planning=NULL` to every
 * Apartment referencing it (SET_NULL on the backend).
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import ToggleSwitch from "@/components/ToggleSwitch.vue"
import { planningsApi } from "@/api/references"
import { projectsApi } from "@/api/objects"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type { I18nText, Planning, Project } from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const confirmStore = useConfirmStore()
const toastStore = useToastStore()

const projectId = computed(() => Number(props.id))
const project = ref<Project | null>(null)
const items = ref<Planning[]>([])
const loading = ref(false)

const canCreate = computed(() => permissions.check("references.plannings.create"))
const canEdit = computed(() => permissions.check("references.plannings.edit"))
const canDelete = computed(() => permissions.check("references.plannings.delete"))

// --- Modal form state ----------------------------------------------------
// Files live in separate refs (FormData doesn't round-trip through
// reactive well), scalar fields in `form`.

function emptyI18n(): I18nText {
  return { ru: "", uz: "", oz: "" }
}

interface FormShape {
  code: string
  name: I18nText
  rooms_count: number | null
  area: string
  sort: number
  is_active: boolean
}

function emptyForm(): FormShape {
  return {
    code: "",
    name: emptyI18n(),
    rooms_count: null,
    area: "",
    sort: 0,
    is_active: true,
  }
}

const form = reactive<FormShape>(emptyForm())
const image2dFile = ref<File | null>(null)
const image3dFile = ref<File | null>(null)
/** URLs for preview — either the freshly-picked file (blob:…) or the
 *  already-stored image URL when editing an existing planning. */
const image2dPreview = ref<string | null>(null)
const image3dPreview = ref<string | null>(null)

const editing = ref<Planning | null>(null)
const showModal = ref(false)
const saving = ref(false)
const saveError = ref<string | null>(null)

const ALLOWED_MIMES = [
  "image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml",
]
const MAX_FILE_BYTES = 5 * 1024 * 1024

// --- Load ----------------------------------------------------------------

async function load() {
  loading.value = true
  try {
    const [projData, listData] = await Promise.all([
      projectsApi.retrieve(projectId.value),
      planningsApi.list({
        project: projectId.value,
        limit: 500,
        ordering: "sort,id",
      }),
    ])
    project.value = projData
    items.value = listData.results
  } finally {
    loading.value = false
  }
}

// --- Modal open/close ----------------------------------------------------

function openCreate() {
  editing.value = null
  Object.assign(form, emptyForm())
  image2dFile.value = null
  image3dFile.value = null
  image2dPreview.value = null
  image3dPreview.value = null
  saveError.value = null
  showModal.value = true
}

function openEdit(item: Planning) {
  editing.value = item
  Object.assign(form, {
    code: item.code,
    name: { ...item.name },
    rooms_count: item.rooms_count,
    area: item.area ?? "",
    sort: item.sort,
    is_active: item.is_active,
  })
  image2dFile.value = null
  image3dFile.value = null
  image2dPreview.value = item.image_2d
  image3dPreview.value = item.image_3d
  saveError.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  // Drop blob: URLs so the browser can free them. Safe no-op on
  // already-freed URLs.
  if (image2dPreview.value?.startsWith("blob:")) {
    URL.revokeObjectURL(image2dPreview.value)
  }
  if (image3dPreview.value?.startsWith("blob:")) {
    URL.revokeObjectURL(image3dPreview.value)
  }
}

// --- File handling -------------------------------------------------------

function pickImage(slot: "2d" | "3d", e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  if (!file) return
  if (!ALLOWED_MIMES.includes(file.type)) {
    saveError.value = t("references.plannings.errors.bad_mime")
    return
  }
  if (file.size > MAX_FILE_BYTES) {
    saveError.value = t("references.plannings.errors.too_large")
    return
  }
  saveError.value = null
  const url = URL.createObjectURL(file)
  if (slot === "2d") {
    image2dFile.value = file
    if (image2dPreview.value?.startsWith("blob:")) {
      URL.revokeObjectURL(image2dPreview.value)
    }
    image2dPreview.value = url
  } else {
    image3dFile.value = file
    if (image3dPreview.value?.startsWith("blob:")) {
      URL.revokeObjectURL(image3dPreview.value)
    }
    image3dPreview.value = url
  }
}

function clearImage(slot: "2d" | "3d") {
  if (slot === "2d") {
    if (image2dPreview.value?.startsWith("blob:")) {
      URL.revokeObjectURL(image2dPreview.value)
    }
    image2dFile.value = null
    image2dPreview.value = null
  } else {
    if (image3dPreview.value?.startsWith("blob:")) {
      URL.revokeObjectURL(image3dPreview.value)
    }
    image3dFile.value = null
    image3dPreview.value = null
  }
}

// --- Save ----------------------------------------------------------------

function buildFormData(): FormData {
  const fd = new FormData()
  fd.append("project", String(projectId.value))
  fd.append("code", form.code)
  fd.append("name", JSON.stringify(form.name))
  if (form.rooms_count !== null) {
    fd.append("rooms_count", String(form.rooms_count))
  }
  if (form.area) fd.append("area", form.area)
  fd.append("sort", String(form.sort))
  fd.append("is_active", form.is_active ? "true" : "false")
  if (image2dFile.value) fd.append("image_2d", image2dFile.value)
  if (image3dFile.value) fd.append("image_3d", image3dFile.value)
  return fd
}

async function save() {
  saving.value = true
  saveError.value = null
  try {
    const fd = buildFormData()
    if (editing.value) {
      await planningsApi.update(editing.value.id, fd)
      toastStore.success(t("common.saved"))
    } else {
      await planningsApi.create(fd)
      toastStore.success(t("common.created"))
    }
    closeModal()
    await load()
  } catch (e) {
    saveError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  } finally {
    saving.value = false
  }
}

async function remove(item: Planning) {
  const nameLoc = item.name[locale.value as keyof I18nText] || `#${item.id}`
  const ok = await confirmStore.ask({
    title: t("references.plannings.confirm_delete"),
    message: nameLoc,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  await planningsApi.destroy(item.id)
  toastStore.success(t("common.deleted"))
  await load()
}

// --- Helpers -------------------------------------------------------------

function localizedName(item: Planning): string {
  return item.name[locale.value as keyof I18nText] || `#${item.id}`
}

function projectTitle(): string {
  if (!project.value) return ""
  return project.value.title[locale.value as keyof I18nText] || `#${project.value.id}`
}

onMounted(load)
</script>

<template>
  <div>
    <!-- Breadcrumb + header -->
    <div class="flex items-end justify-between mb-5 mt-1 px-1 gap-4">
      <div class="min-w-0">
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle flex items-center gap-2 flex-wrap"
        >
          <button class="hover:text-ym-primary" @click="router.push('/references')">
            {{ t("nav.references") }}
          </button>
          <span>/</span>
          <button
            class="hover:text-ym-primary"
            @click="router.push('/references/plannings')"
          >
            {{ t("references.plannings.title") }}
          </button>
          <span>/</span>
          <span class="truncate">{{ projectTitle() }}</span>
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em] truncate">
          {{ projectTitle() || t("common.loading") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.plannings.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.plannings.new") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="!items.length"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("references.plannings.empty") }}
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("references.plannings.fields.code") }}</th>
            <th>{{ t("references.plannings.fields.name") }}</th>
            <th class="text-right">{{ t("references.plannings.fields.rooms_count") }}</th>
            <th class="text-right">{{ t("references.plannings.fields.area") }}</th>
            <th>{{ t("references.plannings.columns.preview") }}</th>
            <th>{{ t("references.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id">
            <td class="font-mono text-[12.5px]">{{ i.code || "—" }}</td>
            <td class="font-medium">{{ localizedName(i) }}</td>
            <td class="text-right font-mono text-[12.5px]">
              {{ i.rooms_count ?? "—" }}
            </td>
            <td class="text-right font-mono text-[12.5px]">
              {{ i.area ?? "—" }}
            </td>
            <td>
              <div class="flex gap-1.5">
                <img
                  v-if="i.image_2d"
                  :src="i.image_2d"
                  class="w-12 h-12 object-cover rounded-sm border border-ym-line-soft"
                  :alt="t('references.plannings.fields.image_2d')"
                />
                <span
                  v-else
                  class="w-12 h-12 rounded-sm bg-ym-sunken/60 flex items-center justify-center text-[10px] text-ym-subtle font-mono"
                >2D</span>
                <img
                  v-if="i.image_3d"
                  :src="i.image_3d"
                  class="w-12 h-12 object-cover rounded-sm border border-ym-line-soft"
                  :alt="t('references.plannings.fields.image_3d')"
                />
                <span
                  v-else
                  class="w-12 h-12 rounded-sm bg-ym-sunken/60 flex items-center justify-center text-[10px] text-ym-subtle font-mono"
                >3D</span>
              </div>
            </td>
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
      <div class="card w-full max-w-2xl p-6 shadow-ym-modal max-h-[92vh] overflow-auto art-scroll">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("references.plannings.edit") : t("references.plannings.new") }}
        </h2>

        <div class="grid grid-cols-3 gap-3 mb-4">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.plannings.fields.code") }}
            </label>
            <input v-model="form.code" class="inp font-mono" placeholder="3К-А" />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.plannings.fields.rooms_count") }}
            </label>
            <input
              v-model.number="form.rooms_count"
              type="number"
              min="0"
              class="inp font-mono"
            />
          </div>
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.plannings.fields.area") }}
            </label>
            <input v-model="form.area" class="inp font-mono" placeholder="72.50" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("references.plannings.fields.name") }}
          </label>
          <div class="grid grid-cols-3 gap-2">
            <input v-model="form.name.ru" class="inp" placeholder="RU" />
            <input v-model="form.name.uz" class="inp" placeholder="UZ" />
            <input v-model="form.name.oz" class="inp" placeholder="ОЗ" />
          </div>
        </div>

        <!-- Images -->
        <div class="grid grid-cols-2 gap-3 mb-4">
          <div
            v-for="slot in (['2d', '3d'] as const)"
            :key="slot"
            class="border border-dashed border-ym-line rounded-md p-3"
          >
            <div class="flex items-center justify-between mb-2">
              <label class="block text-[12px] font-medium">
                {{
                  slot === "2d"
                    ? t("references.plannings.fields.image_2d")
                    : t("references.plannings.fields.image_3d")
                }}
              </label>
              <button
                v-if="slot === '2d' ? image2dPreview : image3dPreview"
                type="button"
                class="btn btn-ghost btn-xs"
                @click="clearImage(slot)"
              >
                <i class="pi pi-times text-[11px]" />
              </button>
            </div>
            <img
              v-if="slot === '2d' ? image2dPreview : image3dPreview"
              :src="slot === '2d' ? (image2dPreview as string) : (image3dPreview as string)"
              class="w-full h-40 object-contain bg-ym-sunken/40 rounded-sm mb-2"
            />
            <div
              v-else
              class="w-full h-40 flex items-center justify-center bg-ym-sunken/40 rounded-sm text-[12px] text-ym-subtle mb-2"
            >
              {{ t("references.plannings.no_image") }}
            </div>
            <input
              type="file"
              :accept="ALLOWED_MIMES.join(',')"
              class="text-[12px]"
              @change="pickImage(slot, $event)"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[12px] font-medium mb-1.5">
              {{ t("references.plannings.fields.sort") }}
            </label>
            <input
              v-model.number="form.sort"
              type="number"
              min="0"
              class="inp font-mono"
            />
          </div>
          <div class="mt-6">
            <ToggleSwitch
              v-model="form.is_active"
              :active-label="t('common.active')"
              :inactive-label="t('common.inactive')"
            />
          </div>
        </div>

        <div v-if="saveError" class="mt-3 text-sm text-ym-danger break-all">
          {{ saveError }}
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" :disabled="saving" @click="closeModal">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
