/**
 * Clients module routes — mounted under LayoutVertical.
 */
import type { RouteRecordRaw } from "vue-router"

const routes: RouteRecordRaw[] = [
  {
    path: "clients",
    name: "clients-list",
    component: () => import("@/views/modules/Clients/index.vue"),
    meta: { permission: "clients.view" },
  },
  {
    path: "clients/:id",
    name: "clients-detail",
    component: () => import("@/views/modules/Clients/detail.vue"),
    meta: { permission: "clients.view" },
    props: true,
  },
]

export default routes
