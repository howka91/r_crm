<script setup lang="ts">
import { AxiosError } from "axios"
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"

import { roleApi } from "@/api/endpoints/users"
import PermissionTreeEditor from "@/components/admin/PermissionTreeEditor.vue"
import { usePermissionStore } from "@/stores/permissions"
import type { Role } from "@/types/models"

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const permissions = usePermissionStore()

const role = ref<Role | null>(null)
const perms = ref<Record<string, boolean>>({})
const paymentTypes = ref<string[]>([])
const saving = ref(false)
const saveError = ref<string | null>(null)

const paymentTypeOptions = [
  { value: "bank", label: "Банк" },
  { value: "cash", label: "Наличные" },
  { value: "barter", label: "Бартер" },
]

const roleId = computed(() => Number(route.params.id))

async function load() {
  const r = await roleApi.retrieve(roleId.value)
  role.value = r
  perms.value = { ...r.permissions }
  paymentTypes.value = [...r.allowed_payment_types]

  // Permission tree comes from the shared store.
  await permissions.loadTree()
}

async function save() {
  if (!role.value) return
  saving.value = true
  saveError.value = null
  try {
    const updated = await roleApi.update(role.value.id, {
      permissions: perms.value,
      allowed_payment_types: paymentTypes.value as ("bank" | "cash" | "barter")[],
    })
    role.value = updated
    perms.value = { ...updated.permissions }
    // If the edited role is the current user's, refresh permission cache.
    permissions.setFromStaff({
      is_superuser: false,
      role: updated,
    })
  } catch (e) {
    saveError.value =
      e instanceof AxiosError
        ? JSON.stringify(e.response?.data ?? e.message)
        : t("errors.unknown")
  } finally {
    saving.value = false
  }
}

function togglePaymentType(value: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) {
    if (!paymentTypes.value.includes(value)) paymentTypes.value.push(value)
  } else {
    paymentTypes.value = paymentTypes.value.filter((v) => v !== value)
  }
}

onMounted(load)
</script>

<template>
  <div v-if="role" class="space-y-6 max-w-4xl">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">{{ role.code }}</h1>
        <div class="text-sm text-surface-500">{{ role.name.ru }}</div>
      </div>
      <div class="flex gap-2">
        <button
          class="px-4 py-2 border rounded hover:bg-surface-100 dark:hover:bg-surface-800"
          @click="router.push({ name: 'admin-roles' })"
        >
          {{ t("common.back") }}
        </button>
        <button
          :disabled="saving"
          class="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
          @click="save"
        >
          {{ t("common.save") }}
        </button>
      </div>
    </div>

    <!-- Payment types -->
    <section class="border rounded p-4 border-surface-200 dark:border-surface-800">
      <h2 class="font-semibold mb-3">Разрешённые типы оплаты</h2>
      <div class="flex gap-4">
        <label
          v-for="pt in paymentTypeOptions"
          :key="pt.value"
          class="inline-flex items-center gap-2 text-sm"
        >
          <input
            type="checkbox"
            :checked="paymentTypes.includes(pt.value)"
            @change="togglePaymentType(pt.value, $event)"
          />
          {{ pt.label }}
        </label>
      </div>
    </section>

    <!-- Permission tree -->
    <section class="border rounded p-4 border-surface-200 dark:border-surface-800">
      <h2 class="font-semibold mb-3">Разрешения</h2>
      <div v-if="permissions.tree.length === 0" class="text-sm text-surface-500">
        {{ t("common.loading") }}
      </div>
      <PermissionTreeEditor v-else v-model="perms" :nodes="permissions.tree" />
    </section>

    <div v-if="saveError" class="text-sm text-red-600">{{ saveError }}</div>
  </div>
  <div v-else>{{ t("common.loading") }}</div>
</template>
