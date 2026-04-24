<!--
  PhotoGallery — reusable photo grid for Project / Building galleries.

  Parent owns the photo list and the action handlers; the component
  renders cards, the «+ Add photo» tile (when canEdit), the hover
  actions, and opens the lightbox on click.

  First photo by order in `photos` = cover; badge «Обложка» on it.
  Non-cover tiles show a hover button «Сделать обложкой» that calls
  `onMakeCover`.
-->
<script setup lang="ts">
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"

import PhotoLightbox from "@/components/PhotoLightbox.vue"
import { useConfirmStore } from "@/store/confirm"

interface Photo {
  id: number
  file: string | null
  caption: string
  sort: number
}

const props = defineProps<{
  photos: Photo[]
  canEdit: boolean
  /** Called with a File picked in the upload tile. Parent builds the
   *  FormData with `project`/`building` FK and POSTs. */
  onUpload?: (file: File) => Promise<void> | void
  onDelete?: (id: number) => Promise<void> | void
  onMakeCover?: (id: number) => Promise<void> | void
  onEditCaption?: (id: number, caption: string) => Promise<void> | void
}>()

const { t } = useI18n()
const confirmStore = useConfirmStore()

const ALLOWED_MIMES = [
  "image/png", "image/jpeg", "image/webp", "image/gif",
]
const MAX_FILE_BYTES = 10 * 1024 * 1024

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const uploadError = ref<string | null>(null)
const editingCaptionId = ref<number | null>(null)
const captionDraft = ref("")

function openLightbox(idx: number) {
  lightboxIndex.value = idx
  lightboxOpen.value = true
}

async function onFilePicked(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  if (!file) return
  uploadError.value = null
  if (!ALLOWED_MIMES.includes(file.type)) {
    uploadError.value = t("errors.photo.bad_mime")
    return
  }
  if (file.size > MAX_FILE_BYTES) {
    uploadError.value = t("errors.photo.too_large")
    return
  }
  await props.onUpload?.(file)
  // Reset the native input so the same file can be re-picked later.
  ;(e.target as HTMLInputElement).value = ""
}

async function askDelete(photo: Photo) {
  const ok = await confirmStore.ask({
    title: t("objects.photos.confirm_delete"),
    message: photo.caption || `#${photo.id}`,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  await props.onDelete?.(photo.id)
}

function startEditCaption(photo: Photo) {
  editingCaptionId.value = photo.id
  captionDraft.value = photo.caption
}

async function commitCaption(photo: Photo) {
  const next = captionDraft.value.trim()
  editingCaptionId.value = null
  if (next === photo.caption) return
  await props.onEditCaption?.(photo.id, next)
}

const coverId = computed(() => props.photos[0]?.id ?? null)
</script>

<template>
  <div>
    <div
      v-if="photos.length === 0 && !canEdit"
      class="card p-8 text-center text-ym-muted text-[13px]"
    >
      {{ t("objects.photos.empty") }}
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      <!-- Photo tiles -->
      <div
        v-for="(photo, idx) in photos"
        :key="photo.id"
        class="group relative aspect-[4/3] rounded-md overflow-hidden border cursor-pointer"
        :class="
          photo.id === coverId
            ? 'border-ym-primary ring-2 ring-ym-primary/40'
            : 'border-ym-line-soft'
        "
        @click="openLightbox(idx)"
      >
        <img
          v-if="photo.file"
          :src="photo.file"
          class="w-full h-full object-cover"
        />
        <div
          v-else
          class="w-full h-full bg-ym-sunken/60 flex items-center justify-center text-ym-subtle"
        >
          <i class="pi pi-image text-[22px]" />
        </div>

        <!-- Cover badge -->
        <span
          v-if="photo.id === coverId"
          class="absolute top-2 left-2 chip chip-primary text-[10.5px]"
        >
          <i class="pi pi-star-fill text-[9px]" />
          {{ t("objects.photos.cover_badge") }}
        </span>

        <!-- Hover action bar -->
        <div
          v-if="canEdit"
          class="absolute inset-x-0 bottom-0 p-2 flex gap-1 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"
          @click.stop
        >
          <button
            v-if="photo.id !== coverId"
            type="button"
            class="btn btn-xs bg-white/90 hover:bg-white text-ym-text"
            :title="t('objects.photos.make_cover')"
            @click="onMakeCover?.(photo.id)"
          >
            <i class="pi pi-star text-[10px]" />
          </button>
          <button
            type="button"
            class="btn btn-xs bg-white/90 hover:bg-white text-ym-text"
            :title="t('objects.photos.edit_caption')"
            @click="startEditCaption(photo)"
          >
            <i class="pi pi-pencil text-[10px]" />
          </button>
          <button
            type="button"
            class="btn btn-xs bg-white/90 hover:bg-white text-ym-danger ml-auto"
            :title="t('common.delete')"
            @click="askDelete(photo)"
          >
            <i class="pi pi-trash text-[10px]" />
          </button>
        </div>

        <!-- Caption strip / editor -->
        <div
          v-if="editingCaptionId === photo.id"
          class="absolute inset-x-0 top-0 p-2 bg-black/80"
          @click.stop
        >
          <input
            v-model="captionDraft"
            class="inp inp-sm w-full"
            :placeholder="t('objects.photos.caption_placeholder')"
            autofocus
            @keydown.enter.prevent="commitCaption(photo)"
            @keydown.escape.prevent="editingCaptionId = null"
            @blur="commitCaption(photo)"
          />
        </div>
        <div
          v-else-if="photo.caption"
          class="absolute inset-x-0 bottom-0 px-2 py-1 text-[11px] text-white bg-black/50 truncate group-hover:opacity-0 transition-opacity"
        >
          {{ photo.caption }}
        </div>
      </div>

      <!-- Upload tile -->
      <label
        v-if="canEdit"
        class="aspect-[4/3] rounded-md border-2 border-dashed border-ym-line hover:border-ym-primary cursor-pointer flex flex-col items-center justify-center gap-2 text-ym-muted hover:text-ym-primary transition-colors"
      >
        <i class="pi pi-plus text-[18px]" />
        <span class="text-[12px] font-medium">
          {{ t("objects.photos.add") }}
        </span>
        <input
          type="file"
          :accept="ALLOWED_MIMES.join(',')"
          class="hidden"
          @change="onFilePicked"
        />
      </label>
    </div>

    <div v-if="uploadError" class="mt-2 text-[12px] text-ym-danger">
      {{ uploadError }}
    </div>

    <PhotoLightbox
      v-model:open="lightboxOpen"
      :photos="photos"
      :start-index="lightboxIndex"
    />
  </div>
</template>
