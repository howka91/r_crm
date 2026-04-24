<script setup lang="ts">
/**
 * Project overview tab — lives next to inventory/pricing/structure.
 *
 * Shows the ЖК "face": cover hero, name+developer+address, description,
 * a few summary metrics (buildings/apartments counts), and the full
 * photo gallery with upload/delete/make-cover actions.
 *
 * Gallery CRUD goes through `projectPhotosApi` — which in turn relies
 * on the backend `prefetch_related("photos")` to keep the hub card
 * grid N+1-free (see TestProjectCoverInSerializer).
 */
import { AxiosError } from "axios"
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import PhotoGallery from "@/components/PhotoGallery.vue"
import { projectPhotosApi, projectsApi } from "@/api/objects"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type { I18nText, Project, ProjectPhoto } from "@/types/models"

const props = defineProps<{ id: string | number }>()

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const toastStore = useToastStore()

const projectId = computed(() => Number(props.id))
const project = ref<Project | null>(null)
const photos = ref<ProjectPhoto[]>([])
const loading = ref(false)

const canEdit = computed(() => permissions.check("objects.projects.edit"))

async function load() {
  loading.value = true
  try {
    const [proj, photosResp] = await Promise.all([
      projectsApi.retrieve(projectId.value),
      projectPhotosApi.list({
        project: projectId.value,
        is_active: "true",
        limit: 200,
        ordering: "sort,id",
      }),
    ])
    project.value = proj
    photos.value = photosResp.results
  } finally {
    loading.value = false
  }
}

// --- Gallery callbacks ---------------------------------------------------

async function uploadPhoto(file: File) {
  const fd = new FormData()
  fd.append("project", String(projectId.value))
  fd.append("file", file)
  try {
    const created = await projectPhotosApi.upload(fd)
    photos.value = [...photos.value, created].sort(
      (a, b) => a.sort - b.sort || a.id - b.id,
    )
    toastStore.success(t("common.saved"))
  } catch (e) {
    toastStore.error(apiErr(e))
  }
}

async function deletePhoto(id: number) {
  try {
    await projectPhotosApi.destroy(id)
    photos.value = photos.value.filter((p) => p.id !== id)
    toastStore.success(t("common.deleted"))
  } catch (e) {
    toastStore.error(apiErr(e))
  }
}

async function makeCover(id: number) {
  try {
    await projectPhotosApi.makeCover(id)
    // Reorder client-side to avoid a full refetch: put the picked one
    // first, push everyone else by 1, then re-sort.
    photos.value = photos.value
      .map((p, idx) => {
        if (p.id === id) return { ...p, sort: 0 }
        return { ...p, sort: idx + 1 }
      })
      .sort((a, b) => a.sort - b.sort || a.id - b.id)
  } catch (e) {
    toastStore.error(apiErr(e))
  }
}

async function editCaption(id: number, caption: string) {
  try {
    const updated = await projectPhotosApi.updateJson(id, { caption })
    photos.value = photos.value.map((p) => (p.id === id ? updated : p))
  } catch (e) {
    toastStore.error(apiErr(e))
  }
}

function apiErr(e: unknown): string {
  if (e instanceof AxiosError && e.response?.data) {
    return JSON.stringify(e.response.data)
  }
  return t("errors.unknown")
}

// --- Helpers -------------------------------------------------------------

function projectTitle(): string {
  if (!project.value) return ""
  return (
    project.value.title[locale.value as keyof I18nText]
      || `#${project.value.id}`
  )
}

function developerName(): string {
  const dev = project.value?.developer_name
  if (!dev) return "—"
  return dev[locale.value as keyof I18nText] || "—"
}

function localizedDescription(): string {
  if (!project.value) return ""
  return project.value.description?.[locale.value as keyof I18nText] || ""
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-3 mt-1 px-1 gap-4">
      <div class="min-w-0">
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle flex items-center gap-2"
        >
          <button class="hover:text-ym-primary" @click="router.push('/objects')">
            {{ t("nav.objects") }}
          </button>
          <span>/</span>
          <span class="truncate">{{ projectTitle() }}</span>
        </div>
        <h1
          class="text-[28px] font-semibold leading-none tracking-[-0.025em] truncate"
        >
          {{ projectTitle() }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("objects.overview.subtitle") }}
        </div>
      </div>
    </div>

    <!-- Tab strip: Каталог → Обзор → Прайсинг → Структура -->
    <div class="flex gap-1 mb-5 border-b border-ym-line-soft">
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}/inventory`)"
      >
        {{ t("objects.tabs.inventory") }}
      </button>
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-ym-primary text-ym-primary font-medium"
      >
        {{ t("objects.tabs.overview") }}
      </button>
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}/pricing`)"
      >
        {{ t("objects.tabs.pricing") }}
      </button>
      <button
        class="px-3 py-2 text-[13px] border-b-2 border-transparent text-ym-muted hover:text-ym-text"
        @click="router.push(`/objects/projects/${projectId}/structure`)"
      >
        {{ t("objects.tabs.structure") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else-if="project" class="space-y-5">
      <!-- Hero + meta -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div
          class="lg:col-span-2 aspect-[16/9] rounded-md overflow-hidden bg-ym-sunken/60 border border-ym-line-soft flex items-center justify-center"
        >
          <img
            v-if="project.cover?.url"
            :src="project.cover.url"
            class="w-full h-full object-cover"
          />
          <div
            v-else
            class="flex flex-col items-center gap-2 text-ym-subtle"
          >
            <i class="pi pi-building text-[36px]" />
            <span class="text-[12px]">{{ t("objects.overview.no_cover") }}</span>
          </div>
        </div>
        <div class="card p-4 flex flex-col gap-3 text-[13px]">
          <div>
            <div
              class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-1"
            >
              {{ t("objects.projects.fields.developer") }}
            </div>
            <div class="font-medium">{{ developerName() }}</div>
          </div>
          <div v-if="project.address">
            <div
              class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-1"
            >
              {{ t("objects.overview.address") }}
            </div>
            <div>{{ project.address }}</div>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-auto pt-3 border-t border-ym-line-soft">
            <div>
              <div class="text-[11px] text-ym-muted">
                {{ t("objects.overview.buildings_count") }}
              </div>
              <div class="text-[20px] font-semibold mt-0.5">
                {{ project.buildings_count }}
              </div>
            </div>
            <div>
              <div class="text-[11px] text-ym-muted">
                {{ t("objects.overview.photos_count") }}
              </div>
              <div class="text-[20px] font-semibold mt-0.5">
                {{ photos.length }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div v-if="localizedDescription()" class="card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle mb-2"
        >
          {{ t("objects.overview.description") }}
        </div>
        <p class="text-[13px] leading-relaxed whitespace-pre-line">
          {{ localizedDescription() }}
        </p>
      </div>

      <!-- Gallery -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="text-[13px] font-semibold">
            {{ t("objects.overview.gallery") }}
          </div>
          <div class="text-[11px] text-ym-muted">
            {{ t("objects.overview.gallery_hint") }}
          </div>
        </div>
        <PhotoGallery
          :photos="photos"
          :can-edit="canEdit"
          :on-upload="uploadPhoto"
          :on-delete="deletePhoto"
          :on-make-cover="makeCover"
          :on-edit-caption="editCaption"
        />
      </div>
    </div>
  </div>
</template>
