import type { NavGroup } from "./types"

const main: NavGroup = {
  headerKey: "nav.group_main",
  children: [
    { titleKey: "nav.dashboard", icon: "pi-th-large", to: "/" },
    {
      titleKey: "nav.objects",
      icon: "pi-building",
      to: "/objects",
      permission: "objects.projects.view",
    },
  ],
}

export default main
