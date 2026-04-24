<script setup lang="ts">
/**
 * ContractTemplate CRUD — list screen.
 *
 * Create/edit happens on a dedicated page (`edit.vue`) because the body
 * is a rich-text editor; shoehorning it into a modal trims the editor
 * surface and clobbers keyboard shortcuts.
 */
import { onMounted, ref, computed } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { contractTemplatesApi } from "@/api/contracts"
import { projectsApi } from "@/api/objects"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type { ContractTemplate, Project } from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const confirmStore = useConfirmStore()
const toastStore = useToastStore()

const items = ref<ContractTemplate[]>([])
const projects = ref<Project[]>([])
const loading = ref(false)

const canCreate = computed(() => permissions.check("references.templates.create"))
const canEdit = computed(() => permissions.check("references.templates.edit"))
const canDelete = computed(() => permissions.check("references.templates.delete"))

const projectMap = computed<Record<number, Project>>(() => {
  const map: Record<number, Project> = {}
  for (const p of projects.value) map[p.id] = p
  return map
})

function projectTitle(id: number | null): string {
  if (id === null) return t("references.contract_templates.scope_global")
  const p = projectMap.value[id]
  if (!p) return "—"
  return p.title[locale.value as "ru" | "uz" | "oz"] || `#${id}`
}

async function load() {
  loading.value = true
  try {
    const [tplResp, projResp] = await Promise.all([
      contractTemplatesApi.list({ limit: 200 }),
      projectsApi.list({ limit: 200 }),
    ])
    items.value = tplResp.results
    projects.value = projResp.results
  } finally {
    loading.value = false
  }
}

function create() {
  router.push({ name: "references-contract-templates-new" })
}

function edit(item: ContractTemplate) {
  router.push({
    name: "references-contract-templates-edit",
    params: { id: item.id },
  })
}

async function remove(item: ContractTemplate) {
  const ok = await confirmStore.ask({
    title: t("references.contract_templates.confirm_delete"),
    message: item.title,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await contractTemplatesApi.destroy(item.id)
    toastStore.success(t("common.save"))
    await load()
  } catch {
    toastStore.error(t("errors.unknown"))
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle"
        >
          {{ t("nav.references") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("references.contract_templates.title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("references.contract_templates.subtitle") }}
        </div>
      </div>
      <button v-if="canCreate" class="btn btn-primary" @click="create">
        <i class="pi pi-plus text-[11px]" />
        {{ t("references.contract_templates.new") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div
      v-else-if="items.length === 0"
      class="card p-8 text-center text-ym-muted"
    >
      {{ t("references.contract_templates.empty") }}
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("references.contract_templates.fields.title") }}</th>
            <th>{{ t("references.contract_templates.fields.project") }}</th>
            <th>
              {{ t("references.contract_templates.fields.placeholders") }}
            </th>
            <th>{{ t("references.columns.status") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id">
            <td class="font-medium">{{ i.title }}</td>
            <td>
              <span
                :class="
                  i.project === null ? 'chip chip-primary' : 'chip chip-ghost'
                "
              >
                {{ projectTitle(i.project) }}
              </span>
            </td>
            <td class="text-ym-muted font-mono text-[12.5px]">
              {{ i.placeholders.length }}
            </td>
            <td>
              <span
                :class="i.is_active ? 'chip chip-success' : 'chip chip-ghost'"
              >
                {{ i.is_active ? t("common.active") : t("common.inactive") }}
              </span>
            </td>
            <td class="text-right whitespace-nowrap">
              <button
                v-if="canEdit"
                class="btn btn-ghost btn-sm mr-2"
                @click="edit(i)"
              >
                {{ t("common.edit") }}
              </button>
              <button
                v-if="canDelete"
                class="btn btn-danger btn-sm"
                @click="remove(i)"
              >
                {{ t("common.delete") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
