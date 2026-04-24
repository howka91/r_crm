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
  {
    path: "references/plannings",
    name: "references-plannings-hub",
    component: () => import("@/views/modules/References/plannings/hub.vue"),
    meta: { permission: "references.plannings.view" },
  },
  {
    path: "references/plannings/project/:id(\\d+)",
    name: "references-plannings-project",
    component: () => import("@/views/modules/References/plannings/project.vue"),
    meta: { permission: "references.plannings.view" },
    props: true,
  },
  {
    path: "references/contract-templates",
    name: "references-contract-templates",
    component: () =>
      import("@/views/modules/References/contractTemplates/index.vue"),
    meta: { permission: "references.templates.view" },
  },
  {
    path: "references/contract-templates/new",
    name: "references-contract-templates-new",
    component: () =>
      import("@/views/modules/References/contractTemplates/edit.vue"),
    meta: { permission: "references.templates.create" },
  },
  {
    path: "references/contract-templates/:id(\\d+)",
    name: "references-contract-templates-edit",
    component: () =>
      import("@/views/modules/References/contractTemplates/edit.vue"),
    meta: { permission: "references.templates.edit" },
  },
]

export default routes
