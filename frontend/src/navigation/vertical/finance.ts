import type { NavGroup } from "./types"

const finance: NavGroup = {
  headerKey: "nav.group_finance",
  children: [
    { titleKey: "nav.finance", icon: "pi-chart-line", disabled: true },
    { titleKey: "nav.finance_charts", icon: "pi-chart-bar", disabled: true },
  ],
}

export default finance
