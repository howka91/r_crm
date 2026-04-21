<script setup lang="ts">
import { AxiosError } from "axios"
import { onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRouter } from "vue-router"

import { roleApi, type RoleWritePayload } from "@/api/endpoints/users"
import { usePermissionStore } from "@/stores/permissions"
import type { Role } from "@/types/models"

const { t, locale } = useI18n()
const router = useRouter()
const permissions = usePermissionStore()

const roles = ref<Role[]>([])
const loading = ref(false)
const showCreate = ref(false)
const createError = ref<string | null>(null)

const form = reactive<RoleWritePayload>({
  code: "",
  name: { ru: "", uz: "", oz: "" },
  permissions: {},
  allowed_payment_types: [],
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
  form.allowed_payment_types = []
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
  if (!confirm(`Удалить роль ${role.code}?`)) return
  try {
    await roleApi.destroy(role.id)
    await load()
  } catch (e) {
    alert(e instanceof AxiosError ? JSON.stringify(e.response?.data) : t("errors.unknown"))
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
        class="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700"
        @click="openCreate"
      >
        + {{ t("common.create") }}
      </button>
    </div>

    <div v-if="loading">{{ t("common.loading") }}</div>

    <table v-else class="w-full border border-surface-200 dark:border-surface-800 rounded">
      <thead class="bg-surface-100 dark:bg-surface-900 text-sm">
        <tr>
          <th class="text-left px-3 py-2">Код</th>
          <th class="text-left px-3 py-2">Название</th>
          <th class="text-left px-3 py-2">Активна</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in roles"
          :key="r.id"
          class="border-t border-surface-200 dark:border-surface-800 text-sm"
        >
          <td class="px-3 py-2 font-mono">{{ r.code }}</td>
          <td class="px-3 py-2">{{ roleNameLocal(r) }}</td>
          <td class="px-3 py-2">{{ r.is_active ? t("common.yes") : t("common.no") }}</td>
          <td class="px-3 py-2 text-right">
            <button
              v-if="permissions.check('administration.roles.permissions')"
              class="text-primary-600 hover:underline mr-3"
              @click="editRole(r)"
            >
              {{ t("common.edit") }}
            </button>
            <button
              v-if="permissions.check('administration.roles.delete')"
              class="text-red-600 hover:underline"
              @click="remove(r)"
            >
              {{ t("common.delete") }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div
      v-if="showCreate"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="showCreate = false"
    >
      <div
        class="bg-white dark:bg-surface-900 rounded-lg p-6 w-full max-w-md shadow-xl border border-surface-200 dark:border-surface-800"
      >
        <h2 class="text-lg font-semibold mb-4">{{ t("common.create") }}</h2>
        <div class="space-y-3 text-sm">
          <div>
            <label class="block mb-1">Код (slug, латиница)</label>
            <input
              v-model="form.code"
              placeholder="sales-manager"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">Название (RU)</label>
            <input
              v-model="form.name.ru"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">Nomi (UZ)</label>
            <input
              v-model="form.name.uz"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">Номи (OZ)</label>
            <input
              v-model="form.name.oz"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
        </div>
        <div v-if="createError" class="mt-3 text-sm text-red-600">{{ createError }}</div>
        <div class="mt-5 flex justify-end gap-2">
          <button
            class="px-4 py-2 border rounded hover:bg-surface-100 dark:hover:bg-surface-800"
            @click="showCreate = false"
          >
            {{ t("common.cancel") }}
          </button>
          <button class="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700" @click="create">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
