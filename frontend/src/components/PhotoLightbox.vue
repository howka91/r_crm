<!--
  PhotoLightbox — fullscreen viewer for a list of images.

  Opens at `startIndex`, supports ←/→ arrows, Esc to close, click on
  backdrop to close. Caption shown at the bottom when present.

  Consumers keep the parent component responsible for the open/close
  state (v-model:open) and for the photo list.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue"

interface LightboxPhoto {
  id: number
  file: string | null
  caption: string
}

const props = defineProps<{
  open: boolean
  photos: LightboxPhoto[]
  startIndex?: number
}>()

const emit = defineEmits<{
  (e: "update:open", v: boolean): void
}>()

const index = ref(props.startIndex ?? 0)

watch(
  () => props.open,
  (o) => {
    if (o) {
      index.value = Math.min(
        Math.max(props.startIndex ?? 0, 0),
        Math.max(props.photos.length - 1, 0),
      )
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
  },
)

const current = computed(() => props.photos[index.value] ?? null)

function next() {
  if (!props.photos.length) return
  index.value = (index.value + 1) % props.photos.length
}
function prev() {
  if (!props.photos.length) return
  index.value = (index.value - 1 + props.photos.length) % props.photos.length
}
function close() {
  emit("update:open", false)
}

function onKey(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === "Escape") {
    e.preventDefault()
    close()
  } else if (e.key === "ArrowRight") {
    e.preventDefault()
    next()
  } else if (e.key === "ArrowLeft") {
    e.preventDefault()
    prev()
  }
}

onMounted(() => window.addEventListener("keydown", onKey))
onUnmounted(() => {
  window.removeEventListener("keydown", onKey)
  document.body.style.overflow = ""
})
</script>

<template>
  <Teleport to="body">
    <transition name="lightbox">
      <div
        v-if="open && current"
        class="fixed inset-0 z-[220] bg-black/90 flex items-center justify-center"
      >
        <!-- Close -->
        <button
          type="button"
          class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          @click="close"
        >
          <i class="pi pi-times text-[16px]" />
        </button>

        <!-- Prev / Next -->
        <button
          v-if="photos.length > 1"
          type="button"
          class="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          @click="prev"
        >
          <i class="pi pi-chevron-left text-[18px]" />
        </button>
        <button
          v-if="photos.length > 1"
          type="button"
          class="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          @click="next"
        >
          <i class="pi pi-chevron-right text-[18px]" />
        </button>

        <!-- Image -->
        <div class="max-w-[92vw] max-h-[88vh] flex flex-col items-center gap-3">
          <img
            v-if="current.file"
            :src="current.file"
            class="max-w-full max-h-[78vh] object-contain"
          />
          <div
            v-if="current.caption"
            class="text-[13px] text-white/90 text-center max-w-[80vw]"
          >
            {{ current.caption }}
          </div>
          <div v-if="photos.length > 1" class="text-[11px] text-white/60 font-mono">
            {{ index + 1 }} / {{ photos.length }}
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 160ms ease;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
</style>
