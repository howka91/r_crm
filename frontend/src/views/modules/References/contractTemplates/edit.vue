<script setup lang="ts">
/**
 * ContractTemplate editor — create + edit share this screen.
 *
 * The body is a Tiptap rich-text editor; placeholders come from a
 * pre-defined catalog of buttons (see `utils/placeholderCatalog.ts`),
 * which mirrors the 39 legacy `contracttemplatefield` rows translated
 * to our new context paths. Admins don't hand-write paths; they pick
 * from labelled buttons and we add the entry to the template's
 * `placeholders` list automatically.
 *
 * A "custom" section stays available for edge cases (extra fields,
 * JSON-keyed values) but is collapsed by default.
 */
import { AxiosError } from "axios"
import { computed, onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import RichTextEditor from "@/components/RichTextEditor.vue"
import ToggleSwitch from "@/components/ToggleSwitch.vue"
import { contractTemplatesApi } from "@/api/contracts"
import { projectsApi } from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type {
  ContractTemplateSource,
  ContractTemplateWrite,
  DocxValidationResult,
  Project,
  TemplatePlaceholder,
} from "@/types/models"
import {
  CATALOG_CATEGORIES,
  CATEGORY_LABELS,
  findCatalogEntry,
  groupCatalog,
  type CatalogEntry,
  type PlaceholderCategory,
} from "@/utils/placeholderCatalog"

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()
const toastStore = useToastStore()

const editorRef = ref<InstanceType<typeof RichTextEditor> | null>(null)

const idParam = computed<number | null>(() => {
  const raw = route.params.id
  if (!raw) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const projects = ref<Project[]>([])
const saving = ref(false)
const loading = ref(false)
const saveError = ref<string | null>(null)
const showCustom = ref(false)

function emptyForm(): ContractTemplateWrite {
  return {
    title: "",
    source: "html",
    body: "",
    placeholders: [],
    project: null,
    author: null,
    is_active: true,
  }
}

const form = reactive<ContractTemplateWrite>(emptyForm())

// --- DOCX upload state ---------------------------------------------------
// A freshly-picked .docx that hasn't been saved yet. `docxFile` is null
// on edit-of-existing-docx-template until the author picks a new file.
// `currentDocxUrl` is the server-side URL of the previously uploaded
// file — shown as a download link so the author knows what's on file.
const docxFile = ref<File | null>(null)
const currentDocxUrl = ref<string | null>(null)
const docxValidation = ref<DocxValidationResult | null>(null)
const validating = ref(false)
const docxError = ref<string | null>(null)

const DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

const isGlobal = computed(() => form.project === null)

const canManageGlobal = computed(() =>
  permissions.check("references.templates.manage_global"),
)
const scopeForbidden = computed(() => isGlobal.value && !canManageGlobal.value)

async function loadProjects() {
  const resp = await projectsApi.list({ limit: 200 })
  projects.value = resp.results
}

async function loadTemplate() {
  if (idParam.value === null) return
  loading.value = true
  try {
    const data = await contractTemplatesApi.retrieve(idParam.value)
    Object.assign(form, {
      title: data.title,
      source: data.source,
      body: data.body,
      placeholders: data.placeholders.map((p) => ({ ...p })),
      project: data.project,
      author: data.author,
      is_active: data.is_active,
    })
    currentDocxUrl.value = data.file
    docxFile.value = null
    docxValidation.value = null
  } finally {
    loading.value = false
  }
}

function projectLabel(p: Project): string {
  return p.title[locale.value as "ru" | "uz" | "oz"] || `#${p.id}`
}

// --- Catalog helpers -----------------------------------------------------

const grouped = groupCatalog()

function catalogLabel(entry: CatalogEntry): string {
  return entry.labels[locale.value as "ru" | "uz" | "oz"] || entry.labels.ru
}

function categoryLabel(cat: PlaceholderCategory): string {
  return (
    CATEGORY_LABELS[cat][locale.value as "ru" | "uz" | "oz"] ||
    CATEGORY_LABELS[cat].ru
  )
}

function isRegistered(key: string): boolean {
  return form.placeholders.some((p) => p.key === key)
}

/**
 * Click a catalog button → insert {{key}} at the Tiptap caret AND ensure
 * the entry is registered in `form.placeholders`. Re-clicking a registered
 * entry just inserts again (useful for repeating the same value).
 */
function pickFromCatalog(entry: CatalogEntry) {
  if (!isRegistered(entry.key)) {
    form.placeholders.push({
      key: entry.key,
      path: entry.path,
      label: catalogLabel(entry),
    })
  }
  editorRef.value?.insertPlaceholder(entry.key)
}

function insertBuiltinQr() {
  // __qr__ doesn't need to be in the placeholders list — it's resolved
  // by the docgen service itself. Just insert an <img> tag at the caret.
  const editor = editorRef.value
  if (!editor) return
  editor.insertPlaceholder("__qr__")
}

// Hand off to the backend upload endpoint. The RichTextEditor expects a
// function that takes a File and resolves to the URL to embed.
async function uploadImage(file: File): Promise<string> {
  const resp = await contractTemplatesApi.uploadImage(file)
  return resp.url
}

function removePlaceholder(key: string) {
  const idx = form.placeholders.findIndex((p) => p.key === key)
  if (idx >= 0) form.placeholders.splice(idx, 1)
}

// --- Custom (advanced) placeholders -------------------------------------

function addCustomPlaceholder() {
  form.placeholders.push({ key: "", path: "", label: "" })
}

/** Catalog-sourced entries (key matches a catalog entry). */
const customPlaceholders = computed(() =>
  form.placeholders
    .map((p, idx) => ({ entry: p, idx }))
    .filter(({ entry }) => findCatalogEntry(entry.key) === undefined),
)

// --- Validation ----------------------------------------------------------

const duplicateKey = computed<string | null>(() => {
  const seen = new Set<string>()
  for (const p of form.placeholders) {
    const key = (p.key || "").trim()
    if (!key) continue
    if (seen.has(key)) return key
    seen.add(key)
  }
  return null
})

// --- Source switch -------------------------------------------------------

function setSource(next: ContractTemplateSource) {
  if (form.source === next) return
  form.source = next
  // Clear the other flow's state so switching back and forth doesn't
  // smuggle stale data into the save payload.
  if (next === "docx") {
    // Keep placeholders — they come from the DOCX validation and
    // double as a UI hint; body stays empty.
    form.body = ""
  } else {
    docxFile.value = null
    docxValidation.value = null
    docxError.value = null
  }
}

// --- DOCX upload + validate ---------------------------------------------

async function onDocxPicked(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  if (!file) return
  if (file.type !== DOCX_MIME && !file.name.toLowerCase().endsWith(".docx")) {
    docxError.value = t("references.contract_templates.errors.bad_docx")
    return
  }
  docxError.value = null
  docxFile.value = file
  docxValidation.value = null
  validating.value = true
  try {
    const result = await contractTemplatesApi.validateDocx(file)
    docxValidation.value = result
    // Populate `placeholders` with the known tags so the template row
    // carries a machine-readable "what's inside" list — handy for the
    // catalog picker in the contract wizard.
    form.placeholders = result.known.map((tag) => ({
      key: tag,
      path: tag,
      label: tag,
    }))
  } catch (e2) {
    docxError.value =
      e2 instanceof AxiosError && e2.response?.data
        ? (e2.response.data as { detail?: string }).detail
            || JSON.stringify(e2.response.data)
        : t("errors.unknown")
    docxFile.value = null
  } finally {
    validating.value = false
  }
}

function copyTagToClipboard(tag: string) {
  const text = `{{ ${tag} }}`
  if (navigator.clipboard?.writeText) {
    void navigator.clipboard.writeText(text)
    toastStore.success(
      t("references.contract_templates.tag_copied", { tag }),
    )
  }
}

async function save() {
  saveError.value = null
  if (form.source === "html" && duplicateKey.value) {
    saveError.value = t("references.contract_templates.duplicate_key")
    return
  }
  if (scopeForbidden.value) {
    saveError.value = t("references.contract_templates.global_forbidden")
    return
  }
  // For docx templates a file is required on create (no previous file
  // to fall back to); on edit the author may keep the existing one.
  if (form.source === "docx") {
    if (idParam.value === null && !docxFile.value) {
      saveError.value = t("references.contract_templates.errors.docx_required")
      return
    }
    if (docxValidation.value && docxValidation.value.unknown.length > 0) {
      saveError.value = t(
        "references.contract_templates.errors.docx_unknown_tags",
      )
      return
    }
  }

  saving.value = true
  try {
    const cleaned: TemplatePlaceholder[] = form.placeholders
      .map((p) => ({
        key: (p.key || "").trim(),
        path: (p.path || "").trim(),
        label: (p.label || "").trim() || undefined,
      }))
      .filter((p) => p.key && p.path)

    if (form.source === "docx") {
      // Multipart — docx file attached alongside scalar fields. When
      // editing an existing template without picking a new file, skip
      // the `file` key so the server keeps the previous upload.
      const fd = new FormData()
      fd.append("title", form.title)
      fd.append("source", form.source)
      fd.append("body", "")
      fd.append("placeholders", JSON.stringify(cleaned))
      if (form.project !== null) fd.append("project", String(form.project))
      fd.append("is_active", form.is_active ? "true" : "false")
      if (docxFile.value) fd.append("file", docxFile.value)
      if (idParam.value === null) {
        await contractTemplatesApi.createMultipart(fd)
      } else {
        await contractTemplatesApi.updateMultipart(idParam.value, fd)
      }
    } else {
      const payload: ContractTemplateWrite = { ...form, placeholders: cleaned }
      if (idParam.value === null) {
        await contractTemplatesApi.create(payload)
      } else {
        await contractTemplatesApi.update(idParam.value, payload)
      }
    }
    toastStore.success(t("references.contract_templates.saved"))
    // Back to the catalog so the manager sees the freshly-saved row
    // in the list right away instead of staying on the edit page.
    router.push({ name: "references-contract-templates" })
  } catch (e) {
    saveError.value =
      e instanceof AxiosError && e.response?.data
        ? JSON.stringify(e.response.data)
        : t("errors.unknown")
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push({ name: "references-contract-templates" })
}

onMounted(async () => {
  await loadProjects()
  await loadTemplate()
})
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5 px-1">
      <button class="btn btn-ghost btn-sm" @click="cancel">
        <i class="pi pi-arrow-left text-[11px]" />
        {{ t("common.back") }}
      </button>
      <h1 class="text-[22px] font-semibold">
        {{
          idParam === null
            ? t("references.contract_templates.new")
            : t("references.contract_templates.edit")
        }}
      </h1>
      <div class="ml-auto">
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <i class="pi pi-save text-[11px]" />
          {{ t("common.save") }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else class="grid grid-cols-12 gap-5">
      <!-- Left: body editor -->
      <div class="col-span-12 lg:col-span-8 flex flex-col gap-4">
        <div class="card p-4">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("references.contract_templates.fields.title") }}
          </label>
          <input v-model="form.title" class="inp" />

          <!-- Source switch — html (Tiptap) vs docx (Word upload).
               Freely switchable, including on existing templates: the
               other flow's payload stays untouched on the server until
               the author actually saves, so toggling back and forth
               costs nothing. Switching a saved template from html to
               docx (or vice versa) replaces the content on save. -->
          <div class="mt-4">
            <div
              class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-2"
            >
              {{ t("references.contract_templates.source_label") }}
            </div>
            <div class="flex gap-2 flex-wrap">
              <button
                type="button"
                class="flex-1 min-w-[180px] px-4 py-3 rounded-md border text-left transition-colors"
                :class="
                  form.source === 'html'
                    ? 'border-ym-primary bg-ym-primary-soft text-ym-primary-h'
                    : 'border-ym-line-soft hover:border-ym-primary'
                "
                @click="setSource('html')"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-pencil text-[12px]" />
                  <span class="text-[13px] font-semibold">
                    {{ t("references.contract_templates.source_html") }}
                  </span>
                </div>
                <div class="text-[11px] text-ym-muted mt-0.5">
                  {{ t("references.contract_templates.source_html_hint") }}
                </div>
              </button>
              <button
                type="button"
                class="flex-1 min-w-[180px] px-4 py-3 rounded-md border text-left transition-colors"
                :class="
                  form.source === 'docx'
                    ? 'border-ym-primary bg-ym-primary-soft text-ym-primary-h'
                    : 'border-ym-line-soft hover:border-ym-primary'
                "
                @click="setSource('docx')"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-file-word text-[12px]" />
                  <span class="text-[13px] font-semibold">
                    {{ t("references.contract_templates.source_docx") }}
                  </span>
                </div>
                <div class="text-[11px] text-ym-muted mt-0.5">
                  {{ t("references.contract_templates.source_docx_hint") }}
                </div>
              </button>
            </div>
          </div>

          <!-- HTML authoring (Tiptap) -->
          <template v-if="form.source === 'html'">
            <div class="flex items-center justify-between mt-4 mb-1.5">
              <label class="block text-[12px] font-medium">
                {{ t("references.contract_templates.fields.body") }}
              </label>
              <button
                type="button"
                class="btn btn-soft btn-xs"
                :title="t('references.contract_templates.insert_qr')"
                @click="insertBuiltinQr"
              >
                <i class="pi pi-qrcode text-[10px]" />
                QR
              </button>
            </div>
            <RichTextEditor
              ref="editorRef"
              v-model="form.body"
              :placeholders="form.placeholders"
              :image-uploader="uploadImage"
            />
            <div class="text-[11px] text-ym-muted mt-1.5 leading-relaxed">
              {{ t("references.contract_templates.body_hint_catalog") }}
            </div>
          </template>

          <!-- DOCX authoring (Word file upload) -->
          <template v-else>
            <div class="mt-4 mb-1.5">
              <label class="block text-[12px] font-medium">
                {{ t("references.contract_templates.fields.docx_file") }}
              </label>
            </div>
            <div
              class="border-2 border-dashed border-ym-line rounded-md p-4"
            >
              <div v-if="currentDocxUrl && !docxFile" class="mb-3">
                <a
                  :href="currentDocxUrl"
                  target="_blank"
                  class="text-[13px] text-ym-primary hover:underline inline-flex items-center gap-1.5"
                >
                  <i class="pi pi-download text-[11px]" />
                  {{ t("references.contract_templates.current_docx") }}
                </a>
              </div>
              <div v-if="docxFile" class="mb-3 text-[13px]">
                <i class="pi pi-file-word text-[12px] text-ym-primary mr-1.5" />
                <span class="font-medium">{{ docxFile.name }}</span>
                <span class="text-ym-muted ml-2">
                  ({{ Math.round(docxFile.size / 1024) }} KB)
                </span>
              </div>
              <input
                type="file"
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                class="text-[12px]"
                :disabled="validating"
                @change="onDocxPicked"
              />
              <div
                v-if="validating"
                class="mt-2 text-[12px] text-ym-muted flex items-center gap-1.5"
              >
                <i class="pi pi-spinner pi-spin text-[11px]" />
                {{ t("references.contract_templates.validating") }}
              </div>
              <div v-if="docxError" class="mt-2 text-[12px] text-ym-danger">
                {{ docxError }}
              </div>
            </div>

            <!-- Validation result — known / unknown tags. -->
            <div
              v-if="docxValidation"
              class="mt-3 border border-ym-line-soft rounded-md p-3"
            >
              <div class="flex items-center gap-2 mb-2">
                <i
                  :class="
                    docxValidation.is_valid
                      ? 'pi pi-check-circle text-ym-success'
                      : 'pi pi-exclamation-triangle text-ym-warning'
                  "
                  class="text-[13px]"
                />
                <span class="text-[13px] font-medium">
                  {{
                    docxValidation.is_valid
                      ? t("references.contract_templates.validation_ok", {
                          n: docxValidation.known.length,
                        })
                      : t("references.contract_templates.validation_warn", {
                          n: docxValidation.unknown.length,
                        })
                  }}
                </span>
              </div>
              <div
                v-if="docxValidation.known.length"
                class="flex flex-wrap gap-1.5 mb-2"
              >
                <span
                  v-for="tag in docxValidation.known"
                  :key="tag"
                  class="chip chip-success mono text-[10.5px]"
                  v-text="`{{ ${tag} }}`"
                />
              </div>
              <div
                v-if="docxValidation.unknown.length"
                class="flex flex-wrap gap-1.5"
              >
                <span
                  v-for="tag in docxValidation.unknown"
                  :key="tag"
                  class="chip chip-danger mono text-[10.5px]"
                  v-text="`{{ ${tag} }}`"
                />
              </div>
              <div
                v-if="docxValidation.unknown.length"
                class="mt-2 text-[11px] text-ym-muted leading-snug"
              >
                {{ t("references.contract_templates.validation_unknown_hint") }}
              </div>
            </div>

            <div class="text-[11px] text-ym-muted mt-2 leading-relaxed">
              {{ t("references.contract_templates.docx_hint") }}
            </div>
          </template>
        </div>

        <!-- Used-placeholders summary (html-only — docx lists come from
             validation response above). -->
        <div v-if="form.source === 'html'" class="card p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-[12px] font-semibold">
              {{ t("references.contract_templates.used_placeholders") }}
              <span class="text-ym-muted font-normal ml-1">
                · {{ form.placeholders.length }}
              </span>
            </div>
            <button
              type="button"
              class="btn btn-ghost btn-xs"
              @click="showCustom = !showCustom"
            >
              <i
                :class="
                  showCustom ? 'pi pi-chevron-up' : 'pi pi-chevron-down'
                "
                class="text-[10px]"
              />
              {{ t("references.contract_templates.custom_toggle") }}
            </button>
          </div>

          <div
            v-if="form.placeholders.length === 0"
            class="text-[12px] text-ym-muted py-1"
          >
            {{ t("references.contract_templates.no_placeholders") }}
          </div>

          <div v-else class="flex flex-wrap gap-1.5">
            <span
              v-for="p in form.placeholders"
              :key="p.key"
              class="chip chip-primary gap-1.5"
              :title="p.path"
            >
              <span class="mono" v-text="`{{${p.key}}}`" />
              <span v-if="p.label" class="font-normal">· {{ p.label }}</span>
              <button
                type="button"
                class="ml-1 opacity-70 hover:opacity-100"
                :title="t('common.delete')"
                @click="removePlaceholder(p.key)"
              >
                <i class="pi pi-times text-[9px]" />
              </button>
            </span>
          </div>

          <!-- Custom (advanced) section -->
          <div v-if="showCustom" class="mt-4 pt-3 border-t border-ym-line-soft">
            <div class="flex items-center justify-between mb-2">
              <div class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle">
                {{ t("references.contract_templates.custom_section") }}
              </div>
              <button
                type="button"
                class="btn btn-ghost btn-xs"
                @click="addCustomPlaceholder"
              >
                <i class="pi pi-plus text-[10px]" />
                {{ t("references.contract_templates.add_placeholder") }}
              </button>
            </div>

            <div
              v-if="customPlaceholders.length === 0"
              class="text-[11px] text-ym-muted"
            >
              {{ t("references.contract_templates.custom_empty") }}
            </div>

            <div v-else class="flex flex-col gap-2">
              <div
                v-for="cp in customPlaceholders"
                :key="cp.idx"
                class="border border-ym-line-soft rounded-md p-2 bg-ym-sunken/40"
              >
                <div class="grid grid-cols-6 gap-1.5">
                  <input
                    v-model="cp.entry.key"
                    :placeholder="
                      t(
                        'references.contract_templates.fields.placeholder_key',
                      )
                    "
                    class="inp inp-sm col-span-2 font-mono"
                  />
                  <input
                    v-model="cp.entry.path"
                    :placeholder="
                      t(
                        'references.contract_templates.fields.placeholder_path',
                      )
                    "
                    class="inp inp-sm col-span-3 font-mono"
                  />
                  <button
                    type="button"
                    class="btn btn-xs btn-ghost col-span-1"
                    :title="t('common.delete')"
                    @click="form.placeholders.splice(cp.idx, 1)"
                  >
                    <i class="pi pi-times text-[11px]" />
                  </button>
                </div>
                <input
                  v-model="cp.entry.label"
                  :placeholder="
                    t(
                      'references.contract_templates.fields.placeholder_label',
                    )
                  "
                  class="inp inp-sm mt-1.5"
                />
              </div>
            </div>

            <div class="text-[11px] text-ym-muted mt-2 leading-snug">
              {{ t("references.contract_templates.placeholders_hint") }}
            </div>
          </div>

          <div
            v-if="duplicateKey"
            class="mt-2 text-[12px] text-ym-danger"
          >
            {{ t("references.contract_templates.duplicate_key") }}:
            <span class="mono">{{ duplicateKey }}</span>
          </div>
        </div>
      </div>

      <!--
        Right column: meta + catalog.

        Sticky inside the `<main>` scroll container so as the admin scrolls
        through a long body editor, the catalog stays visible. The inner
        catalog gets `flex-1 min-h-0` which lets it shrink and scroll
        internally — keeps both panels within one viewport.
      -->
      <div
        class="col-span-12 lg:col-span-4 lg:sticky lg:top-2 lg:self-start lg:max-h-[calc(100vh-6rem)] flex flex-col gap-4 min-h-0"
      >
        <div class="card p-4 flex-shrink-0">
          <label class="block text-[12px] font-medium mb-1.5">
            {{ t("references.contract_templates.fields.project") }}
          </label>
          <select
            v-model="form.project"
            class="inp"
            :disabled="scopeForbidden"
          >
            <option :value="null">
              {{ t("references.contract_templates.fields.project_any") }}
            </option>
            <option v-for="p in projects" :key="p.id" :value="p.id">
              {{ projectLabel(p) }}
            </option>
          </select>
          <div class="mt-2 flex items-center gap-2 flex-wrap">
            <span :class="isGlobal ? 'chip chip-primary' : 'chip chip-ghost'">
              {{
                isGlobal
                  ? t("references.contract_templates.scope_global")
                  : t("references.contract_templates.scope_project")
              }}
            </span>
            <div class="ml-auto">
              <ToggleSwitch
                v-model="form.is_active"
                :active-label="t('common.active')"
                :inactive-label="t('common.inactive')"
              />
            </div>
          </div>
          <div v-if="scopeForbidden" class="mt-2 text-[11px] text-ym-danger">
            {{ t("references.contract_templates.global_forbidden") }}
          </div>
        </div>

        <!-- Catalog picker — fills the remaining viewport height.
             HTML flow: click → insert `{{key}}` at the Tiptap caret.
             DOCX flow: click → copy `{{ dotted.path }}` to clipboard,
             author then pastes it into Word. -->
        <div class="card p-4 flex-1 min-h-0 flex flex-col">
          <div class="text-[12px] font-semibold mb-1 flex-shrink-0">
            {{ t("references.contract_templates.catalog_title") }}
          </div>
          <div class="text-[11px] text-ym-muted mb-3 leading-snug flex-shrink-0">
            {{
              form.source === "docx"
                ? t("references.contract_templates.catalog_hint_docx")
                : t("references.contract_templates.catalog_hint")
            }}
          </div>

          <div class="flex flex-col gap-4 flex-1 overflow-auto art-scroll pr-1 min-h-0">
            <div
              v-for="cat in CATALOG_CATEGORIES"
              :key="cat"
              class="flex flex-col gap-1.5"
            >
              <div
                class="text-[10px] uppercase tracking-wider font-mono text-ym-subtle"
              >
                {{ categoryLabel(cat) }}
              </div>
              <div class="grid grid-cols-1 gap-1">
                <button
                  v-for="entry in grouped[cat]"
                  :key="entry.key"
                  type="button"
                  class="text-left px-2.5 py-1.5 rounded border transition-colors flex items-center justify-between gap-2"
                  :class="
                    form.source === 'html' && isRegistered(entry.key)
                      ? 'border-ym-primary bg-ym-primary-soft text-ym-primary'
                      : 'border-ym-line-soft bg-ym-surface hover:border-ym-primary hover:bg-ym-primary-soft/40'
                  "
                  @click="
                    form.source === 'docx'
                      ? copyTagToClipboard(entry.path)
                      : pickFromCatalog(entry)
                  "
                >
                  <span class="flex flex-col min-w-0">
                    <span class="text-[12px] font-medium truncate">
                      {{ catalogLabel(entry) }}
                    </span>
                    <span
                      class="mono text-[10.5px] truncate opacity-70"
                      v-text="
                        form.source === 'docx'
                          ? `{{ ${entry.path} }}`
                          : `{{${entry.key}}}`
                      "
                    />
                  </span>
                  <i
                    v-if="form.source === 'html' && isRegistered(entry.key)"
                    class="pi pi-check-circle text-[12px]"
                  />
                  <i
                    v-else-if="form.source === 'docx'"
                    class="pi pi-copy text-[11px] opacity-60"
                  />
                  <i v-else class="pi pi-plus text-[10px] opacity-60" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="saveError" class="mt-4 text-sm text-ym-danger break-all px-1">
      {{ saveError }}
    </div>
  </div>
</template>
