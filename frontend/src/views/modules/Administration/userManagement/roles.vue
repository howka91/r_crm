<script setup lang="ts">
/**
 * Roles list + create modal.
 * Mirrors `yangi-mahalla-main/src/views/modules/Administration/userManagement/roles.vue`.
 */
import { AxiosError } from "axios"
import { onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { roleApi, type RoleWritePayload } from "@/api/administration"
import { useConfirmStore } from "@/store/confirm"
import { usePermissionStore } from "@/store/permissions"
import { useToastStore } from "@/store/toast"
import type { Role } from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const roles = ref<Role[]>([])
const loading = ref(false)
const showCreate = ref(false)
const createError = ref<string | null>(null)

const form = reactive<RoleWritePayload>({
  code: "",
  name: { ru: "", uz: "", oz: "" },
  permissions: {},
  is_active: true,
})

async function load() {
  loading.value = true
  try {
    const data = await roleApi.list({ limit: 100 })
    roles.value = data.results
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.code = ""
  form.name = { ru: "", uz: "", oz: "" }
  form.permissions = {}
  form.is_active = true
}

function openCreate() {
  resetForm()
  createError.value = null
  showCreate.value = true
}

async function create() {
  createError.value = null
  try {
    const created = await roleApi.create(form)
    showCreate.value = false
    await load()
    router.push({ name: "admin-role-edit", params: { id: created.id } })
  } catch (e) {
    if (e instanceof AxiosError && e.response?.data) {
      createError.value = JSON.stringify(e.response.data)
    } else {
      createError.value = t("errors.unknown")
    }
  }
}

async function remove(role: Role) {
  const ok = await confirmStore.ask({
    title: t("common.delete"),
    message: role.code,
    severity: "danger",
    okLabel: t("common.delete"),
  })
  if (!ok) return
  try {
    await roleApi.destroy(role.id)
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

function editRole(role: Role) {
  router.push({ name: "admin-role-edit", params: { id: role.id } })
}

function roleNameLocal(role: Role): string {
  return role.name[locale.value as "ru" | "uz" | "oz"] || role.code
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">{{ t("nav.admin_permissions") }}</h1>
      <button
        v-if="permissions.check('administration.roles.create')"
        class="btn btn-primary"
        @click="openCreate"
      >
        <i class="pi pi-plus text-[11px]" />
        {{ t("common.create") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>Код</th>
            <th>Название</th>
            <th>Активна</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in roles" :key="r.id">
            <td class="font-mono text-[12.5px] text-ym-primary">{{ r.code }}</td>
            <td class="font-medium">{{ roleNameLocal(r) }}</td>
            <td>
              <span
                :class="r.is_active ? 'chip chip-success' : 'chip chip-ghost'"
              >
                {{ r.is_active ? t("common.yes") : t("common.no") }}
              </span>
            </td>
            <td class="text-right whitespace-nowrap">
              <button
                v-if="permissions.check('administration.roles.permissions')"
                class="btn btn-ghost btn-sm mr-2"
                @click="editRole(r)"
              >
                {{ t("common.edit") }}
              </button>
              <button
                v-if="permissions.check('administration.roles.delete')"
                class="btn btn-danger btn-sm"
                @click="remove(r)"
              >
                {{ t("common.delete") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="showCreate"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="showCreate = false"
    >
      <div class="card w-full max-w-md p-6 shadow-ym-modal">
        <h2 class="text-lg font-semibold mb-4">{{ t("common.create") }}</h2>
        <div class="space-y-3 text-sm">
          <div>
            <label class="block mb-1.5 font-medium">Код (slug, латиница)</label>
            <input v-model="form.code" placeholder="sales-manager" class="inp" />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Название (RU)</label>
            <input v-model="form.name.ru" class="inp" />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Nomi (UZ)</label>
            <input v-model="form.name.uz" class="inp" />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Номи (OZ)</label>
            <input v-model="form.name.oz" class="inp" />
          </div>
        </div>
        <div v-if="createError" class="mt-3 text-sm text-ym-danger">{{ createError }}</div>
        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showCreate = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="create">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
