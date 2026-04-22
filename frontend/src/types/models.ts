/**
 * Hand-written model types for Phase 0-1.
 *
 * Phase N+ will replace these with generated types from the OpenAPI schema:
 *   npx openapi-typescript http://localhost:8000/api/schema/ -o src/types/api.d.ts
 */

export type Locale = "ru" | "uz" | "oz"

export type I18nText = Record<Locale, string>

export type Theme = "light" | "dark"

export type PaymentType = "bank" | "cash" | "barter"

// --- Permission tree (from /permissions/tree/) ----------------------------

export interface PermissionNode {
  key: string
  label: I18nText
  children?: PermissionNode[]
}

// --- Role -----------------------------------------------------------------

export interface Role {
  id: number
  code: string
  name: I18nText
  permissions: Record<string, boolean>
  allowed_payment_types: PaymentType[]
  is_active: boolean
  created_at: string
  modified_at: string
}

export interface RoleBrief {
  id: number
  code: string
  name: I18nText
  permissions: Record<string, boolean>
  allowed_payment_types: PaymentType[]
}

// --- Staff ----------------------------------------------------------------

export interface Staff {
  id: string
  email: string
  full_name: string
  phone_number: string
  language: Locale
  theme: Theme
  photo: string | null
  is_active: boolean
  is_superuser: boolean
  role: RoleBrief | null
  date_joined: string
  last_login: string | null
}

// --- References ------------------------------------------------------------
// Mirrors backend models in apps.references.models.

export interface TimeStamped {
  created_at: string
  modified_at: string
}

export interface Developer extends TimeStamped {
  id: number
  name: I18nText
  director: string
  address: string
  email: string
  phone: string
  bank_name: string
  bank_account: string
  inn: string
  nds: string
  oked: string
  extra: Record<string, unknown>
  is_active: boolean
}

export type DeveloperWrite = Omit<Developer, "id" | "created_at" | "modified_at">

export interface SalesOffice extends TimeStamped {
  id: number
  name: I18nText
  address: string
  /** Decimal, serialized as string by DRF. */
  latitude: string | null
  longitude: string | null
  /** "HH:MM:SS" or null. */
  work_start: string | null
  work_end: string | null
  phone: string
  photo: string | null
  is_active: boolean
}

export type SalesOfficeWrite = Omit<SalesOffice, "id" | "created_at" | "modified_at" | "photo">

export interface Currency extends TimeStamped {
  id: number
  /** ISO 4217, 3 letters, uppercase. */
  code: string
  symbol: string
  name: I18nText
  /** Decimal string — 1 unit of currency = N UZS. */
  rate: string
  is_active: boolean
}

export type CurrencyWrite = Omit<Currency, "id" | "created_at" | "modified_at">

/** Shared shape for every LookupModel subclass (13 backend tables). */
export interface LookupItem extends TimeStamped {
  id: number
  name: I18nText
  sort: number
  is_active: boolean
}

export interface BadgeItem extends LookupItem {
  color: string
}

export interface LocationItem extends LookupItem {
  region: number | null
}

export interface PaymentInPercentItem extends LookupItem {
  percent: string
}

// --- Objects ---------------------------------------------------------------
// Mirrors backend models in apps.objects.models.
// Hierarchy: Project → Building → Section → Floor (→ Apartment in phase 3.2).

export interface Project extends TimeStamped {
  id: number
  developer: number
  /** Read-only — `developer.name` joined in by the serializer. */
  developer_name: I18nText | null
  title: I18nText
  address: string
  description: I18nText
  banks: Array<Record<string, unknown>>
  contract_number_index: number
  sort: number
  is_active: boolean
  /** Read-only — count of child buildings. */
  buildings_count: number
}

export type ProjectWrite = Omit<
  Project,
  | "id"
  | "created_at"
  | "modified_at"
  | "developer_name"
  | "buildings_count"
  | "contract_number_index"
>

export interface Building extends TimeStamped {
  id: number
  project: number
  title: I18nText
  number: string
  cadastral_number: string
  date_of_issue: string | null
  planning_file: string | null
  sort: number
  is_active: boolean
  sections_count: number
}

export type BuildingWrite = Omit<
  Building,
  "id" | "created_at" | "modified_at" | "sections_count" | "planning_file"
>

export interface Section extends TimeStamped {
  id: number
  building: number
  title: I18nText
  number: number
  planning_file: string | null
  sort: number
  is_active: boolean
  floors_count: number
}

export type SectionWrite = Omit<
  Section,
  "id" | "created_at" | "modified_at" | "floors_count" | "planning_file"
>

export interface Floor extends TimeStamped {
  id: number
  section: number
  number: number
  /** Decimal string. */
  price_per_sqm: string
  sort: number
  is_active: boolean
}

export type FloorWrite = Omit<Floor, "id" | "created_at" | "modified_at">

/** URL slug for each lookup type — matches backend kebab-cased class names. */
export type LookupTypeSlug =
  | "apartment-type"
  | "room-type"
  | "construction-stage"
  | "decoration"
  | "premises-decoration"
  | "home-material"
  | "output-windows"
  | "occupied-by"
  | "badge"
  | "payment-method"
  | "payment-in-percent"
  | "region"
  | "location"
