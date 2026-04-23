/**
 * Administration module API — staff + roles.
 *
 * Mirrors `yangi-mahalla-main/src/api/administration.js` in naming; its
 * methods are split here into `staffApi` and `roleApi` namespaces to match
 * DRF's ViewSet-per-resource layout.
 */
import { http } from "@/libs/axios"
import type { Role, Staff } from "@/types/models"

// DRF pagination envelope.
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// --- Staff ----------------------------------------------------------------

export interface StaffWritePayload {
  login: string
  email?: string
  full_name: string
  phone_number?: string
  language?: "ru" | "uz" | "oz"
  theme?: "light" | "dark"
  role_id?: number | null
  is_active?: boolean
  password?: string
}

export const staffApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Staff>>("/staff/", { params }).then((r) => r.data),
  retrieve: (id: string) => http.get<Staff>(`/staff/${id}/`).then((r) => r.data),
  create: (payload: StaffWritePayload) =>
    http.post<Staff>("/staff/", payload).then((r) => r.data),
  update: (id: string, payload: Partial<StaffWritePayload>) =>
    http.patch<Staff>(`/staff/${id}/`, payload).then((r) => r.data),
  destroy: (id: string) => http.delete(`/staff/${id}/`).then((r) => r.data),
  resetPassword: (id: string, newPassword: string) =>
    http
      .post(`/staff/${id}/reset-password/`, { new_password: newPassword })
      .then((r) => r.data),
}

// --- Role -----------------------------------------------------------------

export interface RoleWritePayload {
  // `code` is optional on create — backend auto-generates a slug from
  // `name.ru` when missing. `name` accepts any subset of {ru, uz, oz};
  // missing translations are backfilled from `ru` server-side.
  code?: string
  name: { ru: string; uz?: string; oz?: string }
  permissions?: Record<string, boolean>
  is_active?: boolean
}

export const roleApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Role>>("/roles/", { params }).then((r) => r.data),
  retrieve: (id: number) => http.get<Role>(`/roles/${id}/`).then((r) => r.data),
  create: (payload: RoleWritePayload) =>
    http.post<Role>("/roles/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<RoleWritePayload>) =>
    http.patch<Role>(`/roles/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/roles/${id}/`).then((r) => r.data),
}
