/**
 * References domain API client.
 *
 * Rich entities get their own typed CRUD bundle (`developersApi`,
 * `salesOfficesApi`, `currenciesApi`). The 13 lookup types share a generic
 * `lookupsApi[slug]` map — each element exposes the same CRUD shape, with
 * URL slug and TS type parameterised.
 *
 * Mirrors backend urls.py route registration.
 */
import { http } from "@/libs/axios"
import type {
  BadgeItem,
  Currency,
  CurrencyWrite,
  Developer,
  DeveloperWrite,
  LocationItem,
  LookupItem,
  LookupTypeSlug,
  PaymentInPercentItem,
  Planning,
  SalesOffice,
  SalesOfficeWrite,
} from "@/types/models"

// DRF pagination envelope (shared with administration).
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// --- Rich entities ---------------------------------------------------------

export const developersApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Developer>>("/developers/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Developer>(`/developers/${id}/`).then((r) => r.data),
  create: (payload: DeveloperWrite) =>
    http.post<Developer>("/developers/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<DeveloperWrite>) =>
    http.patch<Developer>(`/developers/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/developers/${id}/`).then((r) => r.data),
}

export const salesOfficesApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<SalesOffice>>("/sales-offices/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<SalesOffice>(`/sales-offices/${id}/`).then((r) => r.data),
  create: (payload: SalesOfficeWrite) =>
    http.post<SalesOffice>("/sales-offices/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<SalesOfficeWrite>) =>
    http.patch<SalesOffice>(`/sales-offices/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/sales-offices/${id}/`).then((r) => r.data),
}

export const currenciesApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Currency>>("/currencies/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Currency>(`/currencies/${id}/`).then((r) => r.data),
  create: (payload: CurrencyWrite) =>
    http.post<Currency>("/currencies/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<CurrencyWrite>) =>
    http.patch<Currency>(`/currencies/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/currencies/${id}/`).then((r) => r.data),
}

/**
 * Planning catalog — create/update take a FormData payload so image_2d
 * and image_3d can be uploaded alongside the scalar fields in a single
 * multipart request. For lightweight PATCHes without files (toggling
 * is_active, renaming), use `updateJson` which sends a JSON body.
 */
export const planningsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Planning>>("/plannings/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Planning>(`/plannings/${id}/`).then((r) => r.data),
  create: (payload: FormData) =>
    http
      .post<Planning>("/plannings/", payload, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),
  update: (id: number, payload: FormData) =>
    http
      .patch<Planning>(`/plannings/${id}/`, payload, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),
  updateJson: (id: number, payload: Record<string, unknown>) =>
    http.patch<Planning>(`/plannings/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/plannings/${id}/`).then((r) => r.data),
}

// --- Lookups (generic) -----------------------------------------------------

/**
 * Generic lookup CRUD shape. Write payloads are intentionally loose
 * (`Record<string, unknown>`) so specialized subtypes (Badge, Location,
 * PaymentInPercent) stay compatible with the shared `lookupsApi` map.
 * The UI screen builds payloads at runtime from `selectedMeta.extras`.
 */
export interface LookupCrud<T extends LookupItem = LookupItem> {
  list: (params?: Record<string, unknown>) => Promise<Paginated<T>>
  retrieve: (id: number) => Promise<T>
  create: (payload: Record<string, unknown>) => Promise<T>
  update: (id: number, payload: Record<string, unknown>) => Promise<T>
  destroy: (id: number) => Promise<unknown>
}

function makeLookupCrud<T extends LookupItem>(slug: string): LookupCrud<T> {
  const base = `/${slug}/`
  return {
    list: (params) => http.get<Paginated<T>>(base, { params }).then((r) => r.data),
    retrieve: (id) => http.get<T>(`${base}${id}/`).then((r) => r.data),
    create: (payload) => http.post<T>(base, payload).then((r) => r.data),
    update: (id, payload) =>
      http.patch<T>(`${base}${id}/`, payload).then((r) => r.data),
    destroy: (id) => http.delete(`${base}${id}/`).then((r) => r.data),
  }
}

/** Metadata + CRUD bundle for every lookup type. Keyed by URL slug. */
export const lookupTypes: Array<{
  slug: LookupTypeSlug
  /** i18n key inside `references.lookup_types.<key>`. */
  labelKey: string
  /** Columns to render beyond the base ones, if any. */
  extras: Array<"color" | "region" | "percent">
}> = [
  { slug: "apartment-type", labelKey: "apartment_type", extras: [] },
  { slug: "room-type", labelKey: "room_type", extras: [] },
  { slug: "construction-stage", labelKey: "construction_stage", extras: [] },
  { slug: "decoration", labelKey: "decoration", extras: [] },
  { slug: "premises-decoration", labelKey: "premises_decoration", extras: [] },
  { slug: "home-material", labelKey: "home_material", extras: [] },
  { slug: "output-windows", labelKey: "output_windows", extras: [] },
  { slug: "occupied-by", labelKey: "occupied_by", extras: [] },
  { slug: "badge", labelKey: "badge", extras: ["color"] },
  { slug: "payment-method", labelKey: "payment_method", extras: [] },
  { slug: "payment-in-percent", labelKey: "payment_in_percent", extras: ["percent"] },
  { slug: "region", labelKey: "region", extras: [] },
  { slug: "location", labelKey: "location", extras: ["region"] },
]

export const lookupsApi: Record<LookupTypeSlug, LookupCrud<LookupItem>> = {
  "apartment-type": makeLookupCrud("apartment-type"),
  "room-type": makeLookupCrud("room-type"),
  "construction-stage": makeLookupCrud("construction-stage"),
  decoration: makeLookupCrud("decoration"),
  "premises-decoration": makeLookupCrud("premises-decoration"),
  "home-material": makeLookupCrud("home-material"),
  "output-windows": makeLookupCrud("output-windows"),
  "occupied-by": makeLookupCrud("occupied-by"),
  badge: makeLookupCrud<BadgeItem>("badge"),
  "payment-method": makeLookupCrud("payment-method"),
  "payment-in-percent": makeLookupCrud<PaymentInPercentItem>("payment-in-percent"),
  region: makeLookupCrud("region"),
  location: makeLookupCrud<LocationItem>("location"),
}
