<script setup lang="ts">
/**
 * Staff (users) admin screen — list + create/edit modal.
 *
 * Mirrors `yangi-mahalla-main/src/views/modules/Administration/userManagement/index.vue`
 * (filename `index.vue` is the Vuexy convention for the module root view).
 */
import { AxiosError } from "axios"
import { onMounted, reactive, ref } from "vue"
import { useI18n } from "vue-i18n"

import { roleApi, staffApi, type StaffWritePayload } from "@/api/administration"
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
      <button class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus text-[11px]" />
        {{ t("common.create") }}
      </button>
    </div>

    <div v-if="loading" class="text-ym-muted">{{ t("common.loading") }}</div>

    <div v-else class="card overflow-hidden">
      <table class="tbl">
        <thead>
          <tr>
            <th>Email</th>
            <th>ФИО</th>
            <th>Роль</th>
            <th>Телефон</th>
            <th>Активен</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="font-mono text-[12.5px] text-ym-primary">{{ u.email }}</td>
            <td class="font-medium">{{ u.full_name }}</td>
            <td class="text-ym-muted">{{ u.role?.code ?? "—" }}</td>
            <td class="font-mono text-[12.5px]">{{ u.phone_number }}</td>
            <td>
              <span
                :class="u.is_active ? 'chip chip-success' : 'chip chip-ghost'"
              >
                {{ u.is_active ? t("common.yes") : t("common.no") }}
              </span>
            </td>
            <td class="text-right whitespace-nowrap">
              <button class="btn btn-ghost btn-sm mr-2" @click="openEdit(u)">
                {{ t("common.edit") }}
              </button>
              <button class="btn btn-danger btn-sm" @click="remove(u)">
                {{ t("common.delete") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Simple modal. Real PrimeVue Dialog can replace this later. -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="showModal = false"
    >
      <div class="card w-full max-w-md p-6 shadow-ym-modal">
        <h2 class="text-lg font-semibold mb-4">
          {{ editing ? t("common.edit") : t("common.create") }}
        </h2>

        <div class="space-y-3 text-sm">
          <div>
            <label class="block mb-1.5 font-medium">Email</label>
            <input v-model="form.email" type="email" class="inp" />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">ФИО</label>
            <input v-model="form.full_name" class="inp" />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Телефон</label>
            <input
              v-model="form.phone_number"
              placeholder="+998901234567"
              class="inp font-mono"
            />
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Роль</label>
            <select v-model="form.role_id" class="inp">
              <option :value="null">—</option>
              <option v-for="r in roles" :key="r.id" :value="r.id">
                {{ r.code }}
              </option>
            </select>
          </div>
          <div>
            <label class="block mb-1.5 font-medium">Язык</label>
            <select v-model="form.language" class="inp">
              <option value="ru">Русский</option>
              <option value="uz">Oʻzbekcha</option>
              <option value="oz">Ўзбекча</option>
            </select>
          </div>
          <div>
            <label class="block mb-1.5 font-medium">
              {{ editing ? "Новый пароль (оставить пустым, чтобы не менять)" : "Пароль" }}
            </label>
            <input v-model="form.password" type="password" class="inp" />
          </div>
          <label class="flex items-center gap-2">
            <input v-model="form.is_active" type="checkbox" />
            <span>Активен</span>
          </label>
        </div>

        <div v-if="saveError" class="mt-3 text-sm text-ym-danger">{{ saveError }}</div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="btn btn-ghost" @click="showModal = false">
            {{ t("common.cancel") }}
          </button>
          <button class="btn btn-primary" @click="save">
            {{ t("common.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
