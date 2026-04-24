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
  BuildingPhoto,
  BuildingWrite,
  Calculation,
  CalculationWrite,
  DiscountRule,
  DiscountRuleWrite,
  Floor,
  FloorWrite,
  PaymentPlan,
  PaymentPlanWrite,
  PriceHistory,
  Project,
  ProjectPhoto,
  ProjectWrite,
  Section,
  SectionWrite,
} from "@/types/models"

import type { Paginated } from "./references"

export interface InventoryTree {
  buildings: Building[]
  sections: Section[]
  floors: Floor[]
  apartments: Apartment[]
}

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
  /** Full tree of Buildings → Sections → Floors → Apartments for one
   *  project in a single request. Replaces the 4-call fan-out used by
   *  the inventory grid and the contract wizard's apartment picker. */
  inventory: (id: number) =>
    http.get<InventoryTree>(`/projects/${id}/inventory/`).then((r) => r.data),
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

export interface DuplicateSectionResponse {
  section: Section
  floors_created: number
  apartments_created: number
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
  /** Cascade-delete the section plus every Floor and Apartment under it. */
  destroyForce: (id: number) =>
    http.delete(`/sections/${id}/?force=true`).then((r) => r.data),
  duplicate: (source_section_id: number, target_building_id: number) =>
    http
      .post<DuplicateSectionResponse>(
        `/sections/${source_section_id}/duplicate/`,
        { target_building_id },
      )
      .then((r) => r.data),
}

export interface ChangePriceResponse {
  floor: Floor
  old_price: string
  new_price: string
  apartments_updated: number
  calculations_upserted: number
  price_history_id: number
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
  /** Cascade-delete the floor plus every Apartment on it. */
  destroyForce: (id: number) =>
    http.delete(`/floors/${id}/?force=true`).then((r) => r.data),
  changePrice: (id: number, new_price: string, comment = "") =>
    http
      .post<ChangePriceResponse>(`/floors/${id}/change-price/`, {
        new_price,
        comment,
      })
      .then((r) => r.data),
}

export interface ChangeStatusResponse {
  apartment: Apartment
  log_id: number
}

export interface BookApartmentResponse {
  apartment: Apartment
  booking_expires_at: string | null
  log_id: number
}

export interface ReleaseApartmentResponse {
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
  book: (id: number, duration_days: number, comment = "", vip = false) =>
    http
      .post<BookApartmentResponse>(`/apartments/${id}/book/`, {
        duration_days,
        comment,
        vip,
      })
      .then((r) => r.data),
  release: (id: number, comment = "") =>
    http
      .post<ReleaseApartmentResponse>(`/apartments/${id}/release/`, {
        comment,
      })
      .then((r) => r.data),
  recalc: (id: number) =>
    http
      .post<{ apartment: Apartment; calculations_upserted: number }>(
        `/apartments/${id}/recalc/`,
      )
      .then((r) => r.data),
}

export const apartmentStatusLogsApi = {
  list: (params?: Record<string, unknown>) =>
    http
      .get<Paginated<ApartmentStatusLog>>("/apartment-status-logs/", { params })
      .then((r) => r.data),
}

export const paymentPlansApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<PaymentPlan>>("/payment-plans/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<PaymentPlan>(`/payment-plans/${id}/`).then((r) => r.data),
  create: (payload: PaymentPlanWrite) =>
    http.post<PaymentPlan>("/payment-plans/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<PaymentPlanWrite>) =>
    http.patch<PaymentPlan>(`/payment-plans/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/payment-plans/${id}/`).then((r) => r.data),
}

export const discountRulesApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<DiscountRule>>("/discount-rules/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<DiscountRule>(`/discount-rules/${id}/`).then((r) => r.data),
  create: (payload: DiscountRuleWrite) =>
    http.post<DiscountRule>("/discount-rules/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<DiscountRuleWrite>) =>
    http.patch<DiscountRule>(`/discount-rules/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/discount-rules/${id}/`).then((r) => r.data),
}

export const calculationsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Calculation>>("/calculations/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Calculation>(`/calculations/${id}/`).then((r) => r.data),
  create: (payload: CalculationWrite) =>
    http.post<Calculation>("/calculations/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<CalculationWrite>) =>
    http.patch<Calculation>(`/calculations/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/calculations/${id}/`).then((r) => r.data),
}

export const priceHistoryApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<PriceHistory>>("/price-history/", { params }).then((r) => r.data),
}

/** Photo galleries. Create/update go multipart (the `file` is a File
 *  object); `updateJson` covers caption-only edits. `makeCover` calls
 *  the backend action that promotes a photo to sort=0 and renumbers
 *  siblings densely. */
export const projectPhotosApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<ProjectPhoto>>("/project-photos/", { params }).then((r) => r.data),
  upload: (form: FormData) =>
    http
      .post<ProjectPhoto>("/project-photos/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),
  updateJson: (id: number, payload: Partial<Pick<ProjectPhoto, "caption" | "is_active">>) =>
    http.patch<ProjectPhoto>(`/project-photos/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/project-photos/${id}/`).then((r) => r.data),
  makeCover: (id: number) =>
    http
      .post<ProjectPhoto>(`/project-photos/${id}/make-cover/`)
      .then((r) => r.data),
}

export const buildingPhotosApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<BuildingPhoto>>("/building-photos/", { params }).then((r) => r.data),
  upload: (form: FormData) =>
    http
      .post<BuildingPhoto>("/building-photos/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),
  updateJson: (id: number, payload: Partial<Pick<BuildingPhoto, "caption" | "is_active">>) =>
    http.patch<BuildingPhoto>(`/building-photos/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/building-photos/${id}/`).then((r) => r.data),
  makeCover: (id: number) =>
    http
      .post<BuildingPhoto>(`/building-photos/${id}/make-cover/`)
      .then((r) => r.data),
}
