<script setup lang="ts">
/**
 * Dashboard — project-level overview.
 *
 * Reproduces `design_handoff_smart_rc/ds-screens.jsx#Dashboard`:
 *  - Header row (eyebrow + project title + summary on the left,
 *    period / export buttons on the right).
 *  - 4 stat cards (Свободно / Бронь / Продано / Выручка) with a soft-tinted
 *    icon tile.
 *  - 2/3 bar chart "Динамика договоров" — 6 months, two stacked bars
 *    per month (primary gradient + primary-soft).
 *  - 1/3 "Недавние договоры" — 5-line list with avatars, IDs and status chips.
 *
 * Data is mocked for Phase 2; wiring to /dashboard/ API lands in a later phase.
 */
import { computed } from "vue"
import { useI18n } from "vue-i18n"

const { t, tm, rt } = useI18n()

interface Stat {
  labelKey: string
  value: string
  detailKey: string
  icon: string
  /** One of success | warning | danger | primary — drives both accent + tile colors. */
  accent: "success" | "warning" | "danger" | "primary"
}

const stats = computed<Stat[]>(() => [
  {
    labelKey: "dashboard.stat_free_label",
    value: "127",
    detailKey: "dashboard.stat_free_detail",
    icon: "pi-check-circle",
    accent: "success",
  },
  {
    labelKey: "dashboard.stat_booked_label",
    value: "38",
    detailKey: "dashboard.stat_booked_detail",
    icon: "pi-clock",
    accent: "warning",
  },
  {
    labelKey: "dashboard.stat_sold_label",
    value: "136",
    detailKey: "dashboard.stat_sold_detail",
    icon: "pi-ban",
    accent: "danger",
  },
  {
    labelKey: "dashboard.stat_revenue_label",
    value: t("dashboard.stat_revenue_value"),
    detailKey: "dashboard.stat_revenue_detail",
    icon: "pi-chart-line",
    accent: "primary",
  },
])

/** 6 months of two-series bar data (contracts + bookings), heights in px. */
const chartData = [
  { a: 60, b: 30 },
  { a: 72, b: 36 },
  { a: 54, b: 40 },
  { a: 88, b: 48 },
  { a: 96, b: 38 },
  { a: 120, b: 52 },
]

const monthLabels = computed<string[]>(() => {
  const raw = tm("dashboard.chart_months")
  if (!Array.isArray(raw)) return []
  return raw.map((m) => rt(m as string))
})

interface RecentContract {
  id: string
  name: string
  status: "paid" | "booked" | "overdue"
  time: string
}

const recent: RecentContract[] = [
  { id: "YM-2026-0421", name: "Каримов Р.А.", status: "paid", time: "7 мин" },
  { id: "YM-2026-0420", name: "Исламова С.К.", status: "booked", time: "52 мин" },
  { id: "YM-2026-0418", name: "Жалилов Б.У.", status: "overdue", time: "3 ч" },
  { id: "YM-2026-0415", name: "Назарова Д.А.", status: "paid", time: "вчера" },
  { id: "YM-2026-0412", name: "Ахмедов Т.И.", status: "booked", time: "вчера" },
]

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean)
  return parts
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
}

function statusChipClass(s: RecentContract["status"]): string {
  return s === "paid"
    ? "chip chip-success"
    : s === "booked"
      ? "chip chip-warn"
      : "chip chip-danger"
}

function statusLabel(s: RecentContract["status"]): string {
  return t(
    s === "paid"
      ? "dashboard.status_paid"
      : s === "booked"
        ? "dashboard.status_booked"
        : "dashboard.status_overdue",
  )
}

/** Soft-fill + foreground for the icon tile inside each stat card. */
const accentTile: Record<Stat["accent"], { bg: string; fg: string }> = {
  success: { bg: "bg-ym-success-soft", fg: "text-ym-success" },
  warning: { bg: "bg-ym-warning-soft", fg: "text-ym-warning" },
  danger: { bg: "bg-ym-danger-soft", fg: "text-ym-danger" },
  primary: { bg: "bg-ym-primary-soft", fg: "text-ym-primary" },
}
</script>

<template>
  <div>
    <!-- Header row -->
    <div class="flex items-end justify-between mb-5 mt-1 px-1">
      <div>
        <div
          class="text-[11px] uppercase tracking-[0.12em] font-mono mb-1.5 text-ym-subtle"
        >
          {{ t("dashboard.eyebrow") }}
        </div>
        <h1 class="text-[28px] font-semibold leading-none tracking-[-0.025em]">
          {{ t("dashboard.project_title") }}
        </h1>
        <div class="text-[13px] mt-2 text-ym-muted">
          {{ t("dashboard.project_summary") }}
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn btn-ghost btn-sm">
          <i class="pi pi-calendar text-[11px]" />
          {{ t("dashboard.period_button") }}
        </button>
        <button class="btn btn-ghost btn-sm">
          <i class="pi pi-download text-[11px]" />
          {{ t("dashboard.export") }}
        </button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-4 gap-4 mb-5">
      <div v-for="s in stats" :key="s.labelKey" class="card p-5">
        <div class="flex items-start justify-between">
          <div
            class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle"
          >
            {{ t(s.labelKey) }}
          </div>
          <div
            :class="[
              'w-8 h-8 rounded-md flex items-center justify-center',
              accentTile[s.accent].bg,
              accentTile[s.accent].fg,
            ]"
          >
            <i :class="['pi', s.icon, 'text-[13px]']" />
          </div>
        </div>
        <div class="text-[26px] font-semibold mt-2 tracking-[-0.025em]">
          {{ s.value }}
        </div>
        <div class="text-[11.5px] font-mono mt-1 text-ym-muted">
          {{ t(s.detailKey) }}
        </div>
      </div>
    </div>

    <!-- Bottom row: chart + recent -->
    <div class="grid grid-cols-3 gap-4">
      <!-- Bar chart -->
      <div class="card p-5 col-span-2">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div
              class="text-[11px] uppercase tracking-wider font-mono text-ym-subtle"
            >
              {{ t("dashboard.chart_eyebrow") }}
            </div>
            <div class="text-[16px] font-semibold mt-1">
              {{ t("dashboard.chart_title") }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="chip chip-primary">{{ t("dashboard.chart_series_contracts") }}</span>
            <span class="chip chip-ghost">{{ t("dashboard.chart_series_booked") }}</span>
          </div>
        </div>
        <div class="relative h-[200px] flex items-end gap-3">
          <div
            v-for="(b, i) in chartData"
            :key="i"
            class="flex-1 flex flex-col items-center gap-1.5"
          >
            <div class="w-full flex items-end gap-1 h-[180px]">
              <div
                class="flex-1 rounded-t-[6px] bg-gradient-to-t from-ym-primary-h to-ym-primary"
                :style="{ height: b.a * 1.4 + 'px' }"
              />
              <div
                class="flex-1 rounded-t-[6px] bg-ym-primary-soft"
                :style="{ height: b.b * 1.4 + 'px' }"
              />
            </div>
            <div class="text-[10.5px] font-mono text-ym-subtle">
              {{ monthLabels[i] }}
            </div>
          </div>
        </div>
      </div>

      <!-- Recent contracts -->
      <div class="card p-5">
        <div
          class="text-[11px] uppercase tracking-wider font-mono mb-1 text-ym-subtle"
        >
          {{ t("dashboard.recent_eyebrow") }}
        </div>
        <div class="text-[16px] font-semibold mb-4">
          {{ t("dashboard.recent_title") }}
        </div>
        <div class="space-y-3">
          <div v-for="c in recent" :key="c.id" class="flex items-center gap-3">
            <div
              class="w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-semibold bg-ym-primary-soft text-ym-primary shrink-0"
            >
              {{ initials(c.name) }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-medium truncate">{{ c.name }}</div>
              <div class="text-[11px] font-mono truncate text-ym-subtle">
                {{ c.id }}
              </div>
            </div>
            <span :class="statusChipClass(c.status)">{{ statusLabel(c.status) }}</span>
            <span class="text-[11px] font-mono text-ym-subtle">{{ c.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
