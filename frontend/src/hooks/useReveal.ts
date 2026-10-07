import { useEffect, useRef } from 'react'
import { prefersReducedMotion } from '../lib/motion'

// One observer shared by every card, so a 100-card grid doesn't create 100 observers.
let observer: IntersectionObserver | null = null

function getObserver(): IntersectionObserver {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer?.unobserve(entry.target)
        }
      }
    },
    { rootMargin: '0px 0px -40px 0px', threshold: 0.1 },
  )
  return observer
}

/**
 * Fade an element in the first time it scrolls into view (adds `is-visible`).
 * Shows it immediately when reduced motion is on or IntersectionObserver is missing.
 */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
      el.classList.add('is-visible')
      return
    }
    const obs = getObserver()
    obs.observe(el)
    return () => obs.unobserve(el)
  }, [])

  return ref
}
