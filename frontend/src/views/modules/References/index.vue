<script setup lang="ts">
/**
 * References hub — overview grid. Each card links into a domain screen and
 * is hidden if the user lacks the corresponding `view` permission.
 */
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"

import { usePermissionStore } from "@/store/permissions"

const { t } = useI18n()
const permissions = usePermissionStore()

interface Card {
  to: string
  titleKey: string
  descKey: string
  icon: string
  permission: string
}

const cards: Card[] = [
  {
    to: "/references/developers",
    titleKey: "nav.references_developers",
    descKey: "references.card_developers_desc",
    icon: "pi-wrench",
    permission: "references.developers.view",
  },
  {
    to: "/references/sales-offices",
    titleKey: "nav.references_sales_offices",
    descKey: "references.card_sales_offices_desc",
    icon: "pi-inbox",
    permission: "references.offices.view",
  },
  {
    to: "/references/currencies",
    titleKey: "nav.references_currencies",
    descKey: "references.card_currencies_desc",
    icon: "pi-dollar",
    permission: "references.currencies.view",
  },
  {
    to: "/references/lookups",
    titleKey: "nav.references_lookups",
    descKey: "references.card_lookups_desc",
    icon: "pi-tags",
    permission: "references.lookups.view",
  },
]

const visible = computed(() => cards.filter((c) => permissions.check(c.permission)))
</script>

<template>
  <div>
    <div class="mb-5 mt-1 px-1">
      <div class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle">
        {{ t("nav.group_references") }}
      </div>
      <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
        {{ t("references.hub_title") }}
      </h1>
      <div class="text-[13px] mt-2 text-ym-muted">
        {{ t("references.hub_subtitle") }}
      </div>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <RouterLink
        v-for="c in visible"
        :key="c.to"
        :to="c.to"
        class="card card-hover p-5 flex flex-col gap-3 no-underline text-ym-text"
      >
        <div class="w-10 h-10 rounded-md flex items-center justify-center bg-ym-primary-soft text-ym-primary">
          <i :class="['pi', c.icon, 'text-[18px]']" />
        </div>
        <div>
          <div class="text-[15px] font-semibold">{{ t(c.titleKey) }}</div>
          <div class="text-[12.5px] text-ym-muted mt-1">{{ t(c.descKey) }}</div>
        </div>
        <div class="mt-auto text-[12px] text-ym-primary font-medium flex items-center gap-1">
          <span>{{ t("common.edit") }}</span>
          <i class="pi pi-arrow-right text-[10px]" />
        </div>
      </RouterLink>
    </div>
  </div>
</template>
