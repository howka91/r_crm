/**
 * Vertical sidebar menu — aggregated from per-domain configs.
 *
 * Mirrors `yangi-mahalla-main/src/navigation/vertical/index.js` layout:
 * each domain owns a file, this module stitches them together in the
 * order they appear in the sidebar.
 *
 * Add a new domain = add one import + one array entry. Do not edit
 * `Sidebar.vue` to add menu items.
 */
import contracts from "./contracts"
import finance from "./finance"
import main from "./main"
import references from "./references"
import sales from "./sales"
import smsReportsAdmin from "./sms_reports_admin"
import type { NavGroup } from "./types"

const navigation: NavGroup[] = [
  main,
  sales,
  contracts,
  finance,
  references,
  smsReportsAdmin,
]

export default navigation
export type { NavGroup, NavLink } from "./types"
