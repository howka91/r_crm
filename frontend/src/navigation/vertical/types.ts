/**
 * Shared types for the vertical sidebar menu configs.
 *
 * Same shape as `yangi-mahalla-main/src/navigation/vertical/*` from the legacy
 * project — each domain exports a default `NavItem[]`; `index.ts` concatenates
 * them into the sidebar menu. Adapted to TS.
 */

export interface NavLink {
  /** i18n key for the label, e.g. "nav.clients" */
  titleKey: string
  /** PrimeIcons class without the "pi " prefix, e.g. "pi-user" */
  icon: string
  /** Internal route path, e.g. "/clients". Omit for design-only placeholders. */
  to?: string
  /** Backend permission key required to see this item, e.g. "clients.view". */
  permission?: string
  /** When true, render the item as visible but not clickable. */
  disabled?: boolean
}

export interface NavHeader {
  /** i18n key for the group header, e.g. "nav.group_sales" */
  headerKey: string
  children: NavLink[]
}

export type NavGroup = NavHeader
