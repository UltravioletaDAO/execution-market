/**
 * useReducedMotion — subscribe to the `prefers-reduced-motion` media query.
 *
 * Components that drive autoplay, parallax, or animation-heavy transitions
 * should gate them behind this hook so users who opt out of motion
 * (a WCAG 2.3.3 / 2.2 AA requirement) get the static variant.
 */

import { useEffect, useState } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

function readInitial(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia(QUERY).matches
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(readInitial)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }

    const mql = window.matchMedia(QUERY)
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches)

    // Sync once on mount in case SSR gave us the wrong initial value.
    setReduced(mql.matches)

    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    }

    // Safari < 14 fallback
    mql.addListener(onChange)
    return () => mql.removeListener(onChange)
  }, [])

  return reduced
}
