/**
 * Hand-written model types for Phase 0-1.
 *
 * Phase N+ will replace these with generated types from the OpenAPI schema:
 *   npx openapi-typescript http://localhost:8000/api/schema/ -o src/types/api.d.ts
 */

export type Locale = "ru" | "uz" | "oz"

export type I18nText = Record<Locale, string>

export type Theme = "light" | "dark"

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
  is_active: boolean
  created_at: string
  modified_at: string
}

export interface RoleBrief {
  id: number
  code: string
  name: I18nText
  permissions: Record<string, boolean>
}

// --- Staff ----------------------------------------------------------------

export interface Staff {
  id: string
  login: string
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
  apartments_count: number
}

export type FloorWrite = Omit<
  Floor,
  "id" | "created_at" | "modified_at" | "apartments_count"
>

/** Apartment status — mirrors backend Apartment.Status.values. */
export type ApartmentStatus =
  | "free"
  | "booked"
  | "booked_vip"
  | "formalized"
  | "escrow"
  | "sold"

export interface Apartment extends TimeStamped {
  id: number
  floor: number
  number: string
  rooms_count: number
  /** Decimal strings — never Float. */
  area: string
  total_bti_area: string
  total_price: string
  surcharge: string
  is_duplex: boolean
  is_studio: boolean
  is_euro_planning: boolean
  planning_file: string | null
  decoration: number | null
  output_window: number | null
  occupied_by: number | null
  /** Array of Badge IDs. */
  characteristics: number[]
  status: ApartmentStatus
  /** Translated status label (read-only). */
  status_display: string
  booking_expires_at: string | null
  sort: number
  is_active: boolean
}

export type ApartmentWrite = Omit<
  Apartment,
  | "id"
  | "created_at"
  | "modified_at"
  | "status_display"
  | "booking_expires_at"
  | "planning_file"
>

export interface ApartmentStatusLog {
  id: number
  apartment: number
  old_status: string
  new_status: string
  changed_by: string | null
  changed_by_name: string | null
  comment: string
  created_at: string
}

// --- Pricing (PaymentPlan / DiscountRule / Calculation / PriceHistory) ----

export interface PaymentPlan extends TimeStamped {
  id: number
  project: number
  name: I18nText
  /** Decimal string, 0..100. */
  down_payment_percent: string
  installment_months: number
  sort: number
  is_active: boolean
}

export type PaymentPlanWrite = Omit<PaymentPlan, "id" | "created_at" | "modified_at">

export interface DiscountRule extends TimeStamped {
  id: number
  project: number
  /** Decimal strings. */
  area_start: string
  area_end: string
  /** FK id → references.PaymentInPercent. */
  payment_percent: number
  discount_percent: string
  is_duplex: boolean
  sort: number
  is_active: boolean
}

export type DiscountRuleWrite = Omit<DiscountRule, "id" | "created_at" | "modified_at">

export interface Calculation extends TimeStamped {
  id: number
  apartment: number
  payment_percent: number
  discount_percent: string
  installment_months: number
  new_price_per_sqm: string
  new_total_price: string
  initial_fee: string
  monthly_payment: string
  is_active: boolean
}

export type CalculationWrite = Omit<Calculation, "id" | "created_at" | "modified_at">

export interface PriceHistory {
  id: number
  floor: number
  old_price: string
  new_price: string
  changed_by: string | null
  changed_by_name: string | null
  comment: string
  created_at: string
}

// --- Clients --------------------------------------------------------------
// Mirrors backend models in apps.clients.models.

export type ClientEntity = "phys" | "jur"
export type ClientGender = "" | "male" | "female"
export type RequisiteType = "internal" | "local"

export interface ClientStatus extends TimeStamped {
  id: number
  name: I18nText
  color: string
  sort: number
  is_active: boolean
}
export type ClientStatusWrite = Omit<ClientStatus, "id" | "created_at" | "modified_at">

export interface ClientGroup extends TimeStamped {
  id: number
  name: I18nText
  sort: number
  is_active: boolean
}
export type ClientGroupWrite = Omit<ClientGroup, "id" | "created_at" | "modified_at">

export interface Client extends TimeStamped {
  id: number
  entity: ClientEntity
  gender: ClientGender
  full_name: string
  phones: string[]
  emails: string[]
  inn: string
  oked: string
  pin: string
  birth_date: string | null
  address: string
  description: string
  manager: string | null
  /** Read-only — Staff.full_name joined in. */
  manager_name: string | null
  status: number | null
  /** Read-only — ClientStatus.name joined in. */
  status_name: I18nText | null
  groups: number[]
  contacts_count: number
  requisites_count: number
  is_active: boolean
}
export type ClientWrite = Omit<
  Client,
  | "id"
  | "created_at"
  | "modified_at"
  | "manager_name"
  | "status_name"
  | "contacts_count"
  | "requisites_count"
>

export interface ClientContactPassport {
  series?: string
  number?: string
  issued_by?: string
  issued_date?: string
  registration_address?: string
  [k: string]: unknown
}

export interface ClientContact extends TimeStamped {
  id: number
  client: number
  full_name: string
  role: string
  is_chief: boolean
  phones: string[]
  email: string
  passport: ClientContactPassport
  birth_date: string | null
  inn: string
  pin: string
  is_active: boolean
}
export type ClientContactWrite = Omit<
  ClientContact,
  "id" | "created_at" | "modified_at"
>

export interface BankRequisite {
  account?: string
  bank?: string
  mfo?: string
  currency?: string
  [k: string]: unknown
}

export interface Requisite extends TimeStamped {
  id: number
  client: number
  type: RequisiteType
  bank_requisite: BankRequisite
  is_active: boolean
}
export type RequisiteWrite = Omit<Requisite, "id" | "created_at" | "modified_at">

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
