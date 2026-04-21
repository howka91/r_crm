<script setup lang="ts">
import { AxiosError } from "axios"
import { onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"

import { roleApi, staffApi, type StaffWritePayload } from "@/api/endpoints/users"
import type { Role, Staff } from "@/types/models"

const { t } = useI18n()

const users = ref<Staff[]>([])
const roles = ref<Role[]>([])
const loading = ref(false)
const editing = ref<Staff | null>(null)
const showModal = ref(false)
const saveError = ref<string | null>(null)

const form = reactive<StaffWritePayload>({
  email: "",
  full_name: "",
  phone_number: "",
  language: "ru",
  theme: "light",
  role_id: null,
  is_active: true,
  password: "",
})

async function load() {
  loading.value = true
  try {
    const [u, r] = await Promise.all([
      staffApi.list({ limit: 100 }),
      roleApi.list({ limit: 100 }),
    ])
    users.value = u.results
    roles.value = r.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    email: "",
    full_name: "",
    phone_number: "",
    language: "ru",
    theme: "light",
    role_id: null,
    is_active: true,
    password: "",
  })
  saveError.value = null
  showModal.value = true
}

function openEdit(user: Staff) {
  editing.value = user
  Object.assign(form, {
    email: user.email,
    full_name: user.full_name,
    phone_number: user.phone_number,
    language: user.language,
    theme: user.theme,
    role_id: user.role?.id ?? null,
    is_active: user.is_active,
    password: "",
  })
  saveError.value = null
  showModal.value = true
}

async function save() {
  saveError.value = null
  try {
    const payload: Partial<StaffWritePayload> = { ...form }
    if (!payload.password) delete payload.password
    if (editing.value) {
      await staffApi.update(editing.value.id, payload)
    } else {
      await staffApi.create(form)
    }
    showModal.value = false
    await load()
  } catch (e) {
    if (e instanceof AxiosError && e.response?.data) {
      saveError.value = JSON.stringify(e.response.data)
    } else {
      saveError.value = t("errors.unknown")
    }
  }
}

async function remove(user: Staff) {
  if (!confirm(`Удалить ${user.full_name || user.email}?`)) return
  await staffApi.destroy(user.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">{{ t("nav.admin_users") }}</h1>
      <button
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
          <th class="text-left px-3 py-2">Email</th>
          <th class="text-left px-3 py-2">ФИО</th>
          <th class="text-left px-3 py-2">Роль</th>
          <th class="text-left px-3 py-2">Телефон</th>
          <th class="text-left px-3 py-2">Активен</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="u in users"
          :key="u.id"
          class="border-t border-surface-200 dark:border-surface-800 text-sm"
        >
          <td class="px-3 py-2">{{ u.email }}</td>
          <td class="px-3 py-2">{{ u.full_name }}</td>
          <td class="px-3 py-2">{{ u.role?.code ?? "—" }}</td>
          <td class="px-3 py-2">{{ u.phone_number }}</td>
          <td class="px-3 py-2">{{ u.is_active ? t("common.yes") : t("common.no") }}</td>
          <td class="px-3 py-2 text-right">
            <button class="text-primary-600 hover:underline mr-3" @click="openEdit(u)">
              {{ t("common.edit") }}
            </button>
            <button class="text-red-600 hover:underline" @click="remove(u)">
              {{ t("common.delete") }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Simple modal. Real PrimeVue Dialog can replace this later. -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="showModal = false"
    >
      <div
        class="bg-white dark:bg-surface-900 rounded-lg p-6 w-full max-w-md shadow-xl border border-surface-200 dark:border-surface-800"
      >
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("common.edit") : t("common.create") }}
        </h2>

        <div class="space-y-3 text-sm">
          <div>
            <label class="block mb-1">Email</label>
            <input
              v-model="form.email"
              type="email"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">ФИО</label>
            <input
              v-model="form.full_name"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">Телефон</label>
            <input
              v-model="form.phone_number"
              placeholder="+998901234567"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <div>
            <label class="block mb-1">Роль</label>
            <select v-model="form.role_id" class="w-full border rounded px-3 py-2 bg-transparent">
              <option :value="null">—</option>
              <option v-for="r in roles" :key="r.id" :value="r.id">
                {{ r.code }}
              </option>
            </select>
          </div>
          <div>
            <label class="block mb-1">Язык</label>
            <select v-model="form.language" class="w-full border rounded px-3 py-2 bg-transparent">
              <option value="ru">Русский</option>
              <option value="uz">Oʻzbekcha</option>
              <option value="oz">Ўзбекча</option>
            </select>
          </div>
          <div>
            <label class="block mb-1">
              {{ editing ? "Новый пароль (оставить пустым, чтобы не менять)" : "Пароль" }}
            </label>
            <input
              v-model="form.password"
              type="password"
              class="w-full border rounded px-3 py-2 bg-transparent"
            />
          </div>
          <label class="flex items-center gap-2">
            <input v-model="form.is_active" type="checkbox" />
            <span>Активен</span>
          </label>
        </div>

        <div v-if="saveError" class="mt-3 text-sm text-red-600">{{ saveError }}</div>

        <div class="mt-5 flex justify-end gap-2">
          <button
            class="px-4 py-2 border rounded hover:bg-surface-100 dark:hover:bg-surface-800"
            @click="showModal = false"
          >
            {{ t("common.cancel") }}
          </button>
          <button class="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700" @click="save">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
