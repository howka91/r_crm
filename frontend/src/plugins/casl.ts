/**
 * CASL integration.
 *
 * The "ability" here uses a single generic `Action × Subject` signature; we do
 * not split by model — permissions are referenced by a dotted key like
 * "objects.apartments.view" (mirroring the backend permission tree).
 *
 * Usage in components:
 *
 *   const { can } = useAbility()
 *   if (can("read", "objects.apartments")) { ... }
 *
 * or in templates: `<Button v-if="$can('read', 'objects.apartments')" ... />`
 */
import { createMongoAbility } from "@casl/ability"
import { abilitiesPlugin, useAbility as _useAbility } from "@casl/vue"

export type AppAbility = ReturnType<typeof createMongoAbility>

export const ability = createMongoAbility() as AppAbility

export { abilitiesPlugin }

export function useAbility() {
  return _useAbility<AppAbility>()
}
