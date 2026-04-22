import type { NavGroup } from "./types"

const contracts: NavGroup = {
  headerKey: "nav.group_contracts",
  children: [
    { titleKey: "nav.contracts_unsigned", icon: "pi-file", disabled: true },
    { titleKey: "nav.contracts_signed", icon: "pi-file-edit", disabled: true },
    { titleKey: "nav.contracts_edit_requests", icon: "pi-history", disabled: true },
  ],
}

export default contracts
