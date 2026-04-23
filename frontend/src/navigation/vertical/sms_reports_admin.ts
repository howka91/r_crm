import type { NavGroup } from "./types"

/**
 * Combined group: SMS · Reports · Administration.
 *
 * Grouped together — matches the legacy project and the current design
 * handoff (a single bottom-of-sidebar section), rather than splitting into
 * three tiny groups.
 */
const smsReportsAdmin: NavGroup = {
  headerKey: "nav.group_sms_reports_admin",
  children: [
    { titleKey: "nav.sms_templates", icon: "pi-envelope", disabled: true },
    { titleKey: "nav.sms_manual", icon: "pi-send", disabled: true },
    { titleKey: "nav.reports", icon: "pi-file-pdf", disabled: true },
    {
      titleKey: "nav.admin_users",
      icon: "pi-users",
      to: "/admin/users",
      permission: "administration.users.view",
    },
    {
      titleKey: "nav.admin_permissions",
      icon: "pi-shield",
      to: "/admin/roles",
      permission: "administration.roles.view",
    },
  ],
}

export default smsReportsAdmin
