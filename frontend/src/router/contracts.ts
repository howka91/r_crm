/**
 * Contracts module routes — mounted under LayoutVertical.
 *
 * Three list screens (unsigned / signed / edit-requests) share a single
 * view that decides the backend filter by the route name. The wizard for
 * creating a contract and the detail page with tabs live next to the lists.
 *
 * Permission meta is enforced by the global router guard in
 * `router/index.ts`.
 */
import type { RouteRecordRaw } from "vue-router"

const routes: RouteRecordRaw[] = [
  {
    path: "contracts/unsigned",
    name: "contracts-unsigned",
    component: () => import("@/views/modules/Contracts/list.vue"),
    meta: { permission: "contracts.unsigned.view", scope: "unsigned" },
  },
  {
    path: "contracts/signed",
    name: "contracts-signed",
    component: () => import("@/views/modules/Contracts/list.vue"),
    meta: { permission: "contracts.signed.view", scope: "signed" },
  },
  {
    path: "contracts/edit-requests",
    name: "contracts-edit-requests",
    component: () => import("@/views/modules/Contracts/list.vue"),
    meta: { permission: "contracts.edit_requests.view", scope: "edit_requests" },
  },
  {
    path: "contracts/new",
    name: "contracts-new",
    component: () => import("@/views/modules/Contracts/wizard.vue"),
    meta: { permission: "contracts.unsigned.create" },
  },
  {
    path: "contracts/:id(\\d+)",
    name: "contracts-detail",
    component: () => import("@/views/modules/Contracts/detail.vue"),
    meta: { permission: "contracts.unsigned.view" },
  },
]

export default routes
