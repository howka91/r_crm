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
