/**
 * Administration module routes — mounted under LayoutVertical.
 *
 * Mirrors `yangi-mahalla-main/src/router/administration.js`. Each domain
 * exports a `RouteRecordRaw[]` that `router/index.ts` plugs into the
 * authenticated shell.
 */
import type { RouteRecordRaw } from "vue-router"

const routes: RouteRecordRaw[] = [
  {
    path: "admin/users",
    name: "admin-users",
    component: () =>
      import("@/views/modules/Administration/userManagement/index.vue"),
    meta: { permission: "administration.users.view" },
  },
  {
    path: "admin/roles",
    name: "admin-roles",
    component: () =>
      import("@/views/modules/Administration/userManagement/roles.vue"),
    meta: { permission: "administration.roles.view" },
  },
  {
    path: "admin/roles/:id",
    name: "admin-role-edit",
    component: () =>
      import("@/views/modules/Administration/userManagement/roleView.vue"),
    meta: { permission: "administration.roles.permissions" },
  },
]

export default routes
