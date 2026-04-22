/**
 * CASL integration. Mirrors `yangi-mahalla-main/src/libs/acl/` from the legacy
 * project, adapted to @casl/vue v2 (Vue 3).
 *
 * The "ability" here uses a single generic `Action × Subject` signature; we do
 * not split by model — permissions are referenced by a dotted key like
 * "objects.apartments.view" (mirroring the backend permission tree).
 *
 * Usage in components:
 *
 *   const { can } = useAbility()
 *   if (can("access", "objects.apartments.view")) { ... }
 *
 * or in templates: `<Button v-if="$can('access', 'objects.apartments.view')" ... />`
 */
import { createMongoAbility } from "@casl/ability"
import { abilitiesPlugin, useAbility as _useAbility } from "@casl/vue"

export type AppAbility = ReturnType<typeof createMongoAbility>

export const ability = createMongoAbility() as AppAbility

export { abilitiesPlugin }

export function useAbility() {
  return _useAbility<AppAbility>()
}
