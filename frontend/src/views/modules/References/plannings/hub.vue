<script setup lang="ts">
/**
 * Plannings hub — one card per ЖК with a count of layouts registered
 * inside. Clicking a card drills into the per-project planning list.
 *
 * Data load is a 2-call parallel fetch (projects + plannings) grouped
 * on the client; acceptable up to ~20 ЖК × ~500 plannings. When the
 * fleet grows the backend can expose a `plannings_count` annotation
 * on ProjectSerializer to collapse this into a single request.
 */
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { planningsApi } from "@/api/references"
import { projectsApi } from "@/api/objects"
import type { I18nText, Planning, Project } from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()

const projects = ref<Project[]>([])
const counts = ref<Record<number, number>>({})
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [projResp, planResp] = await Promise.all([
      projectsApi.list({ limit: 500, ordering: "sort,id" }),
      planningsApi.list({ limit: 1000 }),
    ])
    projects.value = projResp.results
    const acc: Record<number, number> = {}
    for (const p of planResp.results) {
      acc[p.project] = (acc[p.project] ?? 0) + 1
    }
    counts.value = acc
  } finally {
    loading.value = false
  }
}

function projectTitle(p: Project): string {
  return p.title[locale.value as keyof I18nText] || `#${p.id}`
}

function openProject(id: number) {
  router.push(`/references/plannings/project/${id}`)
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-start justify-between mb-5 mt-1 px-1 gap-4">
      <div>
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle flex items-center gap-2"
        >
          <button class="hover:text-ym-primary" @click="router.push('/references')">
            {{ t("nav.references") }}
          </button>
          <span>/</span>
          <span>{{ t("references.plannings.title") }}</span>
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("references.plannings.hub_title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.plannings.subtitle") }}
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="!projects.length"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("references.plannings.hub_empty") }}
      <div class="mt-3">
        <button class="btn btn-primary btn-sm" @click="router.push('/objects')">
          {{ t("nav.objects") }}
          <i class="pi pi-arrow-right text-[10px]" />
        </button>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <button
        v-for="p in projects"
        :key="p.id"
        type="button"
        class="card card-hover p-5 text-left flex flex-col gap-3"
        @click="openProject(p.id)"
      >
        <div
          class="w-10 h-10 rounded-md flex items-center justify-center bg-ym-primary-soft text-ym-primary"
        >
          <i class="pi pi-folder text-[18px]" />
        </div>
        <div>
          <div class="text-[15px] font-semibold leading-tight">
            {{ projectTitle(p) }}
          </div>
          <div class="text-[12px] text-ym-muted mt-1 truncate">
            {{ p.address || "—" }}
          </div>
        </div>
        <div class="mt-auto flex items-center justify-between">
          <span class="chip chip-ghost">
            {{ t("references.plannings.count_label", { n: counts[p.id] ?? 0 }) }}
          </span>
          <i class="pi pi-arrow-right text-[11px] text-ym-primary" />
        </div>
      </button>
    </div>
  </div>
</template>
