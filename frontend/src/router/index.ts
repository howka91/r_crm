/**
 * Router aggregator.
 *
 * Mirrors `yangi-mahalla-main/src/router/index.js`: public routes + a
 * LayoutVertical shell whose children come from per-domain modules
 * (`./administration.ts`, future `./clients.ts`, `./contracts.ts`, ...).
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router"

import { useAuthStore } from "@/store/auth"
import { usePermissionStore } from "@/store/permissions"

import administrationRoutes from "./administration"
import clientsRoutes from "./clients"
import objectsRoutes from "./objects"
import referencesRoutes from "./references"

const routes: RouteRecordRaw[] = [
  // --- Standalone / full-layout routes -------------------------------------
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/Login.vue"),
    meta: { public: true, layout: "full" },
  },
  {
    path: "/403",
    name: "forbidden",
    component: () => import("@/views/error/Forbidden.vue"),
    meta: { public: true, layout: "full" },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/error/Error404.vue"),
    meta: { public: true, layout: "full" },
  },

  // --- Authenticated shell (LayoutVertical) --------------------------------
  {
    path: "/",
    component: () => import("@/layouts/vertical/LayoutVertical.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("@/views/Home.vue"),
      },
      ...objectsRoutes,
      ...clientsRoutes,
      ...referencesRoutes,
      ...administrationRoutes,
    ],
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
