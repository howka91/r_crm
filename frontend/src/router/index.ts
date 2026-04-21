import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router"

import { useAuthStore } from "@/stores/auth"
import { usePermissionStore } from "@/stores/permissions"

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("@/components/layout/AppShell.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("@/views/DashboardView.vue"),
      },
      {
        path: "admin/users",
        name: "admin-users",
        component: () => import("@/views/admin/UsersView.vue"),
        meta: { permission: "administration.users.view" },
      },
      {
        path: "admin/roles",
        name: "admin-roles",
        component: () => import("@/views/admin/RolesView.vue"),
        meta: { permission: "administration.roles.view" },
      },
      {
        path: "admin/roles/:id",
        name: "admin-role-edit",
        component: () => import("@/views/admin/RoleEditView.vue"),
        meta: { permission: "administration.roles.permissions" },
      },
    ],
  },
  {
    path: "/403",
    name: "forbidden",
    component: () => import("@/views/ForbiddenView.vue"),
    meta: { public: true },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFoundView.vue"),
    meta: { public: true },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const permissions = usePermissionStore()

  // Hydrate user once per session from stored token.
  if (!auth.initialized) {
    await auth.fetchMe()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: "login", query: { next: to.fullPath } }
  }

  if (to.name === "login" && auth.isAuthenticated) {
    return { name: "dashboard" }
  }

  const requiredPerm = to.meta.permission as string | undefined
  if (requiredPerm && auth.isAuthenticated && !permissions.check(requiredPerm)) {
    return { name: "forbidden" }
  }
})
