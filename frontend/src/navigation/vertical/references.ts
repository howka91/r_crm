import type { NavGroup } from "./types"

/**
 * References group. Each link is gated by a backend permission. Users see
 * only what their role grants — sidebar filters in `Sidebar.vue` via
 * `usePermissionStore().check`.
 */
const references: NavGroup = {
  headerKey: "nav.group_references",
  children: [
    {
      titleKey: "nav.references_developers",
      icon: "pi-wrench",
      to: "/references/developers",
      permission: "references.developers.view",
    },
    {
      titleKey: "nav.references_sales_offices",
      icon: "pi-inbox",
      to: "/references/sales-offices",
      permission: "references.offices.view",
    },
    {
      titleKey: "nav.references_currencies",
      icon: "pi-dollar",
      to: "/references/currencies",
      permission: "references.currencies.view",
    },
    {
      titleKey: "nav.references_lookups",
      icon: "pi-tags",
      to: "/references/lookups",
      permission: "references.lookups.view",
    },
    {
      titleKey: "nav.references_contract_templates",
      icon: "pi-clipboard",
      to: "/references/contract-templates",
      permission: "references.templates.view",
    },
  ],
}

export default references
