/**
 * Objects module routes — mounted under LayoutVertical.
 *
 * Hub at `/objects` (ЖК grid). Drill-down `/objects/projects/:id` shows a
 * single project with its building tree and (phase 3.5) the shaxmatka.
 * Permission meta is enforced by the global router guard in `router/index.ts`.
 */
import type { RouteRecordRaw } from "vue-router"

const routes: RouteRecordRaw[] = [
  {
    path: "objects",
    name: "objects-hub",
    component: () => import("@/views/modules/Objects/index.vue"),
    meta: { permission: "objects.projects.view" },
  },
  {
    path: "objects/projects/:id",
    name: "objects-project-detail",
    component: () => import("@/views/modules/Objects/projects/detail.vue"),
    meta: { permission: "objects.projects.view" },
    props: true,
  },
  {
    path: "objects/projects/:id/pricing",
    name: "objects-project-pricing",
    component: () => import("@/views/modules/Objects/projects/pricing.vue"),
    meta: { permission: "objects.projects.view" },
    props: true,
  },
]

export default routes
