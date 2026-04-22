/**
 * References module routes — mounted under LayoutVertical.
 *
 * Hub page at `/references` (overview) + 4 domain screens. Permission meta
 * is enforced by the global router guard in `router/index.ts`.
 */
import type { RouteRecordRaw } from "vue-router"

const routes: RouteRecordRaw[] = [
  {
    path: "references",
    name: "references-hub",
    component: () => import("@/views/modules/References/index.vue"),
  },
  {
    path: "references/developers",
    name: "references-developers",
    component: () => import("@/views/modules/References/developers/index.vue"),
    meta: { permission: "references.developers.view" },
  },
  {
    path: "references/sales-offices",
    name: "references-sales-offices",
    component: () => import("@/views/modules/References/salesOffices/index.vue"),
    meta: { permission: "references.offices.view" },
  },
  {
    path: "references/currencies",
    name: "references-currencies",
    component: () => import("@/views/modules/References/currencies/index.vue"),
    meta: { permission: "references.currencies.view" },
  },
  {
    path: "references/lookups",
    name: "references-lookups",
    component: () => import("@/views/modules/References/lookups/index.vue"),
    meta: { permission: "references.lookups.view" },
  },
]

export default routes
