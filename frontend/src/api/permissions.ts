import { http } from "@/libs/axios"
import type { PermissionNode } from "@/types/models"

export const permissionsApi = {
  getTree: () =>
    http.get<{ tree: PermissionNode[] }>("/permissions/tree/").then((r) => r.data.tree),
}
