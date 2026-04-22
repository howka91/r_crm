import type { NavGroup } from "./types"

/**
 * Kanban and "Презентация" from the original Vuexy template are dropped per
 * architectural decision #10 in docs/SESSION_STATE.md — they are NOT in the
 * product plan.
 */
const sales: NavGroup = {
  headerKey: "nav.group_sales",
  children: [{ titleKey: "nav.clients", icon: "pi-user", disabled: true }],
}

export default sales
