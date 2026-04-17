/**
 * Client-side feature flags (build-time Vite env vars).
 *
 * All flags default to OFF — opt-in via `VITE_*=true` in `.env.local`
 * or the build environment. Keep this module free of side effects so
 * tree-shaking can eliminate unused branches.
 */

export function isWorldIdEnabled(): boolean {
  return import.meta.env.VITE_WORLD_ID_ENABLED === 'true'
}
