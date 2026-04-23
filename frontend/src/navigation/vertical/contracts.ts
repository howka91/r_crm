import type { NavGroup } from "./types"

const contracts: NavGroup = {
  headerKey: "nav.group_contracts",
  children: [
    {
      titleKey: "nav.contracts_unsigned",
      icon: "pi-file",
      to: "/contracts/unsigned",
      permission: "contracts.unsigned.view",
    },
    {
      titleKey: "nav.contracts_signed",
      icon: "pi-file-edit",
      to: "/contracts/signed",
      permission: "contracts.signed.view",
    },
    {
      titleKey: "nav.contracts_edit_requests",
      icon: "pi-history",
      to: "/contracts/edit-requests",
      permission: "contracts.edit_requests.view",
    },
  ],
}

export default contracts
