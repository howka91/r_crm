/**
 * Objects domain API client.
 *
 * Shape mirrors `api/references.ts` — each hierarchy level gets its own
 * typed CRUD bundle. The `list` functions accept a `params` object for
 * server-side filtering; common filters are `project`, `building`, `section`.
 *
 * Routes mirror backend `apps.objects.urls`:
 *   /projects/ /buildings/ /sections/ /floors/
 */
import { http } from "@/libs/axios"
import type {
  Apartment,
  ApartmentStatus,
  ApartmentStatusLog,
  ApartmentWrite,
  Building,
  BuildingWrite,
  Floor,
  FloorWrite,
  Project,
  ProjectWrite,
  Section,
  SectionWrite,
} from "@/types/models"

import type { Paginated } from "./references"

export const projectsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Project>>("/projects/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Project>(`/projects/${id}/`).then((r) => r.data),
  create: (payload: ProjectWrite) =>
    http.post<Project>("/projects/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ProjectWrite>) =>
    http.patch<Project>(`/projects/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/projects/${id}/`).then((r) => r.data),
}

export const buildingsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Building>>("/buildings/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Building>(`/buildings/${id}/`).then((r) => r.data),
  create: (payload: BuildingWrite) =>
    http.post<Building>("/buildings/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<BuildingWrite>) =>
    http.patch<Building>(`/buildings/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/buildings/${id}/`).then((r) => r.data),
}

export const sectionsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Section>>("/sections/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Section>(`/sections/${id}/`).then((r) => r.data),
  create: (payload: SectionWrite) =>
    http.post<Section>("/sections/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<SectionWrite>) =>
    http.patch<Section>(`/sections/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/sections/${id}/`).then((r) => r.data),
}

export const floorsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Floor>>("/floors/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Floor>(`/floors/${id}/`).then((r) => r.data),
  create: (payload: FloorWrite) =>
    http.post<Floor>("/floors/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<FloorWrite>) =>
    http.patch<Floor>(`/floors/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/floors/${id}/`).then((r) => r.data),
}

export interface ChangeStatusResponse {
  apartment: Apartment
  log_id: number
}

export const apartmentsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Apartment>>("/apartments/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Apartment>(`/apartments/${id}/`).then((r) => r.data),
  create: (payload: ApartmentWrite) =>
    http.post<Apartment>("/apartments/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ApartmentWrite>) =>
    http.patch<Apartment>(`/apartments/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/apartments/${id}/`).then((r) => r.data),
  changeStatus: (id: number, new_status: ApartmentStatus, comment = "") =>
    http
      .post<ChangeStatusResponse>(`/apartments/${id}/change-status/`, {
        new_status,
        comment,
      })
      .then((r) => r.data),
}

export const apartmentStatusLogsApi = {
  list: (params?: Record<string, unknown>) =>
    http
      .get<Paginated<ApartmentStatusLog>>("/apartment-status-logs/", { params })
      .then((r) => r.data),
}
